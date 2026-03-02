#!/usr/bin/env python3
"""
URL2PDF — Web-интерфейс на Streamlit.

Конвертер веб-страниц в PDF с веб-интерфейсом.
"""

from __future__ import annotations

import streamlit as st
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from typing import Literal
import io
import subprocess
import sys


# =============================================================================
# АВТОМАТИЧЕСКАЯ УСТАНОВКА БРАУЗЕРА (для Streamlit Cloud)
# =============================================================================

def install_playwright_browsers():
    """Устанавливает браузеры Playwright при первом запуске."""
    try:
        with sync_playwright() as p:
            # Проверяем, установлен ли браузер
            p.chromium.launch(headless=True).close()
    except Exception:
        # Если браузер не установлен, устанавливаем его
        st.warning("📦 Установка браузера Chromium... Это может занять минуту.")
        try:
            subprocess.run(
                [sys.executable, "-m", "playwright", "install", "chromium"],
                check=True,
                capture_output=True
            )
            st.success("✅ Браузер установлен!")
        except subprocess.CalledProcessError as e:
            st.error(f"❌ Ошибка установки браузера: {e}")
            st.stop()


# Устанавливаем браузер при запуске
install_playwright_browsers()


# =============================================================================
# КОНСТАНТЫ
# =============================================================================

# A4 размеры при 96 DPI (для viewport)
A4_PORTRAIT: dict[str, int] = {'width': 794, 'height': 1123}
A4_LANDSCAPE: dict[str, int] = {'width': 1123, 'height': 794}

# A4 в пунктах при 72 DPI (для PDF)
A4_WIDTH_PT: int = 595
MARGIN_05CM_PT: int = 38

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

# Таймаут ожидания сети
NETWORK_IDLE_TIMEOUT_MS: int = 15000


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================

def validate_url(url: str) -> tuple[bool, str]:
    """
    Валидация URL для защиты от SSRF.

    Returns:
        (is_valid, error_message)
    """
    if not url:
        return False, "URL не может быть пустым"

    parsed = urlparse(url)

    if parsed.scheme not in ALLOWED_SCHEMES:
        return False, f"Недопустимая схема: '{parsed.scheme}'. Разрешены только: http, https"

    if parsed.hostname in BLOCKED_HOSTS:
        return False, f"Заблокированный хост: '{parsed.hostname}'. Доступ к внутренним ресурсам запрещён"

    return True, ""


def build_pdf_options(
    format: Literal['A4', 'Letter', 'Legal', 'Tabloid'],
    landscape: bool,
    print_background: bool,
    margins: dict[str, str],
    scale: float,
    full_page: bool,
) -> dict:
    """Собирает опции для генерации PDF."""
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
    """Вычисляет масштаб для вписывания контента в A4."""
    available_width = A4_WIDTH_PT - (MARGIN_05CM_PT * 2)

    if content_width > available_width:
        return available_width / content_width
    elif scale == 0.0:
        return 1.0
    return scale


def generate_pdf(
    url: str,
    full_page: bool,
    landscape: bool,
    format: str,
    print_background: bool,
    margin_top: str,
    margin_bottom: str,
    margin_left: str,
    margin_right: str,
    scale: float,
    timeout: int,
    image_timeout: int,
    hide_selectors: list[str],
    progress_callback=None,
) -> tuple[bytes, str, str]:
    """
    Генерирует PDF из URL.

    Returns:
        (pdf_bytes, filename, error_message)
    """
    browser = None

    with sync_playwright() as p:
        try:
            if progress_callback:
                progress_callback(10, "Запуск браузера...")

            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport=DESKTOP_VIEWPORT)

            if progress_callback:
                progress_callback(20, "Загрузка страницы...")

            # Устанавливаем viewport
            if full_page and not landscape:
                page.set_viewport_size(A4_PORTRAIT)
            elif full_page and landscape:
                page.set_viewport_size(A4_LANDSCAPE)
            else:
                page.set_viewport_size(DESKTOP_VIEWPORT)

            # CSS для печати
            page.add_style_tag(content=PRINT_CSS)
            page.emulate_media(media='screen')

            # Навигация
            page.goto(url, wait_until='domcontentloaded', timeout=timeout)

            if progress_callback:
                progress_callback(40, "Ожидание загрузки контента...")

            try:
                page.wait_for_load_state('networkidle', timeout=NETWORK_IDLE_TIMEOUT_MS)
            except PlaywrightTimeout:
                pass

            if progress_callback:
                progress_callback(60, f"Ожидание изображений ({image_timeout // 1000} сек)...")

            page.wait_for_timeout(image_timeout)

            # Авто-масштабирование
            content_width = page.evaluate('() => document.documentElement.scrollWidth')
            scale = calculate_scale(content_width, scale)

            # Скрытие элементов
            if hide_selectors:
                for selector in hide_selectors:
                    try:
                        page.locator(selector).evaluate('el => el.style.display = "none"')
                    except Exception:
                        pass

            if progress_callback:
                progress_callback(80, "Генерация PDF...")

            # Генерация PDF
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

            pdf_bytes = page.pdf(**pdf_options)

            if progress_callback:
                progress_callback(100, "Готово!")

            # Генерируем имя файла
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"url2pdf_{timestamp}.pdf"

            return pdf_bytes, filename, ""

        except PlaywrightTimeout:
            return None, "", f"Таймаут загрузки страницы ({timeout}мс)"
        except Exception as e:
            return None, "", str(e)
        finally:
            if browser is not None:
                browser.close()


