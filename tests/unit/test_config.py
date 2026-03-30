from velocity.config import PlatformConfig, get_config


def test_config_defaults():
    config = PlatformConfig()
    assert config.environment == "dev"
    assert config.llm.default_provider == "openai"
    assert config.infra.database.backend == "sqlite"

def test_config_env_overrides(monkeypatch):
    monkeypatch.setenv("VELOCITY_ENVIRONMENT", "production")
    monkeypatch.setenv("VELOCITY_LLM__DEFAULT_MODEL", "gpt-4-turbo")
    
    config = PlatformConfig()
    assert config.environment == "production"
    assert config.llm.default_model == "gpt-4-turbo"

def test_get_config_singleton():
    c1 = get_config()
    c2 = get_config()
    assert c1 is c2
