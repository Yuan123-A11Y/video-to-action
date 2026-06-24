"""配置读取模块。"""

from pathlib import Path

import yaml


DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"


def load_config(config_path: Path | str | None = None) -> dict:
    """加载 YAML 配置文件。"""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_output_dir(config: dict) -> Path:
    """获取输出目录。"""
    output_dir = Path(config.get("output_dir", "outputs"))
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
