from abc import ABC, abstractmethod

class BaseModule(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """Tên của module (cd: 'headers', 'cookies', 'tls')"""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Mô tả ngắn về module"""
        pass

    @abstractmethod
    async def scan(self, url: str, **kwargs) -> list:
        """Thực hiện quét bảo mật theo URL, trả về danh sách findings"""
        pass

    def get_info(self) -> dict:
        return {"name": self.name, "description": self.description}