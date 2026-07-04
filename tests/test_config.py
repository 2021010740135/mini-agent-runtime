"""测试 Config 模块"""

from agent.config import Config


def test_config_defaults(monkeypatch):
    """验证未设置环境变量时的默认值."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)

    config = Config()
    assert config.api_key == ""
    assert config.base_url == "https://api.openai.com/v1"
    assert config.model == "gpt-4o-mini"


def test_config_from_env(monkeypatch):
    """验证从环境变量读取配置."""
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://custom.com/v1")
    monkeypatch.setenv("LLM_MODEL", "gpt-5")

    config = Config()
    assert config.api_key == "sk-test"
    assert config.base_url == "https://custom.com/v1"
    assert config.model == "gpt-5"


def test_config_validate_missing_key(monkeypatch):
    """验证缺少 API Key 时 validate() 抛出异常."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config = Config()
    try:
        config.validate()
        assert False, "应该抛出 ValueError"
    except ValueError:
        pass
