import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests
import yaml
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

# UI 自动化
try:
    import wxautox
    from wxautox import WeChat
    from wxautox.msgs import FriendMessage, FriendTextMessage
except ImportError as exc:  # pragma: no cover - 提前失败
    raise SystemExit(f"未安装 wxautox，请先 pip install wxautox：{exc}") from exc


@dataclass
class AppConfig:
    api_key: str
    friend_nickname: str
    base_url: str = "https://api.openai.com/v1"
    model: str = "gpt-4.1"
    failure_reply: str = "你太美丽了"
    min_reply_interval: float = 3.0
    request_timeout: int = 15
    max_retries: int = 3


def load_config(path: Path = Path("config.yaml")) -> AppConfig:
    if not path.exists():
        raise SystemExit(f"缺少配置文件：{path}，可复制 config.yaml.example 创建")
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}

    api_key = os.getenv("OPENAI_API_KEY") or raw.get("api_key")
    if not api_key:
        raise SystemExit("未找到 api_key，请在 config.yaml 或环境变量 OPENAI_API_KEY 中设置")

    friend = raw.get("friend_nickname")
    if not friend:
        raise SystemExit("未设置 friend_nickname，请在 config.yaml 填写要监听的联系人昵称")

    return AppConfig(
        api_key=api_key,
        friend_nickname=friend,
        base_url=raw.get("base_url", AppConfig.base_url),
        model=raw.get("model", AppConfig.model),
        failure_reply=raw.get("failure_reply", AppConfig.failure_reply),
        min_reply_interval=float(raw.get("min_reply_interval", AppConfig.min_reply_interval)),
        request_timeout=int(raw.get("request_timeout", AppConfig.request_timeout)),
        max_retries=int(raw.get("max_retries", AppConfig.max_retries)),
    )


class ChatGPTClient:
    def __init__(self, config: AppConfig):
        self.config = config
        self.endpoint = f"{config.base_url.rstrip('/')}/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        }

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=5),
        retry=retry_if_exception_type(requests.RequestException),
    )
    def _request(self, user_text: str) -> str:
        payload = {
            "model": self.config.model,
            "messages": [{"role": "user", "content": user_text}],
        }
        resp = requests.post(
            self.endpoint,
            headers=self.headers,
            json=payload,
            timeout=self.config.request_timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise requests.RequestException("empty choices from API")
        return choices[0]["message"]["content"]

    def chat(self, user_text: str) -> Optional[str]:
        try:
            return self._request(user_text)
        except Exception as exc:
            print(f"[warn] ChatGPT 调用失败：{exc}")
            return None


class RateLimiter:
    def __init__(self, min_interval: float):
        self.min_interval = min_interval
        self._last = 0.0

    def wait(self):
        now = time.time()
        delta = now - self._last
        if delta < self.min_interval:
            time.sleep(self.min_interval - delta)
        self._last = time.time()


class Bot:
    def __init__(self, cfg: AppConfig):
        self.cfg = cfg
        self.client = ChatGPTClient(cfg)
        self.limiter = RateLimiter(cfg.min_reply_interval)
        self.wx = WeChat()

    def _is_friend_text(self, msg) -> bool:
        if isinstance(msg, FriendTextMessage):
            return True
        if isinstance(msg, FriendMessage) and getattr(msg, "type", "").lower().find("text") >= 0:
            return True
        return False

    def _extract_text(self, msg) -> Optional[str]:
        if hasattr(msg, "content"):
            return str(msg.content)
        if hasattr(msg, "get_all_text"):
            return str(msg.get_all_text())
        return None

    def handle_message(self, msg, chat):
        if not self._is_friend_text(msg):
            return
        text = self._extract_text(msg)
        if not text:
            return

        print(f"[info] 收到消息：{text}")
        reply = self.client.chat(text)
        if reply is None:
            reply = self.cfg.failure_reply
        self.limiter.wait()
        result = chat.SendMsg(reply)
        print(f"[info] 已回复：{reply}，状态：{result}")

    def run(self):
        nickname = self.cfg.friend_nickname
        print(f"[info] 监听联系人：{nickname}")
        add_res = self.wx.AddListenChat(nickname, self.handle_message)
        print(f"[info] AddListenChat 结果：{add_res}")
        self.wx.StartListening()
        print("[info] 开始监听（Ctrl+C 退出）")
        try:
            self.wx.KeepRunning()
        except KeyboardInterrupt:
            print("[info] 已退出")


def main():
    cfg = load_config()
    bot = Bot(cfg)
    bot.run()


if __name__ == "__main__":
    main()
