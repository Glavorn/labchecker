import os
import subprocess
import tempfile

from .models import LabLanguage


def run_check(language: LabLanguage, source_code: str, filename: str = "solution") -> tuple[str, bool]:
    suffix = ".py" if language == LabLanguage.python else ".sh"

    with tempfile.NamedTemporaryFile(mode="w", suffix=suffix, delete=False) as tmp:
        tmp.write(source_code)
        tmp_path = tmp.name

    try:
        if language == LabLanguage.python:
            cmd = ["flake8", "--max-line-length=100", tmp_path]
        else:
            # без --shell ругается SC2148 на файлы без шебанга
            cmd = ["shellcheck", "--shell=bash", tmp_path]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        output = (result.stdout + result.stderr).strip()
        output = output.replace(tmp_path, filename)
        has_issues = result.returncode != 0
        return output or "Проблем не найдено.", has_issues
    except FileNotFoundError:
        return "Линтер не установлен в контейнере.", True
    except subprocess.TimeoutExpired:
        return "Проверка не уложилась в таймаут.", True
    finally:
        os.unlink(tmp_path)
