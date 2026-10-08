"""
Снимок кода проекта в один Markdown-файл.

Запуск из корня appTTSwindov:
    python tools/snapshot.py

Результат: snapshot.md в корне проекта.
"""

import os
import subprocess
import time


BASE_DIR = "."
OUTPUT_FILE = "snapshot.md"

EXCLUDE_DIRS = {
    "__pycache__", ".git", ".venv", "venv", "env",
    "sessions", "presets", "logs", "tools/__pycache__",
    ".idea", ".vscode", "node_modules",
}

INCLUDE_EXTS = {
    ".py", ".md", ".txt", ".json", ".yml", ".yaml", ".toml", ".cfg", ".ini",
}

INCLUDE_FILES = {
    ".gitignore", "requirements.txt", "README.md", "CHANGELOG.md",
}


def run_git(args: list) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True, text=True, encoding="utf-8",
            timeout=5,
        )
        return result.stdout.strip()
    except Exception as e:
        return f"(git error: {e})"


def should_include(path: str, filename: str) -> bool:
    if filename in INCLUDE_FILES:
        return True
    ext = os.path.splitext(filename)[1].lower()
    return ext in INCLUDE_EXTS


def collect_structure(base: str) -> str:
    lines = []
    for root, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith("."))
        rel_root = os.path.relpath(root, base)
        if rel_root == ".":
            indent = ""
        else:
            depth = rel_root.count(os.sep) + 1
            indent = "│   " * (depth - 1) + "├── "
        if rel_root != ".":
            lines.append(f"{indent}{os.path.basename(root)}/")
            indent = "│   " * depth + "├── "
        else:
            indent = "├── "
        for f in sorted(files):
            if should_include(os.path.join(root, f), f):
                lines.append(f"{indent}{f}")
    return "\n".join(lines)


def collect_code(base: str) -> str:
    parts = []
    for root, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith("."))
        for f in sorted(files):
            full = os.path.join(root, f)
            if not should_include(full, f):
                continue
            rel = os.path.relpath(full, base).replace("\\", "/")
            ext = os.path.splitext(f)[1].lower().lstrip(".")
            if not ext:
                ext = "text"
            parts.append(f"## 📄 `{rel}`\n")
            parts.append(f"```{ext}")
            try:
                with open(full, "r", encoding="utf-8") as fp:
                    parts.append(fp.read())
            except Exception as e:
                parts.append(f"# Ошибка чтения: {e}")
            parts.append("```\n")
    return "\n".join(parts)


def main():
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    branch = run_git(["branch", "--show-current"])
    last_commits = run_git(["log", "--oneline", "-20"])
    status = run_git(["status", "--short"])

    header = []
    header.append("# Code Snapshot: appTTSwindov\n")
    header.append(f"**Дата:** {timestamp}")
    header.append(f"**Ветка:** {branch}")
    header.append(f"**Путь:** {os.path.abspath(BASE_DIR)}\n")
    header.append("## Последние коммиты\n")
    header.append("```")
    header.append(last_commits or "(нет коммитов)")
    header.append("```\n")
    if status:
        header.append("## Незакоммиченные изменения\n")
        header.append("```")
        header.append(status)
        header.append("```\n")
    header.append("## Структура проекта\n")
    header.append("```")
    header.append(collect_structure(BASE_DIR))
    header.append("```\n")
    header.append("---\n")

    code = collect_code(BASE_DIR)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(header))
        f.write(code)

    size_kb = os.path.getsize(OUTPUT_FILE) / 1024
    print(f"[SNAPSHOT] Готово: {os.path.abspath(OUTPUT_FILE)} ({size_kb:.1f} КБ)")


if __name__ == "__main__":
    main()