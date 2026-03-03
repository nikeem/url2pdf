# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Проект

URL2PDF — это инструмент на Python для конвертации веб-страниц в PDF-файлы с помощью Playwright. Проект включает две версии:

- **CLI** (`url2pdf.py`) — консольная утилита
- **Web** (`streamlit_app.py`) — веб-интерфейс на Streamlit

## Установка и запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Установка браузеров Playwright (обязательно!)
playwright install

# CLI-версия
python url2pdf.py https://example.com

# Web-версия
streamlit run streamlit_app.py
```

## Архитектура

### Общие компоненты

Обе версии используют общие вспомогательные функции:
- `validate_url()` — SSRF защита (блокирует localhost/internal)
- `build_pdf_options()` — сбор опций для генерации PDF
- `calculate_scale()` — авто-масштабирование под A4

### CLI (url2pdf.py)

1. **CLI-слой** (`@click.*`) — парсинг аргументов
2. **Валидация** — проверка URL на SSRF
3. **Браузер** — запуск headless Chromium
4. **Загрузка** — навигация с `wait_until='domcontentloaded'`
5. **Ожидание** — настраиваемая пауза для lazy-loading изображений
6. **Масштабирование** — авто-подбор по ширине контента
7. **Генерация PDF** — через `page.pdf()`

### Web (streamlit_app.py)

- **@st.cache_resource** — кэширование установки браузера
- **progress_callback** — отображение прогресса
- **validate_url()** — валидация с проверкой `hostname is None`
- **disabled кнопка** — отключена при пустом URL

## Ключевые особенности

- **Viewport**: Для `--full-page` устанавливается A4-размер (794×1123px)
- **Фоны**: CSS с `-webkit-print-color-adjust: exact`
- **Media emulation**: `emulate_media(media='screen')` для сохранения стиля
- **Авто-масштаб**: `available_width / content_width` (A4 = 595pt минус поля)
- **SSRF защита**: Блокировка localhost, 127.0.0.1, 0.0.0.0, ::1

## Зависимости

- `playwright>=1.58.0` — управление браузером
- `click>=8.3.1` — CLI-интерфейс
- `streamlit>=1.28.0` — веб-интерфейс

## Файлы

| Файл | Описание |
|------|----------|
| `url2pdf.py` | CLI-версия |
| `streamlit_app.py` | Web-версия |
| `requirements.txt` | Python-зависимости |
| `packages.txt` | Системные зависимости для Linux (Streamlit Cloud) |
