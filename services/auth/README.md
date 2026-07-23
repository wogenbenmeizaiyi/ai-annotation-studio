# Auth Service

AI Annotation Studio 的独立认证服务，负责注册审批、登录、Cookie 会话、刷新令牌轮换、
密码修改和超级管理员用户管理。业务服务通过 Ed25519 公钥验证访问令牌，并通过 Redis
读取用户状态和会话撤销状态。

本地完整启动由仓库根目录的 `scripts/dev.ps1` 管理。首次创建超级管理员：

```powershell
$env:APP_ENV_FILE = (Resolve-Path ..\..\.local\env\auth.env).Path
uv run python -m scripts.create_super_admin
```

服务默认端口为 `8787`。生产环境必须挂载已有的签名私钥和公钥，服务不会在生产模式自动
生成密钥。
