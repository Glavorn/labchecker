import os
import subprocess
import tempfile
import zipfile
from pathlib import Path

from ..models import LabLanguage

EXTENSION_BY_LANGUAGE = {
    LabLanguage.python: ".py",
    LabLanguage.bash: ".sh",
}

MAX_ARCHIVE_FILES = 500
MAX_ARCHIVE_UNCOMPRESSED_SIZE = 20 * 1024 * 1024  # 20 MB


def run_check(language: LabLanguage, filename: str, file_bytes: bytes) -> tuple[str, bool]:
    if filename.lower().endswith(".zip"):
        return _check_archive(language, file_bytes)
    return _check_single_file(language, file_bytes)


def _check_single_file(language: LabLanguage, file_bytes: bytes) -> tuple[str, bool]:
    suffix = EXTENSION_BY_LANGUAGE[language]
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(file_bytes)
        tmp_path = tmp.name

    try:
        return _lint_file(language, Path(tmp_path))
    finally:
        os.unlink(tmp_path)


def _check_archive(language: LabLanguage, file_bytes: bytes) -> tuple[str, bool]:
    suffix = EXTENSION_BY_LANGUAGE[language]

    with tempfile.TemporaryDirectory() as tmp_dir:
        zip_path = Path(tmp_dir) / "upload.zip"
        zip_path.write_bytes(file_bytes)

        try:
            with zipfile.ZipFile(zip_path) as archive:
                error = _validate_archive(archive)
                if error:
                    return error, True
                archive.extractall(tmp_dir)
        except zipfile.BadZipFile:
            return "Не удалось распаковать архив: повреждённый ZIP-файл.", True

        zip_path.unlink()
        targets = sorted(p for p in Path(tmp_dir).rglob(f"*{suffix}") if p.is_file())
        if not targets:
            return f"В архиве не найдено файлов с расширением {suffix}.", True

        chunks = []
        has_issues = False
        for path in targets:
            output, issues = _lint_file(language, path)
            has_issues = has_issues or issues
            chunks.append(f"=== {path.relative_to(tmp_dir)} ===\n{output}")
        return "\n\n".join(chunks), has_issues


def _validate_archive(archive: zipfile.ZipFile) -> str | None:
    infos = archive.infolist()
    if len(infos) > MAX_ARCHIVE_FILES:
        return f"В архиве больше {MAX_ARCHIVE_FILES} файлов — отклонено."
    if sum(info.file_size for info in infos) > MAX_ARCHIVE_UNCOMPRESSED_SIZE:
        return "Архив после распаковки превышает допустимый размер (20 МБ)."
    return None


def _lint_file(language: LabLanguage, path: Path) -> tuple[str, bool]:
    if language == LabLanguage.python:
        cmd = ["flake8", "--max-line-length=100", str(path)]
    else:
        cmd = ["shellcheck", str(path)]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        output = (result.stdout + result.stderr).strip()
        return output or "Проблем не найдено.", result.returncode != 0
    except FileNotFoundError:
        return "Линтер не установлен в контейнере.", True
    except subprocess.TimeoutExpired:
        return "Проверка не уложилась в таймаут.", True
