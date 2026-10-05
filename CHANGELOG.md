# Changelog

## [Unreleased] — feature/conveyors

### Добавлено
- Моноконвейер (`🎬`): снять + распознать + озвучить + автозакрытие сессии.
- Поликонвейер (`📸` + `▶`): накопление скринов в очередь, OCR по одному, TTS, автозакрытие.
- Короткий ID сессии (`short_id`) и `manifest.json` в каждой сессии.
- Построчный fuzzy-фильтр дубликатов (0.75) + проверка по словам (70%) для длинных строк.
- `normalize_for_tts`: склейка переносов, фильтр токенов без букв, `...` → `…`.
- `sample_rate` снижен с 48000 до 24000 (файлы в 2 раза меньше).
- Ручка перетаскивания рамки в верхнем левом углу.
- Плашка (`ui/widget.py`): компактный режим с кнопками 👁 ▶ 🔁 🆕 ⚙.
- Хоткеи: `Ctrl+Alt+↓` (снять в очередь), `Ctrl+Alt+→` (запуск поликонвейера).
- Иконки вместо текста в верхней панели большого окна + тултипы.
- Кнопки удаления аудио: 🗑 (удалить выбранное), ✕ (очистить список).
- Git-репозиторий, `.gitignore`, GitHub: https://github.com/NRG367GSI/screen-to-speech

### Изменено
- Хоткеи переведены с `QTimer.singleShot` на `pyqtSignal` — стабильнее.
- `FrameWindow` — дочерний `ControlPanel` (закрывается с главным).
- Закрытие главного окна завершает всё приложение.

### Удалено
- Старые методы `full_cycle`, `capture_only`, `process_session`, `_process_worker`.
- `next_voice` / `prev_voice` из хоткеев (голос меняется в большом окне).

## [v2.0] — архитектура v2

### Добавлено
- Модульная структура: `core/`, `ui/`, `presets/`, `sessions/`, `logs/`.
- `core/image_utils.py` — подготовка изображений.
- `core/session.py` — управление папкой сессии.
- `core/ocr.py` — OCR через LM Studio (PaddleOCR-VL).
- `core/tts.py` — Silero TTS.
- `ui/thumbnail.py`, `ui/frame_window.py`, `ui/control_panel.py`, `ui/widget.py`.
- `main.py` — точка входа.

### Сохранено
- v1 (`ocr_tts_app.py` + `preset_manager.py`) как эталон.