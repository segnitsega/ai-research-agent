import pytest

from research_agent.workflow.errors import describe_run_failure

pytestmark = pytest.mark.unit


def test_describe_api_key_failure() -> None:
    message = describe_run_failure(RuntimeError("Unauthorized 401 invalid api key for xai"))
    assert "XAI_API_KEY" in message


def test_describe_model_not_found() -> None:
    message = describe_run_failure(RuntimeError("status_code: 404, model_name: gemini-2.5-flash"))
    assert "model was not found" in message.lower()


def test_describe_generic_failure_hides_raw_body() -> None:
    message = describe_run_failure(RuntimeError("something exploded in the pipeline"))
    assert "unexpectedly" in message.lower()
    assert "exploded" not in message
