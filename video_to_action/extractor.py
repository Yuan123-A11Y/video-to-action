"""视频内容提取模块：提取音频、转写文字、截取关键帧。"""

import logging
import shutil
import subprocess
from pathlib import Path

from video_to_action.exceptions import ExtractionError

logger = logging.getLogger(__name__)


class Extractor:
    """视频内容提取器。"""

    # 类级别模型缓存（所有实例共享）
    _model_cache = {}  # {cache_key: model}
    _model_lock = __import__("threading").Lock()  # 并发加载保护
    _max_cached_models = 2  # 最多缓存几个模型（防止内存泄漏）

    # HuggingFace 镜像检测缓存（避免每次转写都等待 3 秒）
    _hf_mirror_checked = False
    _hf_mirror_use_mirror = False
    _hf_mirror_lock = __import__("threading").Lock()

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
            raise ExtractionError("未找到 ffmpeg，请先安装 ffmpeg")
        audio_path = self.audio_dir / f"{video_path.stem}.wav"
        command = self._build_audio_command(video_path, audio_path)
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            raise ExtractionError(f"ffmpeg 提取音频失败: {result.stderr}")
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
        import os

        from faster_whisper import WhisperModel

        # 自动设置 HuggingFace 镜像（解决国内网络连接问题，结果缓存避免重复检测）
        if not os.environ.get("HF_ENDPOINT"):
            with self.__class__._hf_mirror_lock:
                if not self.__class__._hf_mirror_checked:
                    use_mirror = False
                    try:
                        import socket

                        socket.create_connection(("huggingface.co", 443), timeout=1)
                    except (OSError, socket.timeout):
                        use_mirror = True
                    self.__class__._hf_mirror_use_mirror = use_mirror
                    self.__class__._hf_mirror_checked = True
            if self.__class__._hf_mirror_use_mirror:
                os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
            else:
                os.environ["HF_ENDPOINT"] = "https://huggingface.co"

        model_name = self.config.get("transcription", {}).get("model", "base")
        device = self._detect_device()
        compute_type = self.config.get("transcription", {}).get("compute_type", "int8")

        # 使用缓存避免重复加载模型（加锁保护并发加载）
        cache_key = f"{model_name}_{device}_{compute_type}"
        if cache_key not in self.__class__._model_cache:
            with self.__class__._model_lock:
                # 双重检查（防止多线程同时过锁后重复加载）
                if cache_key not in self.__class__._model_cache:
                    model = WhisperModel(model_name, device=device, compute_type=compute_type)
                    self.__class__._model_cache[cache_key] = model
        else:
            model = self.__class__._model_cache[cache_key]

        if not audio_path.exists():
            raise ExtractionError(f"音频文件不存在：{audio_path}，ffmpeg 可能未正确提取音频")

        # 启用 VAD（语音活动检测）过滤静音片段，提升转写速度 30%+
        segments, _ = model.transcribe(
            str(audio_path),
            language="zh",
            vad_filter=True,  # 启用 VAD 过滤静音
            vad_parameters=dict(min_silence_duration_ms=500),  # 最小静音时长 500ms
        )
        result = [
            {
                "start": float(segment.start),
                "end": float(segment.end),
                "text": self._normalize_text(segment.text),
            }
            for segment in segments
        ]

        # 清理超出上限的缓存模型（防止内存泄漏）
        self._trim_model_cache()

        return result

    def _trim_model_cache(self):
        """清理超出 _max_cached_models 限制的缓存模型，释放内存。"""
        with self.__class__._model_lock:
            if len(self.__class__._model_cache) <= self.__class__._max_cached_models:
                return
            # 删除最早加入缓存的模型（简单 FIFO）
            oldest_key = next(iter(self.__class__._model_cache))
            del self.__class__._model_cache[oldest_key]

    @classmethod
    def clear_model_cache(cls):
        """手动清理所有缓存的 Whisper 模型（释放内存）。"""
        with cls._model_lock:
            cls._model_cache.clear()
            logger.info("已清理 Whisper 模型缓存")

    def _get_video_duration(self, video_path: Path) -> float:
        """使用 ffprobe 获取视频总时长（秒）。"""
        if shutil.which("ffprobe") is None:
            raise ExtractionError("未找到 ffprobe，请先安装 ffmpeg")
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
            raise ExtractionError(f"ffprobe 获取视频时长失败: {result.stderr}")
        return float(result.stdout.strip())

    def extract_frames(self, video_path: Path, count: int = 5) -> list[Path]:
        """从视频中均匀截取 count 张关键帧。

        通过 ffprobe 获取视频总时长，按等间隔时间点使用 ffmpeg 逐帧截取，
        避免依赖未定义的帧序号变量。
        """
        if shutil.which("ffmpeg") is None:
            raise ExtractionError("未找到 ffmpeg")
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
            # 音频提取或转写失败：记录日志，但不污染 text 字段
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(f"音频处理失败: {e}")
            segments = []  # 空列表，text 将为空字符串

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

    def process_with_platform_strategy(self, video_path: Path, platform: str, video_url: str = "") -> dict:
        """根据平台选择最合适的分析策略。
        
        Args:
            video_path: 视频文件路径
            platform: 平台名称（bilibili/douyin/youtube/unknown）
            video_url: 原始视频URL（用于拉取字幕和元数据）
            
        Returns:
            包含 text, segments, frames, metadata, platform 的字典
        """
        transcription_text = ""
        segments = []
        metadata = {}

        if platform == "bilibili":
            # 策略1：尝试拉取B站字幕
            subtitle_text = self._try_extract_bilibili_subtitles(video_url)
            if subtitle_text:
                # 有字幕，跳过 Whisper
                logger.info(f"✅ B站字幕拉取成功，跳过 Whisper 转写")
                transcription_text = subtitle_text
                segments = [{"start": 0, "end": 0, "text": subtitle_text}]
            else:
                # 无字幕，回退到 Whisper
                logger.info(f"⚠️ B站字幕拉取失败，回退到 Whisper 转写")
                audio_path = self.extract_audio(video_path)
                segs = self.transcribe(audio_path)
                transcription_text = " ".join(seg["text"] for seg in segs)
                segments = segs

            # 拉取B站元数据
            metadata = self._extract_bilibili_metadata(video_url)

        elif platform == "douyin":
            # 抖音：用 Whisper 转写
            logger.info(f"抖音视频，使用 Whisper 转写")
            audio_path = self.extract_audio(video_path)
            segs = self.transcribe(audio_path)
            transcription_text = " ".join(seg["text"] for seg in segs)
            segments = segs

            # 拉取抖音元数据
            metadata = self._extract_douyin_metadata(video_url)

        else:
            # 未知平台：通用策略
            logger.info(f"未知平台，使用通用 Whisper 转写策略")
            audio_path = self.extract_audio(video_path)
            segs = self.transcribe(audio_path)
            transcription_text = " ".join(seg["text"] for seg in segs)
            segments = segs

        # 截取关键帧（所有平台都需要）
        frames = []
        try:
            frames = self.extract_frames(video_path)
        except Exception as e:
            logger.warning(f"关键帧截取失败: {e}")
            frames = []

        return {
            "text": transcription_text,
            "segments": segments,
            "frames": [str(f) for f in frames],
            "metadata": metadata,
            "platform": platform,
        }

    def _try_extract_bilibili_subtitles(self, video_url: str) -> str:
        """尝试用 yt-dlp 拉取B站AI字幕，成功返回文本，失败返回空字符串。
        
        Args:
            video_url: B站视频URL
            
        Returns:
            字幕文本（成功）或空字符串（失败）
        """
        import tempfile
        from pathlib import Path as PathLib

        if not video_url:
            return ""

        # 检查 yt-dlp 是否安装
        if shutil.which("yt-dlp") is None:
            logger.warning("yt-dlp 未安装，无法拉取B站字幕")
            return ""

        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                # 用 yt-dlp 下载字幕（不下载视频）
                cmd = [
                    "yt-dlp",
                    "--write-auto-sub",
                    "--skip-download",
                    "--sub-lang", "zh-Hans", "zh", "zh-CN", "chi",  # 优先中文
                    "--convert-subs", "srt",
                    "-o", f"{tmpdir}/subtitle",
                    video_url,
                ]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)

                # 查找生成的字幕文件
                srt_files = list(PathLib(tmpdir).glob("*.srt"))
                vtt_files = list(PathLib(tmpdir).glob("*.vtt"))

                subtitle_file = None
                if srt_files:
                    subtitle_file = srt_files[0]
                elif vtt_files:
                    subtitle_file = vtt_files[0]

                if subtitle_file and subtitle_file.exists():
                    content = subtitle_file.read_text(encoding="utf-8")
                    # 解析 SRT/VTT，提取纯文本
                    return self._parse_subtitle_to_text(content)
        except subprocess.TimeoutExpired:
            logger.warning(f"拉取B站字幕超时: {video_url}")
        except Exception as e:
            logger.warning(f"拉取B站字幕失败: {e}")

        return ""

    def _parse_subtitle_to_text(self, subtitle_content: str) -> str:
        """解析 SRT/VTT 字幕文件，提取纯文本。
        
        Args:
            subtitle_content: SRT或VTT格式的字幕内容
            
        Returns:
            提取的纯文本（合并为一行）
        """
        import re
        lines = subtitle_content.split("\n")
        text_lines = []
        for line in lines:
            line = line.strip()
            # 跳过序号行、时间戳行、空行
            if re.match(r"^\d+$", line):
                continue
            if re.match(r"^\d{2}:\d{2}:\d{2}", line):
                continue
            if line.startswith("WEBVTT"):
                continue
            if line.startswith("NOTE"):
                continue
            if line:
                text_lines.append(line)
        return " ".join(text_lines)

    def _extract_bilibili_metadata(self, video_url: str) -> dict:
        """用 yt-dlp 拉取B站视频元数据。
        
        Args:
            video_url: B站视频URL
            
        Returns:
            包含标题、简介、标签、播放量等信息的字典
        """
        import json

        if not video_url:
            return {}

        # 检查 yt-dlp 是否安装
        if shutil.which("yt-dlp") is None:
            logger.warning("yt-dlp 未安装，无法拉取B站元数据")
            return {}

        try:
            cmd = ["yt-dlp", "--dump-json", "--skip-download", video_url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                info = json.loads(result.stdout)
                return {
                    "title": info.get("title", ""),
                    "description": info.get("description", ""),
                    "tags": info.get("tags", []),
                    "duration": info.get("duration", 0),
                    "view_count": info.get("view_count", 0),
                    "danmaku_count": info.get("danmaku_count", 0),
                    "platform": "bilibili",
                }
        except subprocess.TimeoutExpired:
            logger.warning(f"拉取B站元数据超时: {video_url}")
        except json.JSONDecodeError as e:
            logger.warning(f"解析B站元数据JSON失败: {e}")
        except Exception as e:
            logger.warning(f"拉取B站元数据失败: {e}")

        return {}

    def _extract_douyin_metadata(self, video_url: str) -> dict:
        """用 yt-dlp 拉取抖音视频元数据。
        
        Args:
            video_url: 抖音视频URL
            
        Returns:
            包含标题、描述、点赞数等信息的字典
        """
        import json

        if not video_url:
            return {}

        # 检查 yt-dlp 是否安装
        if shutil.which("yt-dlp") is None:
            logger.warning("yt-dlp 未安装，无法拉取抖音元数据")
            return {}

        try:
            cmd = ["yt-dlp", "--dump-json", "--skip-download", video_url]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            if result.returncode == 0 and result.stdout:
                info = json.loads(result.stdout)
                return {
                    "title": info.get("title", ""),
                    "description": info.get("description", ""),
                    "duration": info.get("duration", 0),
                    "view_count": info.get("view_count", 0),
                    "like_count": info.get("like_count", 0),
                    "platform": "douyin",
                }
        except subprocess.TimeoutExpired:
            logger.warning(f"拉取抖音元数据超时: {video_url}")
        except json.JSONDecodeError as e:
            logger.warning(f"解析抖音元数据JSON失败: {e}")
        except Exception as e:
            logger.warning(f"拉取抖音元数据失败: {e}")

        return {}
