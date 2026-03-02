# URL2PDF

Конвертер веб-страниц в качественные PDF-файлы с помощью Playwright.

## 📖 Описание

URL2PDF создаёт PDF-документы из веб-страниц с сохранением:
- Фоновых изображений и цветов
- Оригинальной вёрстки
- Автоматической разбивкой на страницы A4
- Авто-масштабированием под ширину страницы

## ⚙️ Установка

```bash
# Перейти в директорию проекта
cd url2pdf

# Установить зависимости Python
pip install -r requirements.txt

# Установить браузеры Playwright (Chromium)
playwright install
```

### Требования
- Python 3.8+
- pip
- Playwright (устанавливается через requirements.txt)

## 🚀 Быстрый старт

### Базовое использование

```bash
# Конвертировать страницу (сохранит в текущую директорию)
python url2pdf.py https://example.com

# Конвертировать с именем файла
python url2pdf.py https://example.com -o output.pdf

# Полная страница с авто-масштабированием
python url2pdf.py https://example.com --full-page
```

## 📋 Опции

| Опция | Краткая | Описание | По умолчанию |
|-------|---------|----------|--------------|
| `--output` | `-o` | Путь к выходному PDF-файлу | `<дата_время>.pdf` |
| `--full-page` | `-f` | Полная страница с разбивкой на A4 и авто-масштабом | выключено |
| `--landscape` | `-l` | Альбомная ориентация | портретная |
| `--format` | `-fmt` | Формат бумаги: A4, Letter, Legal, Tabloid | A4 |
| `--scale` | `-s` | Масштаб (0.0=авто, 0.5-2.0) | авто-подбор |
| `--margin-top` | — | Верхнее поле | 0.5cm |
| `--margin-bottom` | — | Нижнее поле | 0.5cm |
| `--margin-left` | — | Левое поле | 0.5cm |
| `--margin-right` | — | Правое поле | 0.5cm |
| `--timeout` | `-t` | Таймаут загрузки (мс) | 60000 (60 сек) |
| `--hide-selectors` | — | CSS-селекторы для скрытия | — |
| `--wait` | `-w` | Доп. ожидание перед генерацией (мс) | 1000 |

## 📚 Примеры использования

### 1. Статья с полной прокруткой

```bash
python url2pdf.py https://habr.com/ru/article/123456 --full-page -o article.pdf
```

### 2. Документация в альбомном формате

```bash
python url2pdf.py https://docs.python.org/3/ --landscape --format Letter
```

### 3. Страница без рекламы и баннеров

```bash
python url2pdf.py https://site.com \
    --full-page \
    --hide-selectors ".ad-banner" \
    --hide-selectors ".sidebar" \
    --hide-selectors "nav"
```

### 4. С ручным масштабированием

Если авто-масштаб слишком мелкий, укажите вручную:

```bash
# Крупнее (80% от оригинала)
python url2pdf.py https://example.com --full-page --scale 0.8

# Мельче (50% от оригинала)
python url2pdf.py https://example.com --full-page --scale 0.5
```

### 5. С нулевыми полями

```bash
python url2pdf.py https://example.com \
    --full-page \
    --margin-top 0cm \
    --margin-bottom 0cm \
    --margin-left 0cm \
    --margin-right 0cm
```

### 6. Для сложных страниц (дольше загрузка)

```bash
python url2pdf.py https://heavy-site.com \
    --full-page \
    --timeout 90000 \
    -o heavy.pdf
```

## ⚙️ Настройки по умолчанию

| Параметр | Значение |
|----------|----------|
| **Формат бумаги** | A4 |
| **Ориентация** | Портретная |
| **Поля** | 0.5cm со всех сторон |
| **Масштаб** | Авто (подбирается по ширине контента) |
| **Таймаут загрузки** | 60 секунд |
| **Ожидание изображений** | 8 секунд |
| **Фоновые изображения** | Включены |
| **Колонтитулы** | Отключены |

## 🔧 Как это работает

1. **Запуск браузера**: Playwright запускает headless-версию Chromium
2. **Загрузка страницы**: Переход по URL с ожиданием DOMContentLoaded
3. **Ожидание контента**: 8 секунд на загрузку изображений (включая lazy-loading)
4. **Применение стилей**: CSS для сохранения фонов при печати
5. **Авто-масштабирование**: Вычисление ширины контента и подбор масштаба для A4
6. **Генерация PDF**: Создание PDF с разбивкой на страницы

## 🛠️ Решение проблем

### Изображения не загружаются
Увеличьте время ожидания:
```bash
python url2pdf.py https://example.com --full-page --timeout 90000
```

### Страница обрезается справа
Используйте ручной масштаб:
```bash
python url2pdf.py https://example.com --full-page --scale 0.7
```

### Фоны не отображаются
Проверьте, что используется `--full-page` (фоны включены по умолчанию)

### Слишком мелко
Отключите авто-масштаб и укажите свой:
```bash
python url2pdf.py https://example.com --full-page --scale 0.8
```

### Таймаут загрузки
Для медленных сайтов увеличьте таймаут:
```bash
python url2pdf.py https://slow-site.com --timeout 120000
```

## 📁 Структура проекта

```
url2pdf/
├── url2pdf.py          # Основной скрипт
├── requirements.txt    # Зависимости Python
├── README.md          # Документация
├── venv/              # Виртуальное окружение
└── *.pdf              # Сгенерированные PDF-файлы
```
