"""Test cases for video_to_action/config.py"""

from pathlib import Path
from unittest.mock import patch

import pytest

from video_to_action.config import DEFAULT_CONFIG_PATH, _expand_env_vars, get_output_dir, load_config


def _mock_environ_get(var_name, default=None):
    """Mock os.environ.get to return test values (avoids Windows env var length limit)."""
    mock_values = {
        "TEST_VAR": "test_value",
        "HOME": "/home/user",
        "API_KEY": "secret123",
        "LLM_API_KEY": "env_secret_key",
        "DOTENV_VAR": "dotenv_value",
        "MANUAL_VAR": "manual_value",
    }
    return mock_values.get(var_name, default)


class TestExpandEnvVars:
    """Test _expand_env_vars function."""

    def test_expand_simple_env_var(self):
        """Test expanding simple ${VAR_NAME} syntax."""
        with patch("os.environ.get", side_effect=_mock_environ_get):
            result = _expand_env_vars("${TEST_VAR}")

            assert result == "test_value"

    def test_expand_simple_env_var_shorthand(self):
        """Test expanding $VAR_NAME syntax."""
        with patch("os.environ.get", side_effect=_mock_environ_get):
            result = _expand_env_vars("$TEST_VAR")

            assert result == "test_value"

    def test_expand_env_var_in_string(self):
        """Test expanding env var in middle of string."""
        with patch("os.environ.get", side_effect=_mock_environ_get):
            result = _expand_env_vars("Path: ${HOME}/projects")

            assert result == "Path: /home/user/projects"

    def test_expand_missing_env_var(self):
        """Test expanding non-existent env var (should keep original)."""
        result = _expand_env_vars("${TEST_NONEXISTENT}")

        # Should return original string (not expanded)
        assert result == "${TEST_NONEXISTENT}"

    def test_expand_in_dict(self):
        """Test expanding env vars in dictionary."""
        with patch("os.environ.get", side_effect=_mock_environ_get):
            obj = {"key": "${API_KEY}", "nested": {"inner": "$API_KEY"}}
            result = _expand_env_vars(obj)

            assert result["key"] == "secret123"
            assert result["nested"]["inner"] == "secret123"

    def test_expand_in_list(self):
        """Test expanding env vars in list."""
        with patch("os.environ.get", side_effect=_mock_environ_get):
            obj = ["${ITEM}", "static", "$ITEM"]
            result = _expand_env_vars(obj)

            # ITEM not in mock_values, so ${ITEM} and $ITEM are kept as-is
            assert "${ITEM}" in result[0]
            assert "static" in result[1]

    def test_expand_no_env_vars(self):
        """Test with string that has no env vars."""
        result = _expand_env_vars("plain string")

        assert result == "plain string"

    def test_expand_empty_string(self):
        """Test with empty string."""
        result = _expand_env_vars("")

        assert result == ""

    def test_expand_non_string_types(self):
        """Test with non-string types (should return as-is)."""
        assert _expand_env_vars(123) == 123
        assert _expand_env_vars(True) is True
        assert _expand_env_vars(None) is None
        assert _expand_env_vars([1, 2, 3]) == [1, 2, 3]  # List without strings


class TestLoadConfig:
    """Test load_config function."""

    def test_load_config_file_not_found(self):
        """Test loading non-existent config file."""
        with pytest.raises(FileNotFoundError, match="配置文件不存在"):
            load_config(Path("/nonexistent/path.yaml"))

    def test_load_config_valid_yaml(self, tmp_path: Path):
        """Test loading valid YAML config file."""
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(
            """
llm:
  provider: mock
  api_key: test_key
output_dir: outputs
""",
            encoding="utf-8",
        )

        result = load_config(config_file)

        assert result["llm"]["provider"] == "mock"
        assert result["output_dir"] == "outputs"

    def test_load_config_with_env_expansion(self, tmp_path: Path):
        """Test loading config with env var expansion."""
        with patch("os.environ.get", side_effect=_mock_environ_get):
            config_file = tmp_path / "settings.yaml"
            config_file.write_text(
                """
llm:
  provider: mock
  api_key: ${LLM_API_KEY}
""",
                encoding="utf-8",
            )

            result = load_config(config_file)

            assert result["llm"]["api_key"] == "env_secret_key"

    def test_load_config_with_dotenv(self, tmp_path: Path):
        """Test loading config with .env file."""
        # Create .env file
        dotenv_file = tmp_path.parent / ".env"
        dotenv_file.write_text("DOTENV_VAR=dotenv_value\n", encoding="utf-8")

        # Create config file
        config_file = tmp_path / "settings.yaml"
        config_file.write_text(
            """
test_var: ${DOTENV_VAR}
""",
            encoding="utf-8",
        )

        result = load_config(config_file)

        assert result["test_var"] == "dotenv_value"

    def test_load_config_default_path(self):
        """Test loading config with default path."""
        # This test assumes DEFAULT_CONFIG_PATH exists
        if DEFAULT_CONFIG_PATH.exists():
            result = load_config()

            assert isinstance(result, dict)
        else:
            pytest.skip("Default config file does not exist")


class TestGetOutputDir:
    """Test get_output_dir function."""

    def test_get_output_dir_from_config(self):
        """Test getting output dir from config."""
        config = {"output_dir": "/custom/output"}
        result = get_output_dir(config)

        assert result == Path("/custom/output")

    def test_get_output_dir_default(self):
        """Test getting default output dir."""
        config = {}
        result = get_output_dir(config)

        assert result == Path("outputs")

    def test_get_output_dir_creates_directory(self, tmp_path: Path):
        """Test that get_output_dir creates the directory."""
        config = {"output_dir": str(tmp_path / "new_dir")}
        result = get_output_dir(config)

        assert result.exists()
        assert result.is_dir()

    def test_get_output_dir_with_path_object(self, tmp_path: Path):
        """Test getting output dir with Path object in config."""
        config = {"output_dir": tmp_path / "path_dir"}
        result = get_output_dir(config)

        assert result.exists()
