from imapclient import IMAPClient
import os
from typing import Iterable

from dotenv import load_dotenv

load_dotenv()


class EmailActions:
    """
    对邮件执行具体动作（标记已读、移动到垃圾箱等）。

    IMAP 配置同样来自环境变量，从而支持不同邮箱服务商。
    """

    def __init__(self) -> None:
        self.user = os.getenv("EMAIL_USER")
        self.password = os.getenv("EMAIL_PASS")
        self.host = os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
        self.port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
        self.ssl = os.getenv("EMAIL_IMAP_SSL", "true").lower() == "true"

    def _with_client(self) -> IMAPClient:
        if not self.user or not self.password:
            raise RuntimeError("EMAIL_USER / EMAIL_PASS 未配置，请在 .env 或环境变量中设置。")
        client = IMAPClient(self.host, port=self.port, ssl=self.ssl)
        client.login(self.user, self.password)
        client.select_folder("INBOX")
        return client

    def mark_as_read(self, msg_ids: Iterable[int]) -> None:
        with self._with_client() as client:
            client.add_flags(list(msg_ids), ["\\Seen"])

    def move_to_trash(self, msg_ids: Iterable[int]) -> None:
        """
        注意：不同服务商的垃圾箱文件夹路径可能不同：
        - Gmail: '[Gmail]/Trash'
        - 网易邮箱等：通常为 'Trash' 或 '已删除'
        因此目标文件夹也通过环境变量允许覆盖。
        """
        trash_folder = os.getenv("EMAIL_TRASH_FOLDER", "[Gmail]/Trash")
        with self._with_client() as client:
            client.move(list(msg_ids), trash_folder)