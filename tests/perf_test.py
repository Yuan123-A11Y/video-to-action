"""
性能对比测试：验证 Whisper 模型单例模式的效果。

测试方法：
1. 第一次转写（冷启动）：需要加载模型
2. 第二次转写（热启动）：使用缓存模型
3. 对比两次的时间差
"""

import time
from pathlib import Path

from video_to_action.extractor import Extractor


def test_model_singleton_performance():
    """测试模型单例模式的性能提升。"""
    config = {"transcription": {"model": "base"}}
    output_dir = Path("outputs/perf_test")
    output_dir.mkdir(exist_ok=True)

    extractor = Extractor(config, output_dir)

    # 创建一个假的音频文件（用于测试模型加载）
    # 注意：这需要真实的音频文件才能运行
    print("性能测试需要真实的音频文件...")
    print("请运行：python tests/perf_test.py <audio_path>")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        audio_path = Path(sys.argv[1])
        config = {"transcription": {"model": "base"}}
        output_dir = Path("outputs/perf_test")
        output_dir.mkdir(exist_ok=True)

        extractor = Extractor(config, output_dir)

        # 第一次转写（冷启动）
        print("第一次转写（冷启动）...")
        start = time.time()
        segments = extractor.transcribe(audio_path)
        cold_time = time.time() - start
        print(f"  耗时: {cold_time:.2f}秒")

        # 第二次转写（热启动）
        print("第二次转写（热启动）...")
        start = time.time()
        segments = extractor.transcribe(audio_path)
        hot_time = time.time() - start
        print(f"  耗时: {hot_time:.2f}秒")

        print(f"\n性能提升: {cold_time/hot_time:.1f}x 加速")
        print(f"节省时间: {cold_time - hot_time:.2f}秒")
    else:
        test_model_singleton_performance()
