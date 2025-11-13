"""
临时邮箱API调用脚本

调用TikHub的Temp-Mail-API来获取临时邮箱地址
文档: https://api.tikhub.io/#/Temp-Mail-API/get_temp_email_api_v1_temp_mail_v1_get_temp_email_address_get
"""

import json
import os
import pathlib
import time
import requests


def load_env_var(key: str, default: str | None = None) -> str | None:
    """
    从环境变量或.env文件加载配置

    Args:
        key: 环境变量键名
        default: 默认值

    Returns:
        环境变量值或默认值
    """
    # 首先尝试从环境变量获取
    val = os.getenv(key)
    if val:
        return val

    # 回退：向上搜索.env文件
    current = pathlib.Path(__file__).resolve().parent
    for _ in range(10):
        dotenv_path = current / ".env"
        if dotenv_path.exists():
            try:
                for line in dotenv_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip().strip('"').strip("'")
                        if k == key:
                            return v
            except Exception:
                pass
        current = current.parent
    return default


def ensure_output_dir() -> pathlib.Path:
    """
    确保输出目录存在

    Returns:
        输出目录路径
    """
    output_dir = pathlib.Path(__file__).resolve().parent / "output"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def get_temp_email_address() -> dict:
    """
    调用TikHub Temp-Mail-API获取临时邮箱地址

    API文档: https://api.tikhub.io/#/Temp-Mail-API/get_temp_email_api_v1_temp_mail_v1_get_temp_email_address_get

    Returns:
        API响应数据

    Raises:
        RuntimeError: API调用失败时抛出
    """
    # 获取API密钥
    api_key = load_env_var("tikhub_API_KEY")
    if not api_key:
        raise RuntimeError("未找到 tikhub_API_KEY 环境变量，请在.env文件中配置或设置环境变量")

    # 构造API请求
    url = "https://api.tikhub.io/api/v1/temp_mail/v1/get_temp_email_address"

    # 设置请求头
    headers = {
        "Accept": "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-API-KEY": api_key,
    }

    print(f"正在调用Temp-Mail-API: {url}")

    try:
        # 发送GET请求
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()

        # 解析JSON响应
        data = resp.json()

        # 检查业务逻辑状态码
        if data.get('code') == 200:
            print("✅ API调用成功")
            return data
        else:
            error_msg = f"API业务逻辑错误: code={data.get('code')}, message={data.get('message', '未知错误')}"
            print(f"❌ {error_msg}")
            raise RuntimeError(error_msg)

    except requests.RequestException as e:
        error_msg = f"HTTP请求失败: {str(e)}"
        print(f"❌ {error_msg}")
        raise RuntimeError(error_msg)
    except json.JSONDecodeError as e:
        error_msg = f"JSON解析失败: {str(e)}"
        print(f"❌ {error_msg}")
        raise RuntimeError(error_msg)


def save_output(data: dict, output_dir: pathlib.Path) -> str:
    """
    保存API响应数据到文件

    Args:
        data: 要保存的数据
        output_dir: 输出目录

    Returns:
        保存的文件路径
    """
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    filename = f"temp_email_address-{timestamp}.json"
    filepath = output_dir / filename

    with filepath.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return str(filepath)


def main() -> None:
    """
    主函数：获取临时邮箱地址并保存结果
    """
    try:
        print("🚀 开始获取临时邮箱地址...")

        # 调用API获取邮箱地址
        data = get_temp_email_address()

        # 确保输出目录存在
        output_dir = ensure_output_dir()

        # 保存结果
        output_path = save_output(data, output_dir)

        print(f"✅ 结果已保存到: {output_path}")

        # 打印邮箱地址信息（如果存在）
        if 'data' in data and data['data']:
            email_data = data['data']
            if 'email_address' in email_data:
                print(f"📧 获取到的临时邮箱: {email_data['email_address']}")
                print(f"🔐 邮箱密码: {email_data.get('password', 'N/A')}")
                print(f"🌐 邮箱域名: {email_data.get('domain', 'N/A')}")
                print(f"👤 邮箱用户名: {email_data.get('name', 'N/A')}")
            else:
                print("⚠️ 响应中未找到邮箱地址字段")
        else:
            print("⚠️ 响应数据结构异常")

    except Exception as e:
        print(f"❌ 执行失败: {str(e)}")
        exit(1)


if __name__ == "__main__":
    main()
