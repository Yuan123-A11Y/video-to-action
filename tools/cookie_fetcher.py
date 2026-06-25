#!/usr/bin/env python3
"""
通用视频平台Cookie获取工具
基于 Playwright 自动打开浏览器让用户登录，然后提取并保存Cookie。

支持平台：
  - 抖音 (douyin)
  - 哔哩哔哩 (bilibili)
  - YouTube (youtube)

使用方法：
  # 获取B站Cookie
  python tools/cookie_fetcher.py --platform bilibili

  # 获取抖音Cookie
  python tools/cookie_fetcher.py --platform douyin

  # 自动等待60秒后抓取（适合AI终端无交互场景）
  python tools/cookie_fetcher.py --platform bilibili --auto-wait 60

  # 指定输出文件和配置文件
  python tools/cookie_fetcher.py --platform bilibili --output config/bilibili_cookies.json --config config/settings.yaml
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence


# 平台配置：登录URL、域名、必需Cookie、推荐Cookie
PLATFORMS = {
    "bilibili": {
        "name": "哔哩哔哩 (B站)",
        "url": "https://www.bilibili.com/",
        "domain": "bilibili.com",
        "required_keys": {"SESSDATA", "bili_jct", "DedeUserID"},
        "suggested_keys": {"SESSDATA", "bili_jct", "DedeUserID", "DedeUserID__ckMd5", "sid", "buvid3"},
        "default_output": "config/bilibili_cookies.json",
    },
    "douyin": {
        "name": "抖音",
        "url": "https://www.douyin.com/",
        "domain": "douyin.com",
        "required_keys": {"msToken", "ttwid", "odin_tt", "passport_csrf_token"},
        "suggested_keys": {"msToken", "ttwid", "odin_tt", "passport_csrf_token", "sid_guard", "sessionid", "sid_tt"},
        "default_output": "config/douyin_cookies.json",
    },
    "youtube": {
        "name": "YouTube",
        "url": "https://www.youtube.com/",
        "domain": "youtube.com",
        "required_keys": set(),  # YouTube不需要特定Cookie
        "suggested_keys": set(),
        "default_output": "config/youtube_cookies.json",
    },
}

PRIMARY_WAIT_UNTIL = "networkidle"
FALLBACK_WAIT_UNTIL = "domcontentloaded"
PRIMARY_TIMEOUT_MS = 300_000
FALLBACK_TIMEOUT_MS = 300_000


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="通用视频平台Cookie获取工具 - 打开浏览器引导登录，然后提取Cookie",
    )
    parser.add_argument(
        "--platform",
        choices=list(PLATFORMS.keys()),
        required=True,
        help="目标平台 (bilibili / douyin / youtube)",
    )
    parser.add_argument(
        "--url",
        default=None,
        help=f"登录页面URL (默认使用平台的默认URL)",
    )
    parser.add_argument(
        "--browser",
        choices=["chromium", "firefox", "webkit"],
        default="chromium",
        help="Playwright 浏览器引擎 (默认: chromium)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="无头模式运行 (不推荐用于手动登录)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="输出Cookie的JSON文件路径",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="可选：同时更新YAML配置文件中的Cookie",
    )
    parser.add_argument(
        "--include-all",
        action="store_true",
        help="保存所有Cookie而非只保存推荐的子集",
    )
    parser.add_argument(
        "--auto-wait",
        type=int,
        default=0,
        metavar="SECONDS",
        help="等待指定秒数后自动抓取Cookie，无需按Enter (适合AI终端无交互场景)",
    )
    return parser.parse_args(argv or sys.argv[1:])


async def capture_cookies(args: argparse.Namespace) -> int:
    """主流程：打开浏览器 → 引导登录 → 提取Cookie → 保存"""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        print("[ERROR] 未安装 Playwright，请先运行: pip install playwright && playwright install chromium", file=sys.stderr)
        return 1

    platform_cfg = PLATFORMS[args.platform]
    url = args.url or platform_cfg["url"]
    domain = platform_cfg["domain"]
    output = args.output or Path(platform_cfg["default_output"])

    print(f"\n{'=' * 60}")
    print(f"🍪 {platform_cfg['name']} Cookie 获取工具")
    print(f"{'=' * 60}")
    print(f"\n目标平台: {platform_cfg['name']}")
    print(f"登录页面: {url}")
    print(f"输出文件: {output.resolve()}")
    print(f"\n{'─' * 60}\n")

    async with async_playwright() as p:
        browser_factory = getattr(p, args.browser)
        browser = await browser_factory.launch(headless=args.headless)
        context = await browser.new_context()
        page = await context.new_page()

        if args.auto_wait > 0:
            print(f"[INFO] 浏览器已启动，请在 {args.auto_wait} 秒内完成 {platform_cfg['name']} 登录。")
            print("[INFO] 时间到后会自动抓取当前Cookie，无需在终端按Enter。\n")
        else:
            print(f"[INFO] ✅ 浏览器已打开！请在弹出的窗口中完成 {platform_cfg['name']} 登录。")
            print("[INFO] 登录成功并看到首页后，回到此终端按 Enter 键继续...\n")

        # 导航 + 等待登录确认
        await wait_for_login_confirmation(page, url, auto_wait_seconds=args.auto_wait)

        # 从浏览器存储状态提取Cookie
        print("\n[INFO] 正在提取Cookie...")
        storage = await context.storage_state()
        cookies = {
            cookie["name"]: cookie["value"]
            for cookie in storage["cookies"]
            if domain in cookie.get("domain", "")
        }

        await context.close()
        await browser.close()

    # 过滤Cookie
    suggested = platform_cfg["suggested_keys"] or {}
    required = platform_cfg["required_keys"]

    if args.include_all:
        picked = cookies
    elif suggested:
        picked = {k: v for k, v in cookies.items() if k in suggested}
        # 如果过滤后没有Cookie，保留全部
        if not picked:
            picked = cookies
            print("[WARN] 未找到推荐的Cookie子集，保留所有Cookie")
    else:
        picked = cookies

    # 保存JSON
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(picked, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✅ 已保存 {len(picked)} 个Cookie到：{output.resolve()}")

    # 检查必需Cookie
    missing_required = required - picked.keys() if required else set()
    if missing_required:
        print(f"\n⚠️  缺少必需Cookie: {', '.join(sorted(missing_required))}")
        print("   这可能导致下载失败，请确保已完成登录。")
    else:
        print(f"\n✅ 所需Cookie已完整获取!")

    # 显示关键Cookie状态
    key_list = sorted(required | suggested) if suggested else sorted(cookies.keys())[:5]
    for key in key_list[:6]:
        status = "✅" if key in picked else "❌"
        val_preview = (picked[key][:16] + "...") if key in picked and len(picked[key]) > 16 else (picked.get(key) or "-")
        print(f"   {status} {key}: {val_preview}")

    # 更新YAML配置（可选）
    if args.config:
        update_config_with_cookie(args.config, args.platform, output)

    return 0


def is_timeout_error(exc: Exception) -> bool:
    return exc.__class__.__name__ == "TimeoutError" or "Timeout" in str(exc)


def is_target_closed_error(exc: Exception) -> bool:
    return exc.__class__.__name__ == "TargetClosedError" or "Target page, context or browser has been closed" in str(exc)


async def goto_with_fallback(page: Any, url: str) -> str:
    """导航到目标页面，带降级策略"""
    try:
        await page.goto(url, wait_until=PRIMARY_WAIT_UNTIL, timeout=PRIMARY_TIMEOUT_MS)
        return PRIMARY_WAIT_UNTIL
    except Exception as exc:
        if is_target_closed_error(exc):
            print("[WARN] 浏览器/页面在导航过程中被关闭，继续使用当前状态")
            return "target_closed"
        if not is_timeout_error(exc):
            raise
        print(f"[WARN] goto(wait_until={PRIMARY_WAIT_UNTIL}) 超时 ({PRIMARY_TIMEOUT_MS}ms)，降级为 {FALLBACK_WAIT_UNTIL}")
    try:
        await page.goto(url, wait_until=FALLBACK_WAIT_UNTIL, timeout=FALLBACK_TIMEOUT_MS)
        return FALLBACK_WAIT_UNTIL
    except Exception as exc:
        if is_target_closed_error(exc):
            print("[WARN] 降级导航时页面被关闭，继续使用当前状态")
            return "target_closed"
        if is_timeout_error(exc):
            print(f"[WARN] 降级导航也超时了 ({FALLBACK_TIMEOUT_MS}ms)，继续执行")
            return "timeout"
        raise


async def wait_for_login_confirmation(page: Any, url: str, *, auto_wait_seconds: int = 0) -> None:
    """等待用户完成登录"""
    if auto_wait_seconds > 0:
        nav_task = asyncio.create_task(goto_with_fallback(page, url))
        await asyncio.sleep(auto_wait_seconds)
        if not nav_task.done():
            nav_task.cancel()
            try:
                await nav_task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                print(f"[WARN] 导航任务取消后出错: {exc}")
        else:
            try:
                await nav_task
            except Exception as exc:
                print(f"[WARN] 导航任务结束: {exc}")
    else:
        nav_task = asyncio.create_task(goto_with_fallback(page, url))
        await asyncio.sleep(0)  # 让nav_task进入await点
        try:
            await asyncio.to_thread(input)
        except EOFError:
            pass

        if not nav_task.done():
            nav_task.cancel()
            try:
                await nav_task
            except asyncio.CancelledError:
                pass
            except Exception as exc:
                print(f"[WARN] 导航任务结束: {exc}")
            return

        try:
            await nav_task
        except Exception as exc:
            print(f"[WARN] 导航任务结束: {exc}")


def update_config_with_cookie(config_path: Path, platform: str, cookie_file: Path) -> None:
    """更新YAML配置文件中的Cookie路径"""
    import yaml

    existing: dict = {}
    if config_path.exists():
        existing = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}

    # 确保 download.cookies.<platform> 指向正确的文件
    if "download" not in existing:
        existing["download"] = {}
    if "cookies" not in existing["download"]:
        existing["download"]["cookies"] = {}

    # 使用相对于配置文件的路径
    rel_path = cookie_file.resolve().relative_to(Path.cwd().resolve())
    existing["download"]["cookies"][platform] = {"file": str(rel_path)}

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(yaml.dump(existing, allow_unicode=True, sort_keys=False), encoding="utf-8")
    print(f"\n✅ 已更新配置文件: {config_path.resolve()}")
    print(f"   download.cookies.{platform}.file = {rel_path}")


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    return asyncio.run(capture_cookies(args))


if __name__ == "__main__":
    raise SystemExit(main())
