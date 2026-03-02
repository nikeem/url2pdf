# TODO: Улучшения url2pdf.py

## 🔴 Высокий приоритет (безопасность и надёжность)

### 1. [Безопасность] Валидация URL (SSRF защита)
- **Проблема:** Нет проверки URL — можно обращаться к внутренним ресурсам
- **Решение:** Добавить валидацию схемы (только http/https) и блокировку localhost
- **Файл:** url2pdf.py:199-200

```python
from urllib.parse import urlparse

ALLOWED_SCHEMES = {'http', 'https'}
BLOCKED_HOSTS = {'localhost', '127.0.0.1', '0.0.0.0'}

def validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"Недопустимая схема: {parsed.scheme}")
    if parsed.hostname in BLOCKED_HOSTS:
        raise ValueError(f"Заблокированный хост: {parsed.hostname}")
```

### 2. [Надёжность] Исправить race condition в finally
- **Проблема:** Если `p.chromium.launch()` упадёт, `browser` не существует и `finally` тоже упадёт
- **Решение:** Проверить существование `browser` перед закрытием
- **Файл:** url2pdf.py:306-308

```python
finally:
    if 'browser' in locals():
        browser.close()
```

---

## 🟡 Средний приоритет (качество кода)

### 3. [Качество] Добавить type hints
- **Проблема:** Отсутствие аннотаций типов ухудшает читаемость и IDE-поддержку
- **Решение:** Добавить type hints для всех параметров функции
- **Файл:** url2pdf.py:103-107

```python
from typing import Tuple

def url2pdf(
    url: str,
    output: str | None,
    wait: int,
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
    hide_selectors: Tuple[str, ...]
) -> None:
```

### 4. [Качество] Вынести магические числа в константы
- **Проблема:** Числа 794, 1123, 595, 38 неясны без контекста
- **Решение:** Создать константы с документацией
- **Файл:** url2pdf.py:167, 169, 226-228

```python
# A4 размеры при 96 DPI (для viewport)
A4_PORTRAIT = {'width': 794, 'height': 1123}
A4_LANDSCAPE = {'width': 1123, 'height': 794}

# A4 в пунктах при 72 DPI (для PDF)
A4_WIDTH_PT = 595
MARGIN_05CM_PT = 38
```

### 5. [Рефакторинг] Устранить дублирование в page.pdf()
- **Проблема:** Два почти идентичных вызова с минимальными различиями
- **Решение:** Вынести общую логику в отдельную функцию
- **Файл:** url2pdf.py:262-292

```python
def build_pdf_options(full_page: bool, format: str, landscape: bool,
                      print_background: bool, margins: dict, scale: float) -> dict:
    options = {
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
```

### 6. [Производительность] Сделать задержку изображений настраиваемой
- **Проблема:** Фиксированные 8 секунд не оптимальны для всех сайтов
- **Решение:** Добавить CLI опцию `--image-timeout`
- **Файл:** url2pdf.py:214-215

```python
@click.option('--image-timeout', type=int, default=8000,
              help='Время ожидания загрузки изображений в мс (по умолчанию: 8000)')
```

---

## 🟢 Низкий приоритет (архитектура)

### 7. [Архитектура] Выделить логику в классы
- **Проблема:** Весь код в одной функции, сложно тестировать отдельные компоненты
- **Решение:** Создать класс `URL2PDFConverter` с методами

```python
class URL2PDFConverter:
    def __init__(self, config: dict):
        self.config = config

    def validate_url(self, url: str) -> None:
        ...

    def calculate_scale(self, content_width: int) -> float:
        ...

    def generate_pdf(self, url: str, output_path: Path) -> None:
        ...
```

### 8. [Тестирование] Добавить unit-тесты
- Создать `tests/test_url2pdf.py`
- Покрыть основную логику тестами
- Использовать pytest для запуска

---

## 📊 Статистика

| Приоритет | Количество задач |
|-----------|------------------|
| 🔴 Высокий | 2 |
| 🟡 Средний | 4 |
| 🟢 Низкий | 2 |
| **Итого** | **8** |
