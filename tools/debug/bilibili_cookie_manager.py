#!/usr/bin/env python3
"""
B站Cookie管理器
用于配置和管理B站视频下载所需的Cookie

使用方法：
1. 手动输入Cookie：python bilibili_cookie_manager.py --manual
2. 从浏览器提取Cookie：python bilibili_cookie_manager.py --browser chrome
3. 验证Cookie：python bilibili_cookie_manager.py --validate
4. 清除Cookie：python bilibili_cookie_manager.py --clear
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

try:
    from rich.console import Console
    from rich.prompt import Prompt, Confirm
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None


class BilibiliCookieManager:
    """B站Cookie管理器"""

    # B站下载所需的关键Cookie
    REQUIRED_COOKIES = ["SESSDATA", "bili_jct", "DedeUserID"]
    OPTIONAL_COOKIES = ["DedeUserID__ckMd5", "sid", "buvid3", "i-wanna-go-back"]

    def __init__(self, cookie_file: str = "config/bilibili_cookies.json"):
        self.cookie_file = Path(cookie_file)
        self.cookies: Dict[str, str] = {}
        self.console = Console() if RICH_AVAILABLE else None

    def print(self, message: str, style: str = ""):
        """打印消息"""
        if self.console:
            self.console.print(message, style=style)
        else:
            print(message)

    def set_cookies(self, cookies: Dict[str, str]):
        """设置Cookie"""
        self.cookies = self._sanitize_cookies(cookies)
        self._save_cookies()
        self.print("✅ Cookie已保存", "green")

    def get_cookies(self) -> Dict[str, str]:
        """获取Cookie"""
        if not self.cookies:
            self._load_cookies()
        return self.cookies

    def get_cookie_string(self) -> str:
        """获取Cookie字符串（用于HTTP请求头）"""
        cookies = self.get_cookies()
        return "; ".join([f"{k}={v}" for k, v in cookies.items()])

    def _sanitize_cookies(self, cookies: Dict[str, str]) -> Dict[str, str]:
        """清理Cookie（移除空值和无效值）"""
        return {k: v for k, v in cookies.items() if k and v}

    def _save_cookies(self):
        """保存Cookie到文件"""
        try:
            self.cookie_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cookie_file, "w", encoding="utf-8") as f:
                json.dump(self.cookies, f, ensure_ascii=False, indent=2)
            self.print(f"💾 Cookie已保存到：{self.cookie_file}", "blue")
        except Exception as e:
            self.print(f"❌ 保存Cookie失败：{e}", "red")

    def _load_cookies(self):
        """从文件加载Cookie"""
        if not self.cookie_file.exists():
            return

        try:
            with open(self.cookie_file, "r", encoding="utf-8") as f:
                self.cookies = json.load(f)
            self.print(f"📂 已从 {self.cookie_file} 加载Cookie", "blue")
        except Exception as e:
            self.print(f"❌ 加载Cookie失败：{e}", "red")

    def validate_cookies(self) -> bool:
        """验证Cookie是否有效"""
        cookies = self.get_cookies()

        if not cookies:
            self.print("❌ 未找到Cookie，请先配置", "red")
            return False

        missing = [key for key in self.REQUIRED_COOKIES if key not in cookies or not cookies.get(key)]
        if missing:
            self.print(f"⚠️  缺少必需的Cookie：{', '.join(missing)}", "yellow")
            return False

        self.print("✅ Cookie验证通过", "green")
        return True

    def clear_cookies(self):
        """清除Cookie"""
        self.cookies = {}
        if self.cookie_file.exists():
            self.cookie_file.unlink()
            self.print("🗑️  Cookie已清除", "yellow")

    def input_manually(self):
        """手动输入Cookie"""
        self.print("=" * 60, "cyan")
        self.print("B站Cookie配置向导", "cyan bold")
        self.print("=" * 60, "cyan")
        self.print("\n请按以下步骤获取B站Cookie：")
        self.print("1. 打开浏览器，访问 https://www.bilibili.com/ 并登录")
        self.print("2. 按 F12 打开开发者工具")
        self.print("3. 切换到「应用」(Application) 标签")
        self.print("4. 在左侧找到「Cookies」->「https://www.bilibili.com」")
        self.print("5. 找到以下Cookie并复制其值：\n")

        cookies = {}

        # 必需Cookie
        self.print("【必需Cookie】", "bold")
        for key in self.REQUIRED_COOKIES:
            value = Prompt.ask(f"  {key}", default="")
            if value:
                cookies[key] = value

        # 可选Cookie
        self.print("\n【可选Cookie（可按回车跳过）】", "bold")
        for key in self.OPTIONAL_COOKIES:
            value = Prompt.ask(f"  {key}", default="")
            if value:
                cookies[key] = value

        # 高级：直接输入Cookie字符串
        self.print("\n【高级】如果您有完整的Cookie字符串，可以直接粘贴：", "bold")
        cookie_str = Prompt.ask("Cookie字符串（格式：key1=value1; key2=value2）", default="")
        if cookie_str:
            self.print("正在解析Cookie字符串...", "blue")
            parsed_cookies = self._parse_cookie_string(cookie_str)
            cookies.update(parsed_cookies)

        # 保存
        if cookies:
            self.set_cookies(cookies)
            self.print("\n" + "=" * 60, "green")
            self.print("✅ Cookie配置完成！", "green bold")
            self.print("=" * 60, "green")
        else:
            self.print("\n❌ 未输入任何Cookie", "red")

    def _parse_cookie_string(self, cookie_str: str) -> Dict[str, str]:
        """解析Cookie字符串"""
        cookies = {}
        try:
            pairs = cookie_str.split(";")
            for pair in pairs:
                if "=" in pair:
                    key, value = pair.strip().split("=", 1)
                    cookies[key.strip()] = value.strip()
            self.print(f"✅ 成功解析 {len(cookies)} 个Cookie", "green")
        except Exception as e:
            self.print(f"❌ 解析Cookie字符串失败：{e}", "red")
        return cookies

    def extract_from_browser(self, browser: str = "chrome"):
        """从浏览器提取Cookie"""
        self.print(f"正在从 {browser} 浏览器提取B站Cookie...", "blue")

        try:
            import browser_cookie3 as bc3
        except ImportError:
            self.print("❌ 未安装 browser-cookie3，请先安装：pip install browser-cookie3", "red")
            return

        try:
            # 从浏览器提取Cookie
            cj = bc3.load(domain_name="bilibili.com", browser=browser)

            cookies = {}
            for cookie in cj:
                if cookie.name in self.REQUIRED_COOKIES or cookie.name in self.OPTIONAL_COOKIES:
                    cookies[cookie.name] = cookie.value

            if cookies:
                self.set_cookies(cookies)
                self.print(f"✅ 成功从 {browser} 提取 {len(cookies)} 个Cookie", "green")
            else:
                self.print("⚠️  未找到B站Cookie，请确保已登录B站", "yellow")

        except Exception as e:
            self.print(f"❌ 从浏览器提取Cookie失败：{e}", "red")
            self.print("请尝试手动输入Cookie", "yellow")

    def show_cookies(self):
        """显示当前Cookie（脱敏）"""
        cookies = self.get_cookies()

        if not cookies:
            self.print("❌ 未找到Cookie", "red")
            return

        self.print("=" * 60, "cyan")
        self.print("当前Cookie：", "cyan bold")
        self.print("=" * 60, "cyan")

        for key, value in cookies.items():
            # 脱敏显示
            if len(value) > 8:
                masked_value = value[:4] + "*" * (len(value) - 8) + value[-4:]
            else:
                masked_value = "*" * len(value)
            self.print(f"  {key}: {masked_value}")

        self.print("=" * 60, "cyan")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="B站Cookie管理器")
    parser.add_argument("--manual", action="store_true", help="手动输入Cookie")
    parser.add_argument("--browser", type=str, help="从浏览器提取Cookie（chrome/firefox/edge）")
    parser.add_argument("--validate", action="store_true", help="验证Cookie")
    parser.add_argument("--show", action="store_true", help="显示Cookie")
    parser.add_argument("--clear", action="store_true", help="清除Cookie")
    parser.add_argument("--file", type=str, default="config/bilibili_cookies.json", help="Cookie文件路径")

    args = parser.parse_args()

    # 创建Cookie管理器
    manager = BilibiliCookieManager(cookie_file=args.file)

    # 如果没有提供参数，显示交互式菜单
    if not any([args.manual, args.browser, args.validate, args.show, args.clear]):
        if RICH_AVAILABLE:
            manager.print("=" * 60, "cyan")
            manager.print("B站Cookie管理器", "cyan bold")
            manager.print("=" * 60, "cyan")
            manager.print("\n请选择操作：")
            manager.print("  1. 手动输入Cookie")
            manager.print("  2. 从浏览器提取Cookie")
            manager.print("  3. 验证Cookie")
            manager.print("  4. 显示Cookie")
            manager.print("  5. 清除Cookie")
            manager.print("  0. 退出\n")

            choice = Prompt.ask("请输入选项", choices=["0", "1", "2", "3", "4", "5"], default="1")

            if choice == "1":
                manager.input_manually()
            elif choice == "2":
                browser = Prompt.ask("请输入浏览器名称", choices=["chrome", "firefox", "edge"], default="chrome")
                manager.extract_from_browser(browser)
            elif choice == "3":
                manager.validate_cookies()
            elif choice == "4":
                manager.show_cookies()
            elif choice == "5":
                manager.clear_cookies()
            elif choice == "0":
                manager.print("退出", "yellow")
        else:
            parser.print_help()
    else:
        # 执行指定的操作
        if args.manual:
            manager.input_manually()
        elif args.browser:
            manager.extract_from_browser(args.browser)
        elif args.validate:
            manager.validate_cookies()
        elif args.show:
            manager.show_cookies()
        elif args.clear:
            manager.clear_cookies()


if __name__ == "__main__":
    main()
