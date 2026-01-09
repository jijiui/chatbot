# 开发流程

按步骤执行，确保可复制与可回归。

## 0. 前提
- Windows 11，本仓库根目录；已安装 Python 3.12。
- 微信客户端 4.1.6.14 登录账号 A，网络可访问 OpenAI。

## 1. 初始化
- 创建/激活虚拟环境：`python -m venv .venv && .\.venv\Scripts\activate`
- 安装依赖：`pip install -r requirements.txt`（如缺失则补充文件后执行）。
- 配置：复制 `config.yaml.example` 为 `config.yaml`，填入 `api_key`、`friend_nickname`（可选 `base_url`）。可用环境变量 `OPENAI_API_KEY` 覆盖 key。

## 2. 实现与运行资产准备
- 生成运行资产：编写/更新 `requirements.txt`，提供 `config.yaml.example`（占位字段 `api_key`、`friend_nickname`、可选 `base_url`）。
- 搭建最小骨架：创建 `main.py`（或 `bot/` 包），包含配置加载、wxautox 监听初始化、ChatGPT API 客户端、节流与重试逻辑。
- 命令验证：确保 `python main.py` 可启动（即便功能未完备），输出基本日志，便于后续增量开发。

## 3. 开发
- 编码后运行格式化与检查：`ruff format . && ruff check .`
- 如改动配置加载/业务逻辑，更新文档并保持类型注解。

## 4. 验证（手动冒烟）
- 启动：`python main.py`（或 `python -m bot`）。
- 用联系人 B 发送文本，验证收到模型回复。
- 断网或用假 key 重试，确认收到失败文案“你太美丽了”。
- 短时间连续两条消息，确认第二条未在 <3 秒内回复（节流生效）。
- 非 B 或非文本消息，确认不回复。
- 强制失焦/退出微信，终端应提示“人工干预”，不再发送。

## 5. 发布准备
- 更新 `requirements.txt` 与 `config.yaml.example`（无敏感信息）。
- 确认上述冒烟用例通过；检查未提交真实密钥。
- 提交代码与文档，按需更新版本号/README，打 tag（如 `v0.1.0`）。

## 6. 运行与回滚
- 日常运行：`python main.py`，保持微信在线；终端即日志。
- 停止：Ctrl+C；重启前确认微信仍在线。
- 回滚：若新版本异常，切回上一个已知 tag/提交，重新按步骤 1–3 验证。
