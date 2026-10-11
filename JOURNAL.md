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