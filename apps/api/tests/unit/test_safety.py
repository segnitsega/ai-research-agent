import pytest

from research_agent.tools.safety import SsrfBlockedError, assert_public_url, ip_is_blocked
from research_agent.workflow.verify import quote_found_in_source


pytestmark = pytest.mark.unit


def test_blocks_private_ip() -> None:
    assert ip_is_blocked("127.0.0.1")
    assert ip_is_blocked("10.1.2.3")
    assert not ip_is_blocked("1.1.1.1")


def test_blocks_literal_private_url() -> None:
    with pytest.raises(SsrfBlockedError):
        assert_public_url("http://127.0.0.1/secret")


def test_blocks_rebinding(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "research_agent.tools.safety._resolve",
        lambda host: ["127.0.0.1"],
    )
    with pytest.raises(SsrfBlockedError):
        assert_public_url("https://example.com/page")


def test_quote_normalization() -> None:
    source = "The model \u201cGemini\u201d is the only provider."
    quote = 'The model "Gemini" is the only provider.'
    assert quote_found_in_source(quote, source)
    assert not quote_found_in_source("The model is OpenAI.", source)
