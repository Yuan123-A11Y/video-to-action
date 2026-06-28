#!/usr/bin/env python3
"""
抖音视频下载工具 v9 - 通过 Playwright 执行页面 JS 直接读视频数据
绕过 API 签名问题：页面加载后会把视频数据写入 JS 变量，直接读就行
"""
import asyncio
import json
import re
import sys
from pathlib import Path


async def get_video_info(url: str) -> dict:
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] 请先安装 Playwright")
        return None

    cookie_file = Path("config/douyin_cookies.txt")
    if not cookie_file.exists():
        print(f"[ERROR] Cookie 文件不存在: {cookie_file}")
        return None

    cookies = []
    with open(cookie_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("#") or not line.strip():
                continue
            parts = line.strip().split("\t")
            if len(parts) >= 7:
                cookies.append({
                    "name": parts[5], "value": parts[6],
                    "domain": parts[0], "path": parts[2],
                    "secure": parts[3] == "TRUE", "httpOnly": False,
                    "expires": float(parts[4]) if parts[4] != "0" else -1,
                })

    print(f"[INFO] 已加载 {len(cookies)} 个 Cookie")

    result = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-ime",
                "--disable-features=RendererCodeIntegrity",
            ]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        await context.add_cookies(cookies)
        page = await context.new_page()

        # 监听所有响应，保存 aweme/detail 的完整响应体
        responses = {}

        async def on_response(resp):
            url_str = resp.url
            if "aweme/v1/web/aweme/detail" in url_str and resp.request.method == "GET":
                try:
                    body_bytes = await resp.body()
                    responses[url_str] = body_bytes.decode("utf-8", errors="replace")
                    print(f"[INFO] ✅ 捕获 API 响应 ({len(body_bytes)} bytes)")
                except Exception as e:
                    print(f"[WARN] 读取响应失败: {e}")

        page.on("response", on_response)

        # 用完整 URL（不是短链接）
        if "v.douyin.com" in url:
            print(f"[INFO] 短链接，先解析...")
            try:
                resp = await page.goto(url, wait_until="domcontentloaded", timeout=15000)
                url = str(page.url)
                print(f"[INFO] 解析后 URL: {url}")
            except Exception:
                url = str(page.url) if page.url else url
        else:
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            except Exception:
                pass

        # 等待页面 JS 执行，API 会被自动调用
        print("[INFO] 等待页面加载（10秒）...")
        await asyncio.sleep(10)

        # 方式1: 从拦截的 API 响应解析
        if responses:
            for url_key, body in responses.items():
                try:
                    data = json.loads(body)
                    aweme = data.get("aweme_detail", {})
                    if aweme:
                        video = aweme.get("video", {})
                        title = aweme.get("desc", "")
                        video_url = extract_video_url(video)
                        if video_url:
                            result = {"title": title, "video_url": video_url}
                            print(f"[INFO] ✅ 从 API 解析: {title[:40]}")
                            break
                except Exception:
                    pass

        # 方式2: 从页面 window 对象读取（页面 JS 会把数据写入全局变量）
        if not result:
            print("[INFO] 从页面 JS 变量读取...")
            try:
                # 抖音页面会把视频数据放在 window._ROUTER_DATA 或 window.__NEXT_DATA__
                js_data = await page.evaluate("""
                    () => {
                        // 尝试多个可能的全局变量
                        const sources = [
                            () => window._ROUTER_DATA,
                            () => window.__NEXT_DATA__,
                            () => window.__INITIAL_STATE__,
                            () => document.getElementById('__NEXT_DATA__')?.textContent,
                            () => document.getElementById('RENDER_DATA')?.textContent,
                        ];
                        for (const fn of sources) {
                            try {
                                const d = fn();
                                if (d) return typeof d === 'string' ? d : JSON.stringify(d);
                            } catch(e) {}
                        }
                        return null;
                    }
                """)
                if js_data:
                    from urllib.parse import unquote
                    try:
                        data = json.loads(js_data if not js_data.startswith('%') else unquote(js_data))
                        # 递归搜索 video 和 playAddr
                        found = find_video_in_obj(data)
                        if found:
                            result = found
                            print(f"[INFO] ✅ 从 JS 变量解析: {found['title'][:40]}")
                    except Exception as e:
                        print(f"[WARN] 解析 JS 数据失败: {e}")
            except Exception as e:
                print(f"[WARN] 读取 JS 变量失败: {e}")

        await context.close()
        await browser.close()

    return result or None


