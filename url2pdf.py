#!/usr/bin/env python3
"""
URL2PDF — Конвертер веб-страниц в PDF.

Создаёт качественные PDF-файлы из веб-страниц с помощью Playwright.
Поддерживает полную прокрутку страницы, фоновые изображения,
автоматическое масштабирование и разбивку на страницы A4.

Пример использования:
    python url2pdf.py https://example.com --full-page -o output.pdf
"""

from __future__ import annotations

import click
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from typing import Literal


# =============================================================================
# КОНСТАНТЫ
# =============================================================================

# A4 размеры при 96 DPI (для viewport)
A4_PORTRAIT: dict[str, int] = {'width': 794, 'height': 1123}
A4_LANDSCAPE: dict[str, int] = {'width': 1123, 'height': 794}

# A4 в пунктах при 72 DPI (для PDF)
A4_WIDTH_PT: int = 595
MARGIN_05CM_PT: int = 38  # ~0.5cm в пикселях при 72 DPI

# Стандартный desktop viewport
DESKTOP_VIEWPORT: dict[str, int] = {'width': 1920, 'height': 1080}

# Настройки безопасности
ALLOWED_SCHEMES: set[str] = {'http', 'https'}
BLOCKED_HOSTS: set[str] = {'localhost', '127.0.0.1', '0.0.0.0', '::1'}

# CSS для сохранения фонов при печати
PRINT_CSS: str = '''
    * {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
        color-adjust: exact !important;
    }
    body {
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
    }
'''

# Таймаут ожидания сети (по умолчанию)
NETWORK_IDLE_TIMEOUT_MS: int = 15000

# Задержка для загрузки изображений по умолчанию
DEFAULT_IMAGE_TIMEOUT_MS: int = 8000


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def validate_url(url: str) -> None:
    """
    Валидация URL для защиты от SSRF.

    Args:
        url: Проверяемый URL

    Raises:
        ValueError: Если URL имеет недопустимую схему или хост
    """
    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(
            f"Недопустимая схема URL: '{parsed.scheme}'. "
            f"Разрешены только: {', '.join(ALLOWED_SCHEMES)}"
        )

    if parsed.hostname in BLOCKED_HOSTS:
        raise ValueError(
            f"Заблокированный хост: '{parsed.hostname}'. "
            f"Доступ к внутренним ресурсам запрещён."
        )


def build_pdf_options(
    format: Literal['A4', 'Letter', 'Legal', 'Tabloid'],
    landscape: bool,
    print_background: bool,
    margins: dict[str, str],
    scale: float,
    full_page: bool,
) -> dict:
    """
    Собирает опции для генерации PDF.

    Args:
        format: Формат бумаги
        landscape: Альбомная ориентация
        print_background: Печатать фоны
        margins: Словарь с полями страницы
        scale: Масштаб
        full_page: Режим полной страницы

    Returns:
        Словарь с опциями для page.pdf()
    """
    options: dict = {
        'format': format,
        'landscape': landscape,
        'margin': margins,
        'scale': scale,
    }

    if full_page:
        options.update({
            'print_background': True,
            'prefer_css_page_size': True,
            'display_header_footer': False,
            'tagged': True,
        })
    else:
        options['print_background'] = print_background

    return options


def calculate_scale(content_width: int, scale: float) -> float:
    """
    Вычисляет масштаб для вписывания контента в A4.

    Args:
        content_width: Ширина контента в пикселях
        scale: Текущий масштаб (0.0 = авто)

    Returns:
        Вычисленный масштаб
    """
    available_width = A4_WIDTH_PT - (MARGIN_05CM_PT * 2)

    if content_width > available_width:
        return available_width / content_width
    elif scale == 0.0:
        return 1.0
    return scale


# =============================================================================
# КОНФИГУРАЦИЯ CLI (ИНТЕРФЕЙС КОМАНДНОЙ СТРОКИ)
# =============================================================================

