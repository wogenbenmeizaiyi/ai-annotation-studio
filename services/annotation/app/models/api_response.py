
from dataclasses import dataclass
from typing import Generic, TypeVar, Optional, Any
from datetime import datetime

T = TypeVar('T')

@dataclass
class ApiResponse(Generic[T]):
    """统一的API响应类型"""
    success: bool
    message: str
    data: Optional[T] = None
    code: int = 200  # HTTP状态码或自定义业务码
    
    @classmethod
    def success_response(cls, data: T, message: str = "成功") -> 'ApiResponse[T]':
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error_response(cls, message: str, code: int = 400) -> 'ApiResponse':
        return cls(success=False, message=message, code=code)

# 业务异常类
class BusinessError(Exception):
    def __init__(self, message: str, code: int = 400):
        self.message = message
        self.code = code
        super().__init__(message)

class TaskNameExistsError(BusinessError):
    pass