def find_video_in_obj(obj, depth=0) -> dict:
    """递归在对象中查找视频地址"""
    if depth > 7 or not obj:
        return None

    if isinstance(obj, dict):
        # 检查是否有 video 字段且包含 playAddr
        video = obj.get("video", {})
        if video and isinstance(video, dict):
            url = extract_video_url(video)
            if url:
                title = obj.get("desc", obj.get("title", "douyin_video"))
                return {"title": title, "video_url": url}

        # 递归搜索
        for v in obj.values():
            result = find_video_in_obj(v, depth + 1)
            if result:
                return result

    elif isinstance(obj, list):
        for item in obj:
            result = find_video_in_obj(item, depth + 1)
            if result:
                return result

    return None


def extract_video_url(video: dict) -> str:
    if not video or not isinstance(video, dict):
        return None
    pa = video.get("play_addr", {})
    if isinstance(pa, dict) and pa.get("url_list"):
        return pa["url_list"][0]
    da = video.get("download_addr", {})
    if isinstance(da, dict) and da.get("url_list"):
        return da["url_list"][0]
    br = video.get("bit_rate", [])
    if br and isinstance(br, list):
        for item in sorted(br, key=lambda x: x.get("bit_rate", 0), reverse=True):
            ba = item.get("play_addr", {})
            if isinstance(ba, dict) and ba.get("url_list"):
                return ba["url_list"][0]
    return None


async def download_video(video_url: str, title: str, output_dir: str = "outputs/douyin") -> bool:
    import requests
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    safe_title = re.sub(r'[\\/*?:"<>|]', "", (title or "douyin_video")[:50]).strip() or "douyin_video"
    output_file = output_dir / f"{safe_title}.mp4"

    print(f"[INFO] 开始下载: {output_file.name}")
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://www.douyin.com/",
        }
        resp = requests.get(video_url, headers=headers, stream=True, timeout=120, allow_redirects=True)
        resp.raise_for_status()

        total = int(resp.headers.get("content-length", 0))
        downloaded = 0

        with open(output_file, "wb") as f:
            for chunk in resp.iter_content(chunk_size=131072):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = downloaded * 100 / total
                        print(f"\r[INFO] 下载中... {pct:.1f}% ({downloaded/1024/1024:.1f}/{total/1024/1024:.1f} MB)", end="", flush=True)

        print(f"\n[INFO] ✅ 下载完成: {downloaded/1024/1024:.2f} MB")
        print(f"[INFO] 路径: {output_file.resolve()}")
        return True
    except Exception as e:
        print(f"\n[ERROR] 下载失败: {e}")
        return False


async def main_async():
    if len(sys.argv) < 2:
        print("用法: python tools/douyin_downloader.py <抖音视频链接>")
        return 1

    url = sys.argv[1]
    info = await get_video_info(url)
    if not info or not info.get("video_url"):
        print("[ERROR] 无法获取视频信息或视频地址")
        print("[INFO] 请确保 Cookie 有效，并重新获取：")
        print("       python tools/cookie_fetcher.py --platform douyin --format netscape --auto-wait 90")
        return 1

    print(f"\n[INFO] 视频: {info.get('title', '')[:60]}")
    print(f"[INFO] 地址: {info['video_url'][:100]}...")
    ok = await download_video(info["video_url"], info.get("title", ""))
    return 0 if ok else 1


def main():
    sys.exit(asyncio.run(main_async()))


if __name__ == "__main__":
    main()
