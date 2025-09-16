"""
视频获取器工厂类
使用工厂模式创建不同平台的视频获取器
"""

from typing import Dict, Type, Optional
from enum import Enum
from .base_fetcher import BaseFetcher
from .douyin_video_fetcher import DouyinVideoFetcher
from .xiaohongshu_fetcher import XiaohongshuFetcher



class Platform(Enum):
    """支持的平台枚举"""
    DOUYIN = "douyin"
    XIAOHONGSHU = "xiaohongshu"

    @classmethod
    def get_all_platforms(cls) -> list:
        """获取所有支持的平台"""
        return [platform.value for platform in cls]

    @classmethod
    def from_string(cls, platform_str: str) -> 'Platform':
        """从字符串创建平台枚举"""
        platform_str = platform_str.lower().strip()
        for platform in cls:
            if platform.value == platform_str:
                return platform
        raise ValueError(f"不支持的平台: {platform_str}，支持的平台: {cls.get_all_platforms()}")


class FetcherFactory:
    """视频获取器工厂类"""

    # 平台与获取器类的映射
    _fetcher_registry: Dict[Platform, Type[BaseFetcher]] = {
        Platform.DOUYIN: DouyinVideoFetcher,
        Platform.XIAOHONGSHU: XiaohongshuFetcher,
    }

    @classmethod
    def create_fetcher(cls, platform: str) -> BaseFetcher:
        """
        创建指定平台的视频获取器

        Args:
            platform (str): 平台名称 (douyin, xiaohongshu)

        Returns:
            BaseFetcher: 对应平台的视频获取器实例

        Raises:
            ValueError: 不支持的平台
            Exception: 创建获取器失败
        """
        try:
            platform_enum = Platform.from_string(platform)
            fetcher_class = cls._fetcher_registry.get(platform_enum)

            if fetcher_class is None:
                raise ValueError(f"平台 {platform} 的获取器未注册")

            return fetcher_class()

        except ValueError as e:
            raise e
        except Exception as e:
            raise Exception(f"创建 {platform} 平台获取器失败: {str(e)}")

    @classmethod
    def register_fetcher(cls, platform: Platform, fetcher_class: Type[BaseFetcher]) -> None:
        """
        注册新的获取器类

        Args:
            platform (Platform): 平台枚举
            fetcher_class (Type[BaseFetcher]): 获取器类

        Raises:
            TypeError: 获取器类不是 BaseFetcher 的子类
        """
        if not issubclass(fetcher_class, BaseFetcher):
            raise TypeError(f"获取器类必须继承自 BaseFetcher")

        cls._fetcher_registry[platform] = fetcher_class
        print(f"已注册 {platform.value} 平台获取器: {fetcher_class.__name__}")

    @classmethod
    def get_supported_platforms(cls) -> list:
        """
        获取所有支持的平台列表

        Returns:
            list: 支持的平台名称列表
        """
        return [platform.value for platform in cls._fetcher_registry.keys()]

    @classmethod
    def is_platform_supported(cls, platform: str) -> bool:
        """
        检查平台是否支持

        Args:
            platform (str): 平台名称

        Returns:
            bool: 是否支持该平台
        """
        try:
            Platform.from_string(platform)
            return True
        except ValueError:
            return False

    @classmethod
    def get_fetcher_info(cls) -> Dict[str, str]:
        """
        获取所有注册的获取器信息

        Returns:
            Dict[str, str]: 平台名称到获取器类名的映射
        """
        return {
            platform.value: fetcher_class.__name__
            for platform, fetcher_class in cls._fetcher_registry.items()
        }


# 便捷函数
def create_fetcher(platform: str) -> BaseFetcher:
    """
    便捷函数：创建视频获取器

    Args:
        platform (str): 平台名称

    Returns:
        BaseFetcher: 视频获取器实例
    """
    return FetcherFactory.create_fetcher(platform)


def get_supported_platforms() -> list:
    """
    便捷函数：获取支持的平台列表

    Returns:
        list: 支持的平台名称列表
    """
    return FetcherFactory.get_supported_platforms()





if __name__ == "__main__":
    # 测试工厂模式
    print("=== 视频获取器工厂测试 ===")

    # 显示支持的平台
    print(f"支持的平台: {get_supported_platforms()}")
    print(f"获取器信息: {FetcherFactory.get_fetcher_info()}")

    # 测试创建不同平台的获取器
    for platform in get_supported_platforms():
        try:
            fetcher = create_fetcher(platform)
            print(f"✅ 成功创建 {platform} 获取器: {fetcher}")
        except Exception as e:
            print(f"❌ 创建 {platform} 获取器失败: {e}")

    # 测试不支持的平台
    try:
        fetcher = create_fetcher("unsupported_platform")
    except Exception as e:
        print(f"✅ 正确处理不支持的平台: {e}")
