# Journal

Краткий журнал сессий. Одна строка = один шаг. Формат: что сделано → к чему привело.

## 2026-10-20 — LMS automation + Silero v5 + переезд

- Silero TTS: `v4_ru` → `v5_5_ru` (авто-ударения в омографах, скорость выше).
- `core/lmstudio_control.py`: автозапуск сервера, автозагрузка модели (`--identifier`), выгрузка при выходе.
- `main.py`: `start_server()` → `ensure_model()` при старте; `unload_model()` → `stop_server()` при выходе.
- Хоткей `Ctrl+Shift+W` — показать/скрыть главное окно.
- Причина `400 Bad Request` от LM Studio: модель не загружена под именем из `MODEL_NAME`. Решение: `lms load <key> --identifier <MODEL_NAME>`.
- Все ветки слиты в `main`, лишние удалены. Работаем в `main`.
- **Дальше:** Правка 2 — каркас UI (AIMP-стиль, модульная архитектура).

## 2026-10-11 — hotkeys + ui-aimp start

- Разобрали проблему хоткеев: `keyboard` умирает поверх игр, `Ctrl+Alt+*` конфликтует с Punto Switcher.
- Перешли на WinAPI `RegisterHotKey` (`ui/hotkeys.py`): отдельный поток, `GetMessageW`, сигнал `fired`.
- Схема `Ctrl+Shift+M/↓/→/↑/N` — работает поверх игр, не требует фокуса.
- Добавили лог хоткеев (`logs/hotkeys.log`) и поле `translate` в пресеты (задел).
- Слили `feature/player` в `main`, удалили `feature/conveyors`.
- Создали ветку `feature/ui-aimp` — под редизайн UI (AIMP-стиль, модульная архитектура).
- Договорились: `JOURNAL.md` + `CHANGELOG.md` обновляю я по запросу.

## Бэклог (не забыть)

- **Редизайн UI** (AIMP-стиль, модульная архитектура):
  - `ui/header.py`, `ui/mode_switcher.py`, `ui/screen_view.py`, `ui/text_view.py`, `ui/playlist.py`, `ui/player.py`, `ui/settings_drawer.py`, `ui/digit_window.py`.
  - Плеер `QMediaPlayer` с плейлистом, перемоткой, скоростью, громкостью.
  - Компакт-режим + режим «цифра».
- **Захват звука TTS в OBS**:
  - Вариант B: VB-Cable + автоматизация настройки (кнопка «Настроить захват в OBS»).
  - Вариант C: нативный WASAPI Process Loopback (отложено).
- **Постобработка текста локальной LLM** (опционально):
  - Вторая модель в LM Studio исправляет OCR-текст перед TTS.
  - Поля в Preset: `postprocess: {enabled, model, prompt}`.
- **Авто-режим** (1 кадр / N сек, hash-сравнение кадров до OCR).
- **Вложение медиа в `text.md`** (ссылки на скриншоты и аудио).
- **WAV → MP3** (уменьшить размер).
- **Портативная сборка** (`llmster` + модель + `start.bat`).
- **Большая сессия (плейлист за день)**.
- **Мелочи:** звуковой пик, логирование в файл, тесты (`tests/` с pytest), README/requirements.