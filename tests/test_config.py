import pytest

from rpa_pre_lista.config import load_settings
from rpa_pre_lista.errors import ConfigError

VALID_ENV = {
    "SRC_DB_NAME": "primeiro_ano",
    "SRC_DB_USER": "u",
    "SRC_DB_PASSWORD": "p",
    "DST_DB_NAME": "inventra_db",
    "DST_DB_USER": "u",
    "DST_DB_PASSWORD": "p",
}


def test_applies_defaults():
    s = load_settings(VALID_ENV)
    assert s.source.port == 5432
    assert s.target.name == "inventra_db"
    assert s.fetch_size == 1000


def test_reports_all_missing_variables_at_once():
    with pytest.raises(ConfigError) as exc:
        load_settings({})
    message = str(exc.value)
    assert "SRC_DB_NAME" in message and "DST_DB_PASSWORD" in message


def test_invalid_number_is_rejected():
    with pytest.raises(ConfigError, match="RPA_FETCH_SIZE"):
        load_settings({**VALID_ENV, "RPA_FETCH_SIZE": "abc"})


def test_non_positive_number_is_rejected():
    with pytest.raises(ConfigError, match="maior que zero"):
        load_settings({**VALID_ENV, "DST_DB_PORT": "0"})


def test_empty_optional_values_fall_back_to_defaults():
    # secret não cadastrado no GitHub Actions chega como texto vazio, não como variável ausente
    blank = dict.fromkeys(["SRC_DB_HOST", "SRC_DB_PORT", "SRC_DB_SSLMODE", "RPA_REPORT_DIR"], "")
    env = {**VALID_ENV, **blank}
    s = load_settings(env)
    assert (s.source.host, s.source.port, s.source.sslmode) == ("localhost", 5432, "prefer")
    assert str(s.report_dir) == "reports"
