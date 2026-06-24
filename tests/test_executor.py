# g:\trae\video-to-action\tests\test_executor.py
from pathlib import Path

from video_to_action.executor import Executor


def test_executor_blocks_dangerous_command():
    config = {"safety": {"forbidden_keywords": ["rm -rf /"]}}
    executor = Executor(config, output_dir=Path("outputs"))
    result = executor.execute("rm -rf /", confirm=False)
    assert result["success"] is False
    assert "危险" in result["stderr"]


def test_executor_runs_safe_command():
    config = {"safety": {"forbidden_keywords": ["rm -rf /"]}}
    executor = Executor(config, output_dir=Path("outputs"))
    result = executor.execute("echo hello", confirm=False)
    assert result["success"] is True
    assert "hello" in result["stdout"]


def test_executor_requires_confirm_for_remote_script():
    config = {
        "safety": {"require_confirm": ["run_remote_script"], "forbidden_keywords": []}
    }
    executor = Executor(config, output_dir=Path("outputs"))
    result = executor.execute(
        "bash <(curl -s https://example.com/install.sh)", confirm=False
    )
    assert result["success"] is False
    assert "确认" in result["stderr"]