# =============================================================================
# STREAMLIT ИНТЕРФЕЙС
# =============================================================================

st.set_page_config(
    page_title="URL2PDF",
    page_icon="📄",
    layout="centered",
    initial_sidebar_state="expanded"
)

st.title("📄 URL2PDF")
st.markdown("Конвертер веб-страниц в качественные PDF-файлы")

# Настройки в сайдбаре
st.sidebar.header("⚙️ Настройки")

# Базовые настройки
url_input = st.text_input(
    "URL страницы",
    placeholder="https://example.com",
    help="Введите полный URL страницы (включая https://)"
)

col1, col2 = st.columns(2)

with col1:
    full_page = st.checkbox("Полная страница", value=True, help="Вся страница с разбивкой на A4")
    landscape = st.checkbox("Альбомная ориентация", value=False)

with col2:
    print_bg = st.checkbox("Фоновые изображения", value=True, help="Сохранять фоны и градиенты")

# Формат бумаги
paper_format = st.selectbox(
    "Формат бумаги",
    ['A4', 'Letter', 'Legal', 'Tabloid'],
    index=0
)

# Поля
st.subheader("Поля страницы")
col1, col2, col3, col4 = st.columns(4)

with col1:
    margin_top = st.text_input("Верх", value="0.5cm")
with col2:
    margin_bottom = st.text_input("Низ", value="0.5cm")
with col3:
    margin_left = st.text_input("Лево", value="0.5cm")
with col4:
    margin_right = st.text_input("Право", value="0.5cm")

# Дополнительно
st.subheader("Дополнительные настройки")

col1, col2 = st.columns(2)

with col1:
    scale = st.slider(
        "Масштаб",
        min_value=0.5,
        max_value=2.0,
        value=1.0,
        step=0.1,
        help="0.5 — мелко, 1.0 — оригинал, 2.0 — крупно. При авто-масштабе игнорируется."
    )

with col2:
    auto_scale = st.checkbox("Авто-масштаб", value=True, help="Подгонять по ширине страницы")

# Скрываемые элементы
hide_selectors_input = st.text_input(
    "CSS-селекторы для скрытия",
    placeholder=".ad-banner, .sidebar, nav",
    help="Через запятую: .ad-banner, .sidebar"
)

# Таймауты
with st.expander("⏱️ Таймауты (для медленных сайтов)"):
    col1, col2 = st.columns(2)
    with col1:
        timeout = st.slider("Таймаут загрузки (сек)", 10, 120, 60)
    with col2:
        image_timeout = st.slider("Ожидание изображений (сек)", 1, 30, 8)

# Разделитель
st.markdown("---")

# Кнопка генерации
generate_btn = st.button("🚀 Создать PDF", type="primary", use_container_width=True)

# Результат
if generate_btn:
    # Валидация URL
    is_valid, error_msg = validate_url(url_input)

    if not is_valid:
        st.error(f"❌ {error_msg}")
        st.stop()

    # Подготовка селекторов
    hide_selectors = [s.strip() for s in hide_selectors_input.split(',') if s.strip()] if hide_selectors_input else []

    # Авто-масштаб
    final_scale = 0.0 if auto_scale else scale

    # Прогресс бар
    progress_bar = st.progress(0)
    status_text = st.empty()

    def progress_callback(value: int, message: str):
        progress_bar.progress(value / 100)
        status_text.text(message)

    # Генерация
    try:
        pdf_bytes, filename, error = generate_pdf(
            url=url_input,
            full_page=full_page,
            landscape=landscape,
            format=paper_format,
            print_background=print_bg,
            margin_top=margin_top,
            margin_bottom=margin_bottom,
            margin_left=margin_left,
            margin_right=margin_right,
            scale=final_scale,
            timeout=timeout * 1000,
            image_timeout=image_timeout * 1000,
            hide_selectors=hide_selectors,
            progress_callback=progress_callback,
        )

        if error:
            st.error(f"❌ Ошибка: {error}")
        else:
            status_text.text("✅ Готово!")
            st.success(f"PDF успешно создан: **{filename}** ({len(pdf_bytes) / 1024:.1f} KB)")

            # Кнопка скачивания
            st.download_button(
                label="📥 Скачать PDF",
                data=pdf_bytes,
                file_name=filename,
                mime="application/pdf",
                use_container_width=True
            )

    except Exception as e:
        st.error(f"❌ Непредвиденная ошибка: {e}")

# Информация
st.markdown("---")
st.markdown("""
### 💡 Советы

- **Полная страница** — используйте для статей и документации
- **Авто-масштаб** — автоматически подстраивает контент по ширине
- **Селекторы** — скройте рекламу и навигацию для чистого PDF
- **Таймауты** — увеличьте для медленных сайтов с большим контентом
""")

# Footer
st.markdown("""
---
<div style='text-align: center;'>
    <small>Powered by Playwright & Streamlit</small><br>
    <small style='color: gray;'>© 2025 Nikita Emelyanov | <a href='https://t.me/emelyanov_na' target='_blank'>t.me/emelyanov_na</a></small>
</div>
""", unsafe_allow_html=True)
