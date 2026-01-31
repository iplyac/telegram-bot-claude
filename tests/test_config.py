"""Tests for configuration module."""

import pytest
from unittest.mock import patch

from tgbot.config import get_agent_api_url


class TestGetAgentApiUrl:
    """Tests for get_agent_api_url function."""

    def test_env_var_set_returns_env_value(self):
        """When AGENT_API_URL is set, it should be returned."""
        with patch.dict("os.environ", {"AGENT_API_URL": "https://master-agent-xxx.run.app"}):
            result = get_agent_api_url()
            assert result == "https://master-agent-xxx.run.app"

    def test_env_var_not_set_returns_none(self):
        """When AGENT_API_URL is not set, None should be returned."""
        with patch.dict("os.environ", {}, clear=True):
            result = get_agent_api_url()
            assert result is None

    def test_env_var_empty_returns_empty(self):
        """When AGENT_API_URL is empty string, empty string is returned (falsy)."""
        with patch.dict("os.environ", {"AGENT_API_URL": ""}, clear=True):
            result = get_agent_api_url()
            # Empty string is falsy, so effectively same as None for boolean checks
            assert not result

    def test_env_var_whitespace_returns_none(self):
        """When AGENT_API_URL is whitespace only, None should be returned."""
        with patch.dict("os.environ", {"AGENT_API_URL": "   "}, clear=True):
            result = get_agent_api_url()
            assert result is None

    def test_url_sanitization_trims_whitespace(self):
        """Whitespace should be trimmed from AGENT_API_URL."""
        with patch.dict("os.environ", {"AGENT_API_URL": "  https://example.com  "}):
            result = get_agent_api_url()
            assert result == "https://example.com"
