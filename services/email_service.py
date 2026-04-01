from imapclient import IMAPClient
import email
import email.utils
import os
from typing import List

from dotenv import load_dotenv

from models.email import Email

load_dotenv()


class EmailService:
    """
    负责与 IMAP 服务器交互的应用服务。

    通过环境变量配置 IMAP 参数，从而在不改动代码的前提下支持不同邮箱服务商
    （如 Gmail、网易 163/126 邮箱等），满足开闭原则。
    """

    def __init__(self) -> None:
        self.user = os.getenv("EMAIL_USER")
        self.password = os.getenv("EMAIL_PASS")
        # 通过配置支持多邮箱服务商
        self.host = os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
        self.port = int(os.getenv("EMAIL_IMAP_PORT", "993"))
        self.ssl = os.getenv("EMAIL_IMAP_SSL", "true").lower() == "true"

    def fetch_unread(self) -> List[Email]:
        if not self.user or not self.password:
            raise RuntimeError("EMAIL_USER / EMAIL_PASS 未配置，请在 .env 或环境变量中设置。")

        with IMAPClient(self.host, port=self.port, ssl=self.ssl) as client:
            client.login(self.user, self.password)
            client.select_folder("INBOX")

            messages = client.search(["UNSEEN"])
            if not messages:
                return []

            response = client.fetch(messages, ["RFC822"])

            emails: List[Email] = []

            for uid, data in response.items():
                raw = data.get(b"RFC822") or data.get("RFC822")
                if not raw:
                    continue
                msg = email.message_from_bytes(raw)

                subject = msg.get("subject", "")
                sender = msg.get("from", "")

                # 解析收件时间，便于后续按“每天”统计
                raw_date = msg.get("date")
                received_at = None
                if raw_date:
                    try:
                        received_at = email.utils.parsedate_to_datetime(raw_date)
                    except Exception:
                        received_at = None

                body = ""

                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain":
                            payload = part.get_payload(decode=True)
                            if payload:
                                body = payload.decode(errors="ignore")
                                break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode(errors="ignore")

                emails.append(
                    Email(
                        subject=subject,
                        sender=sender,
                        body=body[:1000],
                        received_at=received_at,
                        uid=int(uid) if uid is not None else None,
                    )
                )

            return emails