import os
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigError


@dataclass(frozen=True)
class DbSettings:
    host: str
    port: int
    name: str
    user: str
    password: str
    sslmode: str


@dataclass(frozen=True)
class Settings:
    source: DbSettings
    target: DbSettings
    fetch_size: int
    report_dir: Path


def _int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError as exc:
        raise ConfigError(f"{key} deve ser um inteiro") from exc
    if value <= 0:
        raise ConfigError(f"{key} deve ser maior que zero")
    return value


def _db(prefix: str, env: Mapping[str, str], missing: list[str]) -> DbSettings:
    def required(key: str) -> str:
        value = env.get(f"{prefix}_{key}", "").strip()
        if not value:
            missing.append(f"{prefix}_{key}")
        return value

    return DbSettings(
        host=env.get(f"{prefix}_HOST", "").strip() or "localhost",
        port=_int(env, f"{prefix}_PORT", 5432),
        name=required("NAME"),
        user=required("USER"),
        password=required("PASSWORD"),
        sslmode=env.get(f"{prefix}_SSLMODE", "").strip() or "prefer",
    )


def load_settings(env: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if env is None else env
    missing: list[str] = []

    source = _db("SRC_DB", env, missing)
    target = _db("DST_DB", env, missing)
    if missing:
        raise ConfigError("Variáveis obrigatórias ausentes: " + ", ".join(missing))

    return Settings(
        source=source,
        target=target,
        fetch_size=_int(env, "RPA_FETCH_SIZE", 1000),
        report_dir=Path(env.get("RPA_REPORT_DIR", "").strip() or "reports"),
    )
