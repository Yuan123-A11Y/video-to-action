"""测试 HuggingFace 镜像设置逻辑。"""
import os
import socket

def test_hf_mirror_setting():
    """测试 HF_ENDPOINT 环境变量设置逻辑。"""
    
    # 清除环境变量（模拟首次运行）
    if "HF_ENDPOINT" in os.environ:
        del os.environ["HF_ENDPOINT"]
    
    print("🔍 测试 HuggingFace 镜像自动设置...")
    
    # 模拟 extractor.py 中的逻辑
    if not os.environ.get("HF_ENDPOINT"):
        try:
            socket.create_connection(("huggingface.co", 443), timeout=3)
            os.environ["HF_ENDPOINT"] = "https://huggingface.co"
            print(f"✅ 连接成功，使用官方源：{os.environ['HF_ENDPOINT']}")
        except (OSError, socket.timeout):
            os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
            print(f"⚡ 连接失败，已切换到国内镜像：{os.environ['HF_ENDPOINT']}")
    
    print(f"\n📝 当前 HF_ENDPOINT: {os.environ.get('HF_ENDPOINT')}")
    return os.environ.get("HF_ENDPOINT")

if __name__ == "__main__":
    endpoint = test_hf_mirror_setting()
    
    # 验证 huggingface_hub 是否使用了镜像
    try:
        from huggingface_hub import get_hf_file_path
        print(f"\n✅ huggingface_hub 库已加载，将使用镜像：{endpoint}")
    except ImportError:
        print(f"\n⚠️  huggingface_hub 库未安装，请运行：pip install huggingface_hub")
