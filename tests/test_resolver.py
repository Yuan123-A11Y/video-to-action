from pathlib import Path

from video_to_action.resolver import Resolver


def test_resolver_detects_missing_dependency():
    resolver = Resolver({}, output_dir=Path("outputs"))
    suggestion = resolver.suggest_fix("pip install example", "command not found: pip")
    assert suggestion is not None
    assert "python" in suggestion.lower() or "pip" in suggestion.lower()


def test_resolver_switches_pip_mirror():
    resolver = Resolver({}, output_dir=Path("outputs"))
    suggestion = resolver.suggest_fix("pip install torch", "Connection timed out")
    assert "huaweicloud" in suggestion


def test_resolver_resolve_executable_for_pip_mirror():
    resolver = Resolver({}, output_dir=Path("outputs"))
    fix = resolver.resolve("pip install torch", "Connection timed out")
    assert fix["resolved"] is True
    assert fix["executable"] is True
    assert fix["new_command"] is not None
    assert "huaweicloud" in fix["new_command"]


def test_resolver_resolve_not_executable_for_missing_dependency():
    resolver = Resolver({}, output_dir=Path("outputs"))
    fix = resolver.resolve("pip install example", "command not found: pip")
    assert fix["resolved"] is True
    assert fix["executable"] is False
    assert fix["new_command"] is None


def test_resolver_resolve_executable_for_sudo():
    resolver = Resolver({}, output_dir=Path("outputs"))
    fix = resolver.resolve("apt install ffmpeg", "permission denied")
    assert fix["resolved"] is True
    assert fix["executable"] is True
    assert fix["new_command"] == "sudo apt install ffmpeg"


def test_resolver_resolve_unknown_error():
    resolver = Resolver({}, output_dir=Path("outputs"))
    fix = resolver.resolve("some command", "unknown weird error")
    assert fix["resolved"] is False
    assert fix["executable"] is False
    assert fix["new_command"] is None
