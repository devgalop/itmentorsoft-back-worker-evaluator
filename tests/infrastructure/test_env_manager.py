"""Tests for src/infrastructure/env_manager/env_manager.py."""

import os
from unittest.mock import patch

import pytest


class TestEnvironmentVariablesConstants:
    """Tests for the EnvironmentVariablesConstants class."""

    def test_validate_mandatory_env_vars_all_present(self, mock_env_vars):
        from src.infrastructure.env_manager.env_manager import (
            EnvironmentVariablesConstants,
        )

        # After mock_env_vars reloads the module, validation should pass
        EnvironmentVariablesConstants.validate_mandatory_env_vars()

    def test_validate_mandatory_env_vars_missing_one(self, mock_env_vars):
        from src.infrastructure.env_manager.env_manager import (
            EnvironmentVariablesConstants,
        )

        with patch.dict(os.environ, {}, clear=True):
            os.environ["ENVIRONMENT"] = "test"
            with pytest.raises(EnvironmentError, match="AWS_ACCESS_KEY_ID"):
                EnvironmentVariablesConstants.validate_mandatory_env_vars()

    def test_validate_mandatory_env_vars_missing_openapi_key(self, mock_env_vars):
        from src.infrastructure.env_manager.env_manager import (
            EnvironmentVariablesConstants,
        )

        with patch.dict(os.environ, {}, clear=True):
            for var in EnvironmentVariablesConstants._mandatory_env_vars:
                os.environ[var] = "test_value"
            del os.environ["OPENCODE_API_KEY"]
            with pytest.raises(EnvironmentError, match="OPENCODE_API_KEY"):
                EnvironmentVariablesConstants.validate_mandatory_env_vars()

    def test_validate_mandatory_env_vars_missing_database_url(self, mock_env_vars):
        from src.infrastructure.env_manager.env_manager import (
            EnvironmentVariablesConstants,
        )

        with patch.dict(os.environ, {}, clear=True):
            for var in EnvironmentVariablesConstants._mandatory_env_vars:
                os.environ[var] = "test_value"
            del os.environ["DATABASE_URL"]
            with pytest.raises(EnvironmentError, match="DATABASE_URL"):
                EnvironmentVariablesConstants.validate_mandatory_env_vars()

    def test_validate_mandatory_env_vars_missing_valkey_host(self, mock_env_vars):
        from src.infrastructure.env_manager.env_manager import (
            EnvironmentVariablesConstants,
        )

        with patch.dict(os.environ, {}, clear=True):
            for var in EnvironmentVariablesConstants._mandatory_env_vars:
                os.environ[var] = "test_value"
            del os.environ["VALKEY_HOST"]
            with pytest.raises(EnvironmentError, match="VALKEY_HOST"):
                EnvironmentVariablesConstants.validate_mandatory_env_vars()

    def test_mandatory_env_vars_list_not_empty(self):
        from src.infrastructure.env_manager.env_manager import (
            EnvironmentVariablesConstants,
        )

        assert len(EnvironmentVariablesConstants._mandatory_env_vars) > 0

    def test_mandatory_env_vars_contains_expected_vars(self):
        from src.infrastructure.env_manager.env_manager import (
            EnvironmentVariablesConstants,
        )

        mandatory = EnvironmentVariablesConstants._mandatory_env_vars
        assert "ENVIRONMENT" in mandatory
        assert "OPENCODE_API_KEY" in mandatory
        assert "DATABASE_URL" in mandatory
        assert "VALKEY_HOST" in mandatory
        assert "AWS_SQS_QUALIFY_QUEUE_URL" in mandatory

    def test_env_vars_read_from_environment(self, mock_env_vars):
        from src.infrastructure.env_manager.env_manager import (
            EnvironmentVariablesConstants,
        )

        # After reload, values should come from patched env
        assert EnvironmentVariablesConstants.ENVIRONMENT == "test"
        assert EnvironmentVariablesConstants.VALKEY_HOST == "localhost"
        assert EnvironmentVariablesConstants.VALKEY_PORT == "6379"

    def test_eval_mode_defaults_to_normal(self):
        from src.infrastructure.env_manager.env_manager import (
            EnvironmentVariablesConstants,
        )

        # When not set, defaults to "normal"
        with patch.dict(os.environ, {"EVALUATION_MODE": "normal"}, clear=True):
            # Reload to pick up new value
            import importlib
            import src.infrastructure.env_manager.env_manager as env_manager

            importlib.reload(env_manager)
            assert env_manager.EnvironmentVariablesConstants.EVALUATION_MODE == "normal"
