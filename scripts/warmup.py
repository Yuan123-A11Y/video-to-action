"""
模型预热脚本。

使用方法：
    python scripts/warmup.py

功能：
  1. 预热 LLM 模型（发送测试请求）
  2. 预热转写模型（加载 faster-whisper 模型）
  3. 保存预热状态（避免重复预热）
"""

import argparse
import json
import sys
import time
from pathlib import Path

# 尝试导入 tqdm（进度条支持）
try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False
    tqdm = None

# 导入 video_to_action 模块
sys.path.insert(0, str(Path(__file__).parent.parent))

from video_to_action.config import load_config
from video_to_action.utils import setup_logging


def warmup_llm(config: dict, model: str = None):
    """预热 LLM 模型。

    Args:
        config: 配置字典
        model: 模型名称（如果为 None，则使用配置中的模型）

    Returns:
        预热是否成功
    """
    print("[WARMUP] Warming up LLM model...")

    llm_config = config.get("llm", {})
    if model is None:
        model = llm_config.get("model", "agnes-2.0-flash")

    api_key = llm_config.get("api_key")
    base_url = llm_config.get("base_url")

    if not api_key or not base_url:
        print("[WARN] LLM config not found, skip warmup")
        return False

    try:
        import httpx

        # 发送测试请求
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 10,
        }

        print(f"[INFO] Sending test request to {base_url}")
        print(f"[INFO] Model: {model}")

        start_time = time.time()
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=30,
        )
        elapsed = time.time() - start_time

        if response.status_code == 200:
            print(f"[OK] LLM model warmed up successfully ({elapsed:.2f}s)")
            return True
        else:
            print(f"[ERROR] LLM warmup failed: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        print(f"[ERROR] LLM warmup error: {e}")
        return False


def warmup_transcription(config: dict, model: str = None):
    """预热转写模型。

    Args:
        config: 配置字典
        model: 模型名称（如果为 None，则使用配置中的模型）

    Returns:
        预热是否成功
    """
    print("[WARMUP] Warming up transcription model...")

    transcription_config = config.get("transcription", {})
    if model is None:
        model = transcription_config.get("model", "base")

    device = transcription_config.get("device", "auto")
    compute_type = transcription_config.get("compute_type", "int8")

    try:
        from faster_whisper import WhisperModel

        print(f"[INFO] Loading faster-whisper model: {model}")
        print(f"[INFO] Device: {device}, Compute type: {compute_type}")

        start_time = time.time()
        model = WhisperModel(model, device=device, compute_type=compute_type)
        elapsed = time.time() - start_time

        print(f"[OK] Transcription model warmed up successfully ({elapsed:.2f}s)")
        return True

    except Exception as e:
        print(f"[ERROR] Transcription model warmup error: {e}")
        return False


def save_warmup_state(output_file: str = "outputs/warmup_state.json"):
    """保存预热状态。

    Args:
        output_file: 输出文件路径（JSON 格式）
    """
    state = {
        "warmup_done": True,
        "timestamp": time.time(),
    }

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)

    print(f"[OK] Warmup state saved to: {output_file}")


def load_warmup_state(output_file: str = "outputs/warmup_state.json") -> bool:
    """加载预热状态。

    Args:
        output_file: 输入文件路径（JSON 格式）

    Returns:
        是否已预热
    """
    output_path = Path(output_file)
    if not output_path.exists():
        return False

    try:
        with open(output_path, "r", encoding="utf-8") as f:
            state = json.load(f)
        return state.get("warmup_done", False)
    except Exception as e:
        print(f"[WARN] Failed to load warmup state: {e}")
        return False


def main():
    """主函数。"""
    parser = argparse.ArgumentParser(description="Warmup models for Video-to-Action")
    parser.add_argument(
        "--config",
        help="Config file path (default: config/settings.yaml)",
    )
    parser.add_argument(
        "--llm-model",
        help="LLM model name (default: use config)",
    )
    parser.add_argument(
        "--transcription-model",
        help="Transcription model name (default: use config)",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM warmup",
    )
    parser.add_argument(
        "--skip-transcription",
        action="store_true",
        help="Skip transcription model warmup",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force warmup even if already warmed up",
    )
    args = parser.parse_args()

    # 初始化日志
    setup_logging(level="INFO", log_file="outputs/warmup.log")

    # 加载配置
    try:
        config = load_config(args.config)
    except Exception as e:
        print(f"[ERROR] Failed to load config: {e}")
        sys.exit(1)

    # 检查是否已预热
    if not args.force and load_warmup_state():
        print("[INFO] Models already warmed up, skip warmup")
        print("[INFO] Use --force to force warmup")
        sys.exit(0)

    # 预热 LLM 模型
    if not args.skip_llm:
        warmup_llm(config, args.llm_model)
    else:
        print("[SKIP] Skip LLM warmup")

    # 预热转写模型
    if not args.skip_transcription:
        warmup_transcription(config, args.transcription_model)
    else:
        print("[SKIP] Skip transcription model warmup")

    # 保存预热状态
    save_warmup_state()

    print("\n[OK] Warmup completed!")


if __name__ == "__main__":
    main()
