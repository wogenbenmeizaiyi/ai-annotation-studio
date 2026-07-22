
# 创建简化版的脚本，去掉最后的 pause
simplified_script = '''@echo off
chcp 65001 >nul

:: ===========================================
:: 强力清理 Python/Celery 进程工具
:: ===========================================

echo.
echo [!] 警告: 这将关闭所有 Python、Celery 和 Uvicorn 进程
echo [!] 包括其他项目的 Python 程序！
echo.
set /p confirm="确定继续? (yes/no): "
if not "%confirm%"=="yes" exit /b

echo.
echo [*] 正在强力清理...

:: 关闭所有 celery
taskkill /F /IM celery.exe >nul 2>&1 && echo [√] 已关闭所有 celery.exe || echo [i] 未发现 celery 进程

:: 关闭所有 python
taskkill /F /IM python.exe >nul 2>&1 && echo [√] 已关闭所有 python.exe || echo [i] 未发现 python 进程

:: 关闭所有 uvicorn
taskkill /F /IM uvicorn.exe >nul 2>&1 && echo [√] 已关闭所有 uvicorn.exe || echo [i] 未发现 uvicorn 进程

echo.
echo [*] 清理完成
'''

# 保存到输出目录
output_path = '/mnt/kimi/output/kill_python_processes.bat'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(simplified_script)

print(f"已保存到: {output_path}")
print("\n脚本内容:")
print(simplified_script)
