from __future__ import annotations

import os
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


@dataclass(frozen=True)
class CacheRule:
    key: str
    name: str
    category: str
    path_templates: tuple[str, ...]
    description: str
    glob_last_part: bool = False
    older_than_days: int | None = None


@dataclass(frozen=True)
class ScanResult:
    rule: CacheRule
    paths: tuple[Path, ...]
    size_bytes: int
    file_count: int
    scan_errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class CleanResult:
    rule_key: str
    deleted_bytes: int
    deleted_files: int
    skipped: tuple[str, ...]


RULES: tuple[CacheRule, ...] = (
    CacheRule(
        "windows-directx", "Windows DirectX Shader Cache", "Windows",
        ("{LOCALAPPDATA}/D3DSCache",),
        "DirectX tarafından yeniden oluşturulan shader dosyaları.",
    ),
    CacheRule(
        "nvidia-shader", "NVIDIA Shader Cache", "Ekran kartı",
        (
            "{LOCALAPPDATA}/NVIDIA/DXCache",
            "{LOCALAPPDATA}/NVIDIA/GLCache",
            "{LOCALAPPDATA}/NVIDIA Corporation/NV_Cache",
        ),
        "NVIDIA'nın yeniden oluşturabildiği DX/GL shader dosyaları.",
    ),
    CacheRule(
        "amd-shader", "AMD Shader Cache", "Ekran kartı",
        (
            "{LOCALAPPDATA}/AMD/DxCache",
            "{LOCALAPPDATA}/AMD/GLCache",
            "{LOCALAPPDATA}/AMD/VkCache",
        ),
        "AMD sürücüsünün yeniden oluşturabildiği shader dosyaları.",
    ),
    CacheRule(
        "intel-shader", "Intel Shader Cache", "Ekran kartı",
        ("{USERPROFILE}/AppData/LocalLow/Intel/ShaderCache",),
        "Intel grafik sürücüsünün yeniden oluşturabildiği shader dosyaları.",
    ),
    CacheRule(
        "discord", "Discord Cache", "Uygulama",
        ("{APPDATA}/discord/Cache",),
        "Discord'un resmi sorun giderme sayfasında belirtilen önbellek.",
    ),
    CacheRule(
        "epic", "Epic Games Launcher Web Cache", "Uygulama",
        ("{LOCALAPPDATA}/EpicGamesLauncher/Saved/webcache*",),
        "Epic Launcher'ın yeniden oluşturduğu webcache klasörleri.",
        glob_last_part=True,
    ),
    CacheRule(
        "user-temp", "Kullanıcı Geçici Dosyaları (7+ gün)", "Geçici dosya",
        ("{TEMP}",),
        "Yalnız kullanıcı TEMP klasöründeki en az 7 günlük dosyalar.",
        older_than_days=7,
    ),
)


def default_environment() -> dict[str, str]:
    user = os.environ.get("USERPROFILE", str(Path.home()))
    local = os.environ.get("LOCALAPPDATA", str(Path(user) / "AppData" / "Local"))
    return {
        "USERPROFILE": user,
        "LOCALAPPDATA": local,
        "APPDATA": os.environ.get("APPDATA", str(Path(user) / "AppData" / "Roaming")),
        "TEMP": os.environ.get("TEMP", str(Path(local) / "Temp")),
    }


def _expand_template(template: str, env: Mapping[str, str]) -> Path:
    value = template
    for key in ("USERPROFILE", "LOCALAPPDATA", "APPDATA", "TEMP"):
        value = value.replace("{" + key + "}", env[key])
    return Path(value)


def resolve_rule_paths(rule: CacheRule, env: Mapping[str, str] | None = None) -> tuple[Path, ...]:
    env = dict(env or default_environment())
    resolved: list[Path] = []
    for template in rule.path_templates:
        candidate = _expand_template(template, env)
        if rule.glob_last_part:
            parent = candidate.parent
            if parent.is_dir():
                resolved.extend(
                    p for p in parent.glob(candidate.name)
                    if p.is_dir() and not _is_reparse(p)
                )
        elif candidate.is_dir() and not _is_reparse(candidate):
            resolved.append(candidate)
    # abspath normalizes the path without following a junction/symlink.
    return tuple(dict.fromkeys(Path(os.path.abspath(p)) for p in resolved))


def _is_reparse(path: Path) -> bool:
    try:
        info = path.lstat()
    except OSError:
        return True
    attrs = getattr(info, "st_file_attributes", 0)
    return path.is_symlink() or bool(attrs & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0))


def _candidate_files(root: Path, older_than_days: int | None, now: float) -> Iterable[Path]:
    cutoff = now - older_than_days * 86400 if older_than_days is not None else None
    for current, dirs, files in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        dirs[:] = [name for name in dirs if not _is_reparse(current_path / name)]
        for name in files:
            path = current_path / name
            try:
                if _is_reparse(path):
                    continue
                info = path.stat()
                if cutoff is None or info.st_mtime <= cutoff:
                    yield path
            except OSError:
                continue


def scan_rule(rule: CacheRule, env: Mapping[str, str] | None = None, now: float | None = None) -> ScanResult:
    paths = resolve_rule_paths(rule, env)
    total = 0
    count = 0
    errors: list[str] = []
    timestamp = time.time() if now is None else now
    for root in paths:
        try:
            for path in _candidate_files(root, rule.older_than_days, timestamp):
                try:
                    total += path.stat().st_size
                    count += 1
                except OSError as exc:
                    errors.append(f"{path}: {exc}")
        except OSError as exc:
            errors.append(f"{root}: {exc}")
    return ScanResult(rule, paths, total, count, tuple(errors))


def scan_all(
    rules: Iterable[CacheRule] = RULES,
    env: Mapping[str, str] | None = None,
    now: float | None = None,
) -> list[ScanResult]:
    return [scan_rule(rule, env, now) for rule in rules]


def clean_result(result: ScanResult, now: float | None = None) -> CleanResult:
    deleted_bytes = 0
    deleted_files = 0
    skipped: list[str] = []
    timestamp = time.time() if now is None else now

    for root in result.paths:
        root = Path(os.path.abspath(root))
        if _is_reparse(root):
            skipped.append(f"{root}: yeniden ayrıştırma noktası güvenlik nedeniyle atlandı")
            continue
        files = list(_candidate_files(root, result.rule.older_than_days, timestamp))
        for path in files:
            try:
                size = path.stat().st_size
                path.unlink()
                deleted_bytes += size
                deleted_files += 1
            except OSError as exc:
                skipped.append(f"{path}: {exc}")

        # Remove only empty child folders; keep the known cache root itself.
        try:
            children = sorted(
                (p for p in root.rglob("*") if p.is_dir() and not _is_reparse(p)),
                key=lambda p: len(p.parts),
                reverse=True,
            )
            for directory in children:
                try:
                    directory.rmdir()
                except OSError:
                    pass
        except OSError as exc:
            skipped.append(f"{root}: {exc}")

    return CleanResult(result.rule.key, deleted_bytes, deleted_files, tuple(skipped))


def human_size(value: int) -> str:
    size = float(value)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size < 1024 or unit == "TB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"

