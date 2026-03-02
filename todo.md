# TODO: Улучшения url2pdf.py

## ✅ Выполнено

### 1. [Безопасность] Валидация URL (SSRF защита) ✅
- Добавлена функция `validate_url()` с проверкой схемы и хоста
- Блокируются: localhost, 127.0.0.1, 0.0.0.0, ::1
- Разрешены только: http, https

### 2. [Надёжность] Исправить race condition в finally ✅
- `browser` инициализируется как `None` перед использованием
- Проверка `if browser is not None` перед закрытием

### 3. [Качество] Добавить type hints ✅
- Все параметры функции аннотированы
- Использованы современные типы: `str | None`, `Literal`, `tuple[str, ...]`
- Добавлен `from __future__ import annotations`

### 4. [Качество] Вынести магические числа в константы ✅
- `A4_PORTRAIT`, `A4_LANDSCAPE` — размеры viewport
- `A4_WIDTH_PT`, `MARGIN_05CM_PT` — размеры для PDF
- `DESKTOP_VIEWPORT` — стандартный размер
- `PRINT_CSS` — CSS для печати

### 5. [Рефакторинг] Устранить дублирование в page.pdf() ✅
- Создана функция `build_pdf_options()` для сборки опций
- Использован распаковщик `**pdf_options` при вызове

### 6. [Производительность] Сделать задержку изображений настраиваемой ✅
- Добавлена опция CLI `--image-timeout`
- Константа `DEFAULT_IMAGE_TIMEOUT_MS = 8000`

### 7. [Рефакторинг] Вынести расчёт масштаба в отдельную функцию ✅
- Создана функция `calculate_scale(content_width, scale)`

---

## 🟢 Осталось (низкий приоритет)

### 8. [Архитектура] Выделить логику в классы
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

### 9. [Тестирование] Добавить unit-тесты
- Создать `tests/test_url2pdf.py`
- Покрыть основную логику тестами
- Использовать pytest для запуска

---

## 📊 Статистика

| Статус | Количество |
|--------|------------|
| ✅ Выполнено | 7 |
| 🟢 Осталось | 2 |
| **Итого** | **9** |
