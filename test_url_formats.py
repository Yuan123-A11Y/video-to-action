"""
URL 格式支持测试脚本。

测试各种视频 URL 格式是否被正确处理：
- 抖音短链
- 抖音 /video/ 格式
- 抖音 modal_id 参数格式
- B站 URL 格式
- YouTube URL 格式
"""

from video_to_action.downloader import detect_video_platform, _extract_video_id_from_url


def test_url_formats():
    """测试各种 URL 格式。"""
    test_cases = [
        # 抖音 URL 格式
        ("https://v.douyin.com/iRNBho6/", "douyin", None),
        ("https://www.douyin.com/video/7513843872540233023", "douyin", "7513843872540233023"),
        ("https://www.douyin.com/jingxuan/course?modal_id=7513843872540233023", "douyin", "7513843872540233023"),
        ("https://www.douyin.com/aweme/v1/play/?modal_id=7513843872540233023", "douyin", "7513843872540233023"),
        # B站 URL 格式
        ("https://www.bilibili.com/video/BV1xx411c7mD", "bilibili", None),
        ("https://b23.tv/BV1xx411c7mD", "bilibili", None),
        # YouTube URL 格式
        ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "youtube", None),
        ("https://youtu.be/dQw4w9WgXcQ", "youtube", None),
        # 未知 URL
        ("https://www.example.com/video/123", "unknown", None),
    ]

    print("URL 格式支持测试结果：")
    print("=" * 80)

    for url, expected_platform, expected_video_id in test_cases:
        platform = detect_video_platform(url)
        video_id = _extract_video_id_from_url(url)

        platform_ok = platform == expected_platform
        video_id_ok = video_id == expected_video_id

        status = "✅" if platform_ok and video_id_ok else "❌"

        print(f"{status} {url}")
        print(f"   平台: {platform} (期望: {expected_platform}) {'✅' if platform_ok else '❌'}")
        print(f"   视频ID: {video_id} (期望: {expected_video_id}) {'✅' if video_id_ok else '❌'}")
        print()


if __name__ == "__main__":
    test_url_formats()
