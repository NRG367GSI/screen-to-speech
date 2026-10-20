# Journal

Краткий журнал сессий. Одна строка = один шаг. Формат: что сделано → к чему привело.

## 2026-10-11 — hotkeys + ui-aimp start

- Разобрали проблему хоткеев: `keyboard` умирает поверх игр, `Ctrl+Alt+*` конфликтует с Punto Switcher.
- Перешли на WinAPI `RegisterHotKey` (`ui/hotkeys.py`): отдельный поток, `GetMessageW`, сигнал `fired`.
- Схема `Ctrl+Shift+M/↓/→/↑/N` — работает поверх игр, не требует фокуса.
- Добавили лог хоткеев (`logs/hotkeys.log`) и поле `translate` в пресеты (задел).
- Слили `feature/player` в `main`, удалили `feature/conveyors`.
- Создали ветку `feature/ui-aimp` — под редизайн UI (AIMP-стиль, модульная архитектура).
- Договорились: `JOURNAL.md` + `CHANGELOG.md` обновляю я по запросу.
- **Дальше:** Правка 2 — каркас UI (header, mode_switcher, screen_view, text_view, playlist). Плеер/drawer/цифра — заглушки.


## Бэклог (не забыть)

- **Захват звука нашего TTS в OBS** (для монтажа):
  - Цель: OBS видит звук нашей программы как отдельный аудиоисточник.
  - Вариант A: плагин `win-capture-audio` (BETA, но просто).
  - Вариант B: VB-Cable + автоматизация настройки в нашей программе (надёжнее).
  - Вариант C: нативный WASAPI Process Loopback (сложно, отдельный проект).
  - Решение: начать с B (кнопка «Настроить захват в OBS»), C — отложить.
  - **Вернуться после:** UI + плеер.

  - **Постобработка текста локальной LLM** (опционально):
  - Вторая модель в LM Studio (например, Qwen) исправляет OCR-текст перед TTS.
  - Поля в Preset: `postprocess: {enabled, model, prompt}`.
  - LM Studio поддерживает несколько моделей одновременно.
  - Приоритет: средний (после UI/плеера).

- **Переход на Silero TTS v5**:
  - `MODEL_ID = "v5_ru"` (или `v5_5_ru`).
  - Автоматические ударения в омографах, качество выше, скорость выше.
  - Приоритет: высокий (простая замена, сразу улучшение).

  
## 2026-10-20 — LMS automation + Silero v5
- Silero TTS обновлён с `v4_ru` на `v5_5_ru`: автоматические ударения в омографах, скорость выше.
- Добавлен `core/lmstudio_control.py`: автозапуск сервера, автозагрузка модели (`--identifier`), выгрузка при выходе.
- `main.py`: `lms.start_server()` → `lms.ensure_model()` при старте, `lms.unload_model()` → `lms.stop_server()` при выходе.
- Добавлен хоткей `Ctrl+Shift+W` — показать/скрыть главное окно.
- Найдена причина `400 Bad Request` от LM Studio: модель не загружена под именем из `MODEL_NAME`. Решение: `lms load <key> --identifier <MODEL_NAME>`.
- **Дальше:** Правка 2 — каркас UI (header, mode_switcher, screen_view, text_view, playlist).