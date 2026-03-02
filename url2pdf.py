#!/usr/bin/env python3
"""
URL2PDF — Конвертер веб-страниц в PDF.

Создаёт качественные PDF-файлы из веб-страниц с помощью Playwright.
Поддерживает полную прокрутку страницы, фоновые изображения,
автоматическое масштабирование и разбивку на страницы A4.

Пример использования:
    python url2pdf.py https://example.com --full-page -o output.pdf

Автор: URL2PDF Project
Лицензия: MIT
"""

import click
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from pathlib import Path
from datetime import datetime


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
    '--hide-selectors',
    type=str,
    multiple=True,
    help='CSS-селекторы элементов для скрытия (можно указывать несколько раз)'
)
def url2pdf(
    url, output, wait, full_page, landscape, format,
    print_background, margin_top, margin_bottom,
    margin_left, margin_right, scale, timeout, hide_selectors
):
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
    # ---------------------------------------------------------------------
    # ПОДГОТОВКА: генерация имени файла и пути
    # ---------------------------------------------------------------------
    if not output:
        # Если имя файла не указано, генерируем по текущей дате/времени
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output = f"{timestamp}.pdf"

    # Преобразуем в абсолютный путь для надёжности
    output_path = Path(output).resolve()

    # Выводим информацию о задаче
    click.echo(f"📄 Конвертация URL в PDF...")
    click.echo(f"   URL: {url}")
    click.echo(f"   Выход: {output_path}")

    # ---------------------------------------------------------------------
    # ЗАПУСК BROWSER: инициализация Playwright и Chromium
    # ---------------------------------------------------------------------
    with sync_playwright() as p:
        # Запускаем Chromium в headless-режиме (без графического интерфейса)
        browser = p.chromium.launch(headless=True)

        # Создаём новую страницу с viewport по умолчанию
        page = browser.new_page(viewport={'width': 1920, 'height': 1080})

        try:
            # -------------------------------------------------------------
            # ЗАГРУЗКА СТРАНИЦЫ
            # -------------------------------------------------------------
            click.echo(f"   Загрузка страницы...")

            # Устанавливаем viewport в соответствии с режимом
            # Для full-page используем размеры, близкие к A4, чтобы сайт
            # рендерился в правильном масштабе
            if full_page and not landscape:
                # Портретный A4: 794 x 1123 пикселей при 96 DPI
                page.set_viewport_size({'width': 794, 'height': 1123})
            elif full_page and landscape:
                # Альбомный A4: 1123 x 794 пикселей
                page.set_viewport_size({'width': 1123, 'height': 794})
            else:
                # Стандартный desktop viewport
                page.set_viewport_size({'width': 1920, 'height': 1080})

            # -------------------------------------------------------------
            # CSS ДЛЯ ПЕЧАТИ: принудительное отображение фонов
            # -------------------------------------------------------------
            # Добавляем CSS для сохранения фоновых изображений и цветов
            # при печати. По умолчанию браузеры экономят краску и убирают фоны.
            page.add_style_tag(content='''
                * {
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                    color-adjust: exact !important;
                }
                body {
                    -webkit-print-color-adjust: exact !important;
                    print-color-adjust: exact !important;
                }
            ''')

            # Эмулируем media='screen' вместо 'print' для сохранения
            # визуального стиля страницы (фонов, градиентов и т.д.)
            page.emulate_media(media='screen')

            # -------------------------------------------------------------
            # НАВИГАЦИЯ И ЗАГРУЗКА КОНТЕНТА
            # -------------------------------------------------------------
            # Загружаем страницу, ждём DOMContentLoaded (быстрее чем full load)
            page.goto(url, wait_until='domcontentloaded', timeout=timeout)

            # Ждём networkidle (все сетевые запросы завершены)
            # с отдельным таймаутом, чтобы не блокировать основную загрузку
            try:
                page.wait_for_load_state('networkidle', timeout=15000)
            except PlaywrightTimeout:
                click.echo(f"   ⚠️  Таймаут ожидания сети, продолжаем...")

            # -------------------------------------------------------------
            # ОЖИДАНИЕ ЗАГРУЗКИ ИЗОБРАЖЕНИЙ
            # -------------------------------------------------------------
            # Критически важно для страниц с ленивой загрузкой (lazy loading)
            # 8 секунд достаточно для большинства современных сайтов
            click.echo(f"   Ожидание загрузки изображений (8 сек)...")
            page.wait_for_timeout(8000)

            # -------------------------------------------------------------
            # АВТО-МАСШТАБИРОВАНИЕ
            # -------------------------------------------------------------
            # Получаем реальную ширину контента страницы
            content_width = page.evaluate('() => document.documentElement.scrollWidth')
            click.echo(f"   Ширина контента: {content_width}px")

            # Вычисляем доступную ширину A4 (595 точек при 72 DPI)
            # с учётом полей (0.5cm ≈ 38 пикселей)
            a4_width_px = 595
            margin_px = 38  # ~0.5cm в пикселях при 72 DPI
            available_width = a4_width_px - (margin_px * 2)

            # Авто-подбор масштаба: если контент шире доступного места,
            # уменьшаем масштаб для вписывания в A4
            if content_width > available_width:
                auto_scale = available_width / content_width
                click.echo(f"   Авто-масштаб: {auto_scale:.2f} (контент {content_width}px > доступного {available_width}px)")
                scale = auto_scale
            elif scale == 0.0:
                # Если масштаб не указан и контент влезает — используем 1.0
                scale = 1.0

            # -------------------------------------------------------------
            # СКРЫТИЕ ЭЛЕМЕНТОВ
            # -------------------------------------------------------------
            # Скрываем ненужные элементы (реклама, навигация и т.п.)
            if hide_selectors:
                for selector in hide_selectors:
                    try:
                        page.locator(selector).evaluate('el => el.style.display = "none"')
                    except Exception:
                        click.echo(f"   ⚠️  Не удалось скрыть: {selector}")

            # -------------------------------------------------------------
            # ГЕНЕРАЦИЯ PDF
            # -------------------------------------------------------------
            click.echo(f"   Генерация PDF...")

            if full_page:
                # Режим полной страницы:
                # - Playwright автоматически разбивает на страницы A4
                # - Включены фоновые изображения
                # - Без колонтитулов
                # - С тегированием для доступности
                pdf_bytes = page.pdf(
                    path=str(output_path),
                    format=format,
                    landscape=landscape,
                    print_background=True,  # Всегда включено для full-page
                    margin={
                        'top': margin_top,
                        'bottom': margin_bottom,
                        'left': margin_left,
                        'right': margin_right,
                    },
                    prefer_css_page_size=True,  # Учитывать CSS @page
                    display_header_footer=False,  # Без колонтитулов
                    tagged=True,  # Доступный PDF с тегами
                    scale=scale,  # Применить вычисленный масштаб
                )
            else:
                # Обычный режим: только видимая область viewport
                pdf_bytes = page.pdf(
                    path=str(output_path),
                    format=format,
                    landscape=landscape,
                    print_background=print_background,
                    margin={
                        'top': margin_top,
                        'bottom': margin_bottom,
                        'left': margin_left,
                        'right': margin_right,
                    },
                    scale=scale,
                )

            # Вывод успешного завершения
            click.echo(f"✅ Готово! PDF сохранён: {output_path}")
            click.echo(f"   Размер: {output_path.stat().st_size / 1024:.1f} KB")

        except PlaywrightTimeout:
            # Обработка таймаута загрузки
            click.echo(f"❌ Ошибка: Таймаут загрузки страницы ({timeout}мс)", err=True)
            raise click.Abort()
        except Exception as e:
            # Обработка прочих ошибок
            click.echo(f"❌ Ошибка: {e}", err=True)
            raise click.Abort()
        finally:
            # Закрываем браузер в любом случае (освобождение ресурсов)
            browser.close()


# =============================================================================
# ТОЧКА ВХОДА
# =============================================================================
if __name__ == '__main__':
    url2pdf()