@click.command()
@click.argument('url')
@click.option(
    '-o', '--output',
    type=click.Path(dir_okay=False, writable=True),
    help='Путь к выходному PDF-файлу. По умолчанию: <дата_время>.pdf'
)
@click.option(
    '--wait', '-w',
    type=int,
    default=1000,
    help='Время ожидания в мс перед генерацией PDF (по умолчанию: 1000)'
)
@click.option(
    '--full-page', '-f',
    is_flag=True,
    help='Полная страница с автоматической разбивкой на A4 и авто-масштабированием'
)
@click.option(
    '--landscape', '-l',
    is_flag=True,
    help='Альбомная ориентация страницы (по умолчанию: портретная)'
)
@click.option(
    '--format', '-fmt',
    type=click.Choice(['A4', 'Letter', 'Legal', 'Tabloid']),
    default='A4',
    help='Формат бумаги: A4, Letter, Legal, Tabloid (по умолчанию: A4)'
)
@click.option(
    '--print-background',
    is_flag=True,
    default=True,
    help='Печатать фоновые изображения и цвета (по умолчанию: включено)'
)
@click.option(
    '--margin-top',
    type=str,
    default='0.5cm',
    help='Верхнее поле (по умолчанию: 0.5cm)'
)
@click.option(
    '--margin-bottom',
    type=str,
    default='0.5cm',
    help='Нижнее поле (по умолчанию: 0.5cm)'
)
@click.option(
    '--margin-left',
    type=str,
    default='0.5cm',
    help='Левое поле (по умолчанию: 0.5cm)'
)
@click.option(
    '--margin-right',
    type=str,
    default='0.5cm',
    help='Правое поле (по умолчанию: 0.5cm)'
)
@click.option(
    '--scale', '-s',
    type=float,
    default=0.0,
    help='Масштабирование PDF (0.0=авто, диапазон: 0.5-2.0). По умолчанию: авто-подбор'
)
@click.option(
    '--timeout', '-t',
    type=int,
    default=60000,
    help='Таймаут загрузки страницы в мс (по умолчанию: 60000 = 60 сек)'
)
@click.option(
    '--image-timeout',
    type=int,
    default=DEFAULT_IMAGE_TIMEOUT_MS,
    help=f'Время ожидания загрузки изображений в мс (по умолчанию: {DEFAULT_IMAGE_TIMEOUT_MS})'
)
@click.option(
    '--hide-selectors',
    type=str,
    multiple=True,
    help='CSS-селекторы элементов для скрытия (можно указывать несколько раз)'
)
def url2pdf(
    url: str,
    output: str | None,
    wait: int,
    full_page: bool,
    landscape: bool,
    format: Literal['A4', 'Letter', 'Legal', 'Tabloid'],
    print_background: bool,
    margin_top: str,
    margin_bottom: str,
    margin_left: str,
    margin_right: str,
    scale: float,
    timeout: int,
    image_timeout: int,
    hide_selectors: tuple[str, ...],
) -> None:
    """
    Конвертирует URL в PDF-файл.

    URL — адрес веб-страницы для конвертации.

    Примеры:

        # Базовое использование
        python url2pdf.py https://example.com

        # Сохранить в конкретный файл
        python url2pdf.py https://example.com -o output.pdf

        # Полная страница с авто-масштабированием
        python url2pdf.py https://example.com --full-page

        # Альбомная ориентация
        python url2pdf.py https://example.com --full-page --landscape

        # Скрыть рекламу
        python url2pdf.py https://example.com --hide-selectors ".ad-banner"
    """
    # -------------------------------------------------------------------------
    # ВАЛИДАЦИЯ URL (SSRF защита)
    # -------------------------------------------------------------------------
    try:
        validate_url(url)
    except ValueError as e:
        click.echo(f"❌ Ошибка валидации URL: {e}", err=True)
        raise click.Abort()

    # -------------------------------------------------------------------------
    # ПОДГОТОВКА: генерация имени файла и пути
    # -------------------------------------------------------------------------
    if not output:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output = f"{timestamp}.pdf"

    output_path = Path(output).resolve()

    click.echo(f"📄 Конвертация URL в PDF...")
    click.echo(f"   URL: {url}")
    click.echo(f"   Выход: {output_path}")

    # -------------------------------------------------------------------------
    # ЗАПУСК BROWSER: инициализация Playwright и Chromium
    # -------------------------------------------------------------------------
    browser = None  # Инициализируем для finally

    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport=DESKTOP_VIEWPORT)

            # -----------------------------------------------------------------
            # ЗАГРУЗКА СТРАНИЦЫ
            # -----------------------------------------------------------------
            click.echo(f"   Загрузка страницы...")

            # Устанавливаем viewport в соответствии с режимом
            if full_page and not landscape:
                page.set_viewport_size(A4_PORTRAIT)
            elif full_page and landscape:
                page.set_viewport_size(A4_LANDSCAPE)
            else:
                page.set_viewport_size(DESKTOP_VIEWPORT)

            # -----------------------------------------------------------------
            # CSS ДЛЯ ПЕЧАТИ: принудительное отображение фонов
            # -----------------------------------------------------------------
            page.add_style_tag(content=PRINT_CSS)
            page.emulate_media(media='screen')

            # -----------------------------------------------------------------
            # НАВИГАЦИЯ И ЗАГРУЗКА КОНТЕНТА
            # -----------------------------------------------------------------
            page.goto(url, wait_until='domcontentloaded', timeout=timeout)

            try:
                page.wait_for_load_state('networkidle', timeout=NETWORK_IDLE_TIMEOUT_MS)
            except PlaywrightTimeout:
                click.echo(f"   ⚠️  Таймаут ожидания сети, продолжаем...")

            # -----------------------------------------------------------------
            # ОЖИДАНИЕ ЗАГРУЗКИ ИЗОБРАЖЕНИЙ
            # -----------------------------------------------------------------
            click.echo(f"   Ожидание загрузки изображений ({image_timeout // 1000} сек)...")
            page.wait_for_timeout(image_timeout)

            # -----------------------------------------------------------------
            # АВТО-МАСШТАБИРОВАНИЕ
            # -----------------------------------------------------------------
            content_width = page.evaluate('() => document.documentElement.scrollWidth')
            click.echo(f"   Ширина контента: {content_width}px")

            scale = calculate_scale(content_width, scale)
            if content_width > A4_WIDTH_PT - (MARGIN_05CM_PT * 2):
                click.echo(f"   Авто-масштаб: {scale:.2f}")

            # -----------------------------------------------------------------
            # СКРЫТИЕ ЭЛЕМЕНТОВ
            # -----------------------------------------------------------------
            if hide_selectors:
                for selector in hide_selectors:
                    try:
                        page.locator(selector).evaluate('el => el.style.display = "none"')
                    except Exception:
                        click.echo(f"   ⚠️  Не удалось скрыть: {selector}")

            # -----------------------------------------------------------------
            # ГЕНЕРАЦИЯ PDF
            # -----------------------------------------------------------------
            click.echo(f"   Генерация PDF...")

            margins = {
                'top': margin_top,
                'bottom': margin_bottom,
                'left': margin_left,
                'right': margin_right,
            }

            pdf_options = build_pdf_options(
                format=format,
                landscape=landscape,
                print_background=print_background,
                margins=margins,
                scale=scale,
                full_page=full_page,
            )

            pdf_bytes = page.pdf(path=str(output_path), **pdf_options)

            click.echo(f"✅ Готово! PDF сохранён: {output_path}")
            click.echo(f"   Размер: {output_path.stat().st_size / 1024:.1f} KB")

        except PlaywrightTimeout:
            click.echo(f"❌ Ошибка: Таймаут загрузки страницы ({timeout}мс)", err=True)
            raise click.Abort()
        except Exception as e:
            click.echo(f"❌ Ошибка: {e}", err=True)
            raise click.Abort()
        finally:
            # Закрываем браузер только если он был успешно создан
            if browser is not None:
                browser.close()


# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================
if __name__ == '__main__':
    url2pdf()
