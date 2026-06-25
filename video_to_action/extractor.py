# g:\trae\video-to-action\video_to_action\extractor.py
"""视频内容提取模块：提取音频、转写文字、截取关键帧。"""

import shutil
import subprocess
from pathlib import Path


class Extractor:
    """视频内容提取器。"""

    # 类级别模型缓存（所有实例共享）
    _model_cache = {}  # {cache_key: model}

    def __init__(self, config: dict, output_dir: Path):
        """初始化提取器并创建输出子目录。"""
        self.config = config
        self.output_dir = output_dir
        self.audio_dir = output_dir / "audio"
        self.frames_dir = output_dir / "frames"
        self.audio_dir.mkdir(exist_ok=True)
        self.frames_dir.mkdir(exist_ok=True)

    def _build_audio_command(self, video_path: Path, audio_path: Path) -> list[str]:
        """构建 ffmpeg 提取音频命令。"""
        return [
            "ffmpeg",
            "-y",
            "-i",
            str(video_path),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(audio_path),
        ]

    def _normalize_text(self, text: str) -> str:
        """清理转写文本，合并连续空白为单个空格并去除首尾空白。"""
        return " ".join(text.split())

    def extract_audio(self, video_path: Path) -> Path:
        """从视频中提取单声道 16kHz PCM 音频。"""
        if shutil.which("ffmpeg") is None:
            raise EnvironmentError("未找到 ffmpeg，请先安装 ffmpeg")
        audio_path = self.audio_dir / f"{video_path.stem}.wav"
        command = self._build_audio_command(video_path, audio_path)
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg 提取音频失败: {result.stderr}")
        return audio_path

    def _detect_device(self) -> str:
        """自动检测并返回最佳计算设备。"""

        # 优先使用配置文件中的设置
        config_device = self.config.get("transcription", {}).get("device", "auto")
        if config_device != "auto":
            return config_device

        # 自动检测 CUDA
        try:
            from ctranslate2 import get_cuda_device_count

            if get_cuda_device_count() > 0:
                return "cuda"
        except Exception:
            pass

        # 回退到 CPU
        return "cpu"

    def transcribe(self, audio_path: Path) -> list[dict]:
        """使用 faster-whisper 将音频转写为带时间戳的文本片段。"""
        from faster_whisper import WhisperModel

        model_name = self.config.get("transcription", {}).get("model", "base")
        device = self._detect_device()
        compute_type = self.config.get("transcription", {}).get("compute_type", "int8")

        # 使用缓存避免重复加载模型
        cache_key = f"{model_name}_{device}_{compute_type}"
        if cache_key not in self.__class__._model_cache:
            model = WhisperModel(model_name, device=device, compute_type=compute_type)
            self.__class__._model_cache[cache_key] = model
        else:
            model = self.__class__._model_cache[cache_key]

        segments, _ = model.transcribe(str(audio_path), language="zh")
        return [
            {
                "start": float(segment.start),
                "end": float(segment.end),
                "text": self._normalize_text(segment.text),
            }
            for segment in segments
        ]

    def _get_video_duration(self, video_path: Path) -> float:
        """使用 ffprobe 获取视频总时长（秒）。"""
        if shutil.which("ffprobe") is None:
            raise EnvironmentError("未找到 ffprobe，请先安装 ffmpeg")
        command = [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(video_path),
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffprobe 获取视频时长失败: {result.stderr}")
        return float(result.stdout.strip())

    def extract_frames(self, video_path: Path, count: int = 5) -> list[Path]:
        """从视频中均匀截取 count 张关键帧。

        通过 ffprobe 获取视频总时长，按等间隔时间点使用 ffmpeg 逐帧截取，
        避免依赖未定义的帧序号变量。
        """
        if shutil.which("ffmpeg") is None:
            raise EnvironmentError("未找到 ffmpeg")
        duration = self._get_video_duration(video_path)
        frames = []
        for i in range(1, count + 1):
            timestamp = i * duration / (count + 1)
            frame_path = self.frames_dir / f"{video_path.stem}_frame_{i}.jpg"
            command = [
                "ffmpeg",
                "-y",
                "-ss",
                str(timestamp),
                "-i",
                str(video_path),
                "-vframes",
                "1",
                str(frame_path),
            ]
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode == 0 and frame_path.exists():
                frames.append(frame_path)
        return frames

    def process(self, video_path: Path) -> dict:
        """完整处理视频：提取音频、转写并截取关键帧。

        每个步骤独立保护，即使某一步失败也尽可能返回已有结果。
        """
        audio_path = None
        segments = []
        try:
            audio_path = self.extract_audio(video_path)
            segments = self.transcribe(audio_path)
        except Exception as e:
            # 音频提取或转写失败时记录异常，继续尝试抽帧
            segments = [{"start": 0, "end": 0, "text": f"[音频处理失败: {e}]"}]

        frames = []
        try:
            frames = self.extract_frames(video_path)
        except Exception:
            frames = []

        full_text = " ".join(seg["text"] for seg in segments)
        return {
            "audio_path": str(audio_path) if audio_path else "",
            "segments": segments,
            "frames": [str(f) for f in frames],
            "text": full_text,
        }
