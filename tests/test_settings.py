import pytest
from pydantic import ValidationError


def test_cors_from_csv_env(settings_factory):
    s = settings_factory(CORS_ALLOW_ORIGINS="https://a.com, https://b.com")
    assert s.cors_allow_origins == ["https://a.com", "https://b.com"]


def test_cors_from_yaml_list(settings_factory):
    s = settings_factory()
    assert "http://localhost:3000" in s.cors_allow_origins


def test_cors_empty_string(settings_factory):
    s = settings_factory(CORS_ALLOW_ORIGINS="")
    assert s.cors_allow_origins == []


def test_env_overrides_yaml(settings_factory):
    s = settings_factory(DB_POOL_SIZE="99")
    assert s.db_pool_size == 99


def test_db_url_masked_in_repr(settings_factory):
    s = settings_factory()
    assert "vills:vills" not in repr(s.database_url)
    assert s.database_url.get_secret_value().startswith("postgresql")


def test_settings_dump_no_plaintext_secret(settings_factory):
    dump = settings_factory().safe_dump()
    assert dump["database_url"] == "***masked***"
    assert dump["redis_url"] == "***masked***"


@pytest.mark.parametrize("env", ["dev", "staging", "prod"])
def test_all_environment_configs_valid(settings_factory, env):
    s = settings_factory(environment=env)
    assert s.app_name == "vills"
    assert isinstance(s.cors_allow_origins, list)
    assert len(s.cors_allow_origins) >= 1


def test_invalid_environment_rejected(settings_factory):
    with pytest.raises(ValidationError):
        settings_factory(environment="producao")
