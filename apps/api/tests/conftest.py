import os

os.environ["ALLOW_MODEL_REQUESTS"] = "false"

from pydantic_ai import models

models.ALLOW_MODEL_REQUESTS = False

import pytest

from research_agent.config import Settings


@pytest.fixture
def settings() -> Settings:
    return Settings(
        model_planner="google:gemini-3.8-flash",
        model_searcher="google:gemini-3.8-flash",
        model_reader="google:gemini-3.8-flash",
        model_critic="google:gemini-3.8-flash",
        model_writer="google:gemini-3.8-flash",
        model_curator="google:gemini-3.8-flash",
        allow_model_requests=False,
        google_api_key=None,
        gemini_api_key=None,
    )
