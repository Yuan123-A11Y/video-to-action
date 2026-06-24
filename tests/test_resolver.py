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
