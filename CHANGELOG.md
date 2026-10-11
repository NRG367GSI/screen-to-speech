# Changelog

## [Unreleased] — feature/ui-aimp

### Добавлено
- **Глобальные хоткеи через WinAPI `RegisterHotKey`** (`ui/hotkeys.py`):
  - Работает поверх игр и приложений, не требует фокуса.
  - Отдельный поток: `RegisterHotKey` + `GetMessageW` в одном потоке.
  - Сигнал `fired(name)` → `pyqtSignal` в GUI-поток.
- **Новая схема хоткеев:** `Ctrl+Shift+M` (моно), `Ctrl+Shift+↓` (снять), `Ctrl+Shift+→` (поли), `Ctrl+Shift+↑` (рамка), `Ctrl+Shift+N` (сессия), `Ctrl+Shift+O` (настройки).
- **Лог хоткеев** — `logs/hotkeys.log`.
- **Поле `translate`** в `Preset` — задел под локальный переводчик.
- **`tools/snapshot.py`** — снимок кода в `snapshot.md` для переезда между сессиями.
- **`JOURNAL.md`** — краткий журнал сессий (по одной строке на шаг).

### Изменено
- `keyboard` → `RegisterHotKey` (WinAPI). `keyboard` больше не используется.
- Хоткеи ушли с `Ctrl+Alt+*` (конфликт с Punto Switcher) и `Alt+Shift+*` (конфликт со сменой языка) на `Ctrl+Shift+*`.
- Убраны дубли хоткеев (`capture_only`, `recognize_only`).

### Удалено
- `test_hotkey.py`, `test_hotkeys2.py` — диагностические скрипты.
- Ветка `feature/conveyors` — влита в `main`.

## [v2.1] — feature/player → main

### Добавлено
- Плашка (`ui/widget.py`): 4 кнопки 👁📸▶⚙, счётчик скринов, тултипы.
- Кнопка сворачивания `➖` в большое окно → виджет.

### Изменено
- Хоткеи: `Ctrl+Alt+Space` (моно), `Ctrl+Alt+↓` (снять), `Ctrl+Alt+→` (поли), `Ctrl+Alt+↑` (рамка), `Ctrl+Alt+N` (сессия).

## [v2.0] — архитектура v2

### Добавлено
- Модульная структура: `core/`, `ui/`, `presets/`, `sessions/`, `logs/`.
- `core/image_utils.py` — подготовка изображений.
- `core/session.py` — управление папкой сессии, `short_id`, `manifest.json`.
- `core/ocr.py` — OCR через LM Studio (PaddleOCR-VL), fuzzy-фильтр дублей (0.75) + по словам (70%).
- `core/tts.py` — Silero TTS, `normalize_for_tts`, `sample_rate=24000`.
- `ui/thumbnail.py`, `ui/frame_window.py`, `ui/control_panel.py`, `ui/widget.py`.
- `main.py` — точка входа.
- Пресеты (`preset_manager.py`): геометрия, голоса, скорость, хоткеи.

### Сохранено
- v1 (`ocr_tts_app.py` + `preset_manager.py`) как эталон.