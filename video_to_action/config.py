"""配置读取模块。"""

import os
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path(__file__).parent.parent / "config" / "settings.yaml"


def _expand_env_vars(obj):
    """递归展开配置中的环境变量引用 ${VAR_NAME}。"""
    if isinstance(obj, str):
        # 支持 ${VAR_NAME} 和 $VAR_NAME 语法
        import re

        def replace_env(match):
            var_name = match.group(1) or match.group(2)
            return os.environ.get(var_name, match.group(0))

        return re.sub(r"\$\{([^}]+)\}|\$([A-Za-z_][A-Za-z0-9_]+)", replace_env, obj)
    elif isinstance(obj, dict):
        return {k: _expand_env_vars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_expand_env_vars(item) for item in obj]
    else:
        return obj


def load_config(config_path: Path | str | None = None) -> dict:
    """加载 YAML 配置文件，并展开环境变量引用。"""
    path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {path}")

    # 尝试加载 .env 文件
    dotenv_path = path.parent.parent / ".env"
    if dotenv_path.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(dotenv_path)
        except ImportError:
            # 如果没有 python-dotenv，手动解析 .env 文件
            with open(dotenv_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()

    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    # 展开环境变量
    config = _expand_env_vars(config)
    return config


def get_output_dir(config: dict) -> Path:
    """获取输出目录。"""
    output_dir = Path(config.get("output_dir", "outputs"))
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
