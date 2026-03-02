# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Проект

URL2PDF — это CLI-утилита на Python для конвертации веб-страниц в PDF-файлы с помощью Playwright. Проект состоит из одного основного файла `url2pdf.py`, который содержит всю логику.

## Установка и запуск

```bash
# Установка зависимостей
pip install -r requirements.txt

# Установка браузеров Playwright (обязательно!)
playwright install

# Базовый запуск
python url2pdf.py https://example.com

# С опциями
python url2pdf.py https://example.com --full-page -o output.pdf
```

## Архитектура

Файл `url2pdf.py` построен по линейному принципу с использованием контекстного менеджера Playwright:

1. **CLI-слой** (декораторы `@click.*`) — парсинг аргументов командной строки
2. **Подготовка** — генерация имени выходного файла
3. **Браузер** — запуск headless Chromium через `sync_playwright()`
4. **Загрузка** — навигация по URL с `wait_until='domcontentloaded'`
5. **Ожидание** — 8-секундная пауза для lazy-loading изображений
6. **Масштабирование** — авто-подбор масштаба по ширине контента для A4
7. **Генерация PDF** — через `page.pdf()`

## Ключевые особенности

- **Viewport**: Для `--full-page` устанавливается размер, близкий к A4 (794×1123px для портрета), чтобы сайт рендерился в правильном масштабе.
- **Фоны при печати**: Добавляется CSS с `-webkit-print-color-adjust: exact` для сохранения фоновых изображений.
- **Media emulation**: Используется `emulate_media(media='screen')` вместо 'print' для сохранения визуального стиля.
- **Авто-масштаб**: Вычисляется как `available_width / content_width` (A4 = 595pt минус поля).
- **Скрытие элементов**: CSS-селекторы применяются через `display = "none"` перед генерацией PDF.

## Зависимости

- `playwright>=1.58.0` — управление браузером
- `click>=8.3.1` — CLI-интерфейс
