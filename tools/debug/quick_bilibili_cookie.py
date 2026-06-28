#!/usr/bin/env python3
"""
B站Cookie快速配置脚本
使用方法：
  python quick_bilibili_cookie.py "SESSDATA=xxx; bili_jct=yyy; DedeUserID=zzz"
"""

import json
import sys
from pathlib import Path


def parse_cookie_string(cookie_str: str) -> dict:
    """解析Cookie字符串"""
    cookies = {}
    try:
        pairs = cookie_str.split(";")
        for pair in pairs:
            pair = pair.strip()
            if "=" in pair:
                key, value = pair.split("=", 1)
                cookies[key.strip()] = value.strip()
        return cookies
    except Exception as e:
        print(f"❌ 解析Cookie字符串失败：{e}")
        return {}


def save_cookies(cookies: dict, output_file: str = "config/bilibili_cookies.json"):
    """保存Cookie到文件"""
    try:
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(cookies, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Cookie已保存到：{output_path}")
        return True
    except Exception as e:
        print(f"❌ 保存Cookie失败：{e}")
        return False


def main():
    print("=" * 60)
    print("B站Cookie快速配置工具")
    print("=" * 60)
    
    if len(sys.argv) < 2:
        print("\n使用方法：")
        print('  python quick_bilibili_cookie.py "SESSDATA=xxx; bili_jct=yyy"')
        print("\n获取Cookie的步骤：")
        print("1. 打开浏览器，访问 https://www.bilibili.com/ 并登录")
        print("2. 按 F12 打开开发者工具")
        print("3. 切换到「控制台」(Console) 标签")
        print("4. 输入并运行：document.cookie")
        print("5. 复制输出的Cookie字符串")
        print("6. 运行本脚本并粘贴Cookie字符串")
        print("\n示例：")
        print('  python quick_bilibili_cookie.py "SESSDATA=xxx; bili_jct=yyy; DedeUserID=zzz"')
        return
    
    # 解析Cookie
    cookie_str = " ".join(sys.argv[1:])
    print(f"\n正在解析Cookie字符串...")
    cookies = parse_cookie_string(cookie_str)
    
    if not cookies:
        print("❌ 未解析到任何Cookie")
        return
    
    print(f"✅ 成功解析 {len(cookies)} 个Cookie：")
    for key in cookies.keys():
        print(f"   - {key}")
    
    # 检查必需Cookie
    required = ["SESSDATA", "bili_jct", "DedeUserID"]
    missing = [key for key in required if key not in cookies]
    
    if missing:
        print(f"\n⚠️  缺少 recommended Cookie：{', '.join(missing)}")
        print("这些Cookie可能不是必需的，但推荐配置。")
    
    # 保存
    print(f"\n正在保存Cookie...")
    if save_cookies(cookies):
        print(f"\n{'=' * 60}")
        print("✅ Cookie配置完成！")
        print(f"{'=' * 60}")
        print("\n接下来可以运行：")
        print("  python test_ytdlp_bilibili.py")
        print("来测试B站视频下载。")
    else:
        print("\n❌ Cookie配置失败")


if __name__ == "__main__":
    main()
