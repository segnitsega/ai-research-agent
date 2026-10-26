import pytest

from research_agent.tools.search import _parse_ddg_html, _unwrap_ddg_url

pytestmark = pytest.mark.unit


def test_parse_ddg_html_direct_links() -> None:
    html = """
    <h2 class="result__title">
      <a rel="nofollow" class="result__a" href="https://deepmind.google/models/gemini/">Gemini — Google DeepMind</a>
    </h2>
    <a class="result__snippet">Gemini models by Google DeepMind</a>
    """
    hits = _parse_ddg_html(html, 5)
    assert len(hits) == 1
    assert str(hits[0].url) == "https://deepmind.google/models/gemini/"
    assert "Gemini" in hits[0].title
    assert "DeepMind" in hits[0].snippet


def test_unwrap_ddg_redirect() -> None:
    wrapped = "https://duckduckgo.com/l/?uddg=https%3A%2F%2Fexample.com%2Fpage&rut=abc"
    assert _unwrap_ddg_url(wrapped) == "https://example.com/page"
