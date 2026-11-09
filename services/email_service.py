import email
import email.utils
import os
from datetime import date, datetime, time, timedelta
from email.header import decode_header, make_header
from typing import List
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from imapclient import IMAPClient

from config.date_range import date_range, validate_days
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

    def fetch_today(self, limit: int | None = None) -> List[Email]:
        """按服务器收件时间筛选本地当天邮件，包含已读和未读。"""
        return self.fetch_recent(days=1, limit=limit)

    def fetch_recent(self, days: int = 1, limit: int | None = None) -> List[Email]:
        validate_days(days)
        start, end = date_range(days)
        return self._fetch(limit=limit, day=end.date() - timedelta(days=1),
                           zone=start.tzinfo, days=days)

    def fetch_unread(self, limit: int | None = None) -> List[Email]:
        return self._fetch(limit=limit)

    def _fetch(self, limit: int | None = None, day: date | None = None, zone: ZoneInfo | None = None, days: int = 1) -> List[Email]:
        if limit is not None and limit < 1:
            raise ValueError("limit 必须大于 0")
        if not self.user or not self.password:
            raise RuntimeError("EMAIL_USER / EMAIL_PASS 未配置，请在 .env 或环境变量中设置。")

        with IMAPClient(self.host, port=self.port, ssl=self.ssl, timeout=30) as client:
            client.login(self.user, self.password)
            # 网易在打开文件夹前要求客户端声明身份（RFC 2971）。
            if client.has_capability("ID"):
                client.id_({
                    "name": "email_manage_agent",
                    "version": "0.1.0",
                    "vendor": "email_manage_agent",
                    "support-email": self.user,
                })
            folder = os.getenv("EMAIL_FOLDER")
            if not folder and day:
                # 优先使用提供商的 All Mail，涵盖已归档邮件；不支持时读取收件箱。
                for flags, delimiter, name in client.list_folders():
                    if any((flag.decode() if isinstance(flag, bytes) else flag).lower() == "\\all" for flag in flags):
                        folder = name
                        break
            client.select_folder(folder or "INBOX", readonly=True)

            # IMAP 日期搜索忽略时区，先扩大候选范围，再用 INTERNALDATE 精确筛选。
            criteria = ["SINCE", day - timedelta(days=days), "BEFORE", day + timedelta(days=2)] if day else ["UNSEEN"]
            messages = client.search(criteria)
            received_dates = {}
            if day and messages:
                start = datetime.combine(day - timedelta(days=days - 1), time.min, tzinfo=zone)
                end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=zone)
                metadata = client.fetch(messages, ["INTERNALDATE"])
                for uid, data in metadata.items():
                    received = data.get(b"INTERNALDATE")
                    if received is None:
                        raise RuntimeError(f"邮件 {uid} 缺少收件时间，无法准确筛选所选日期范围邮件")
                    if received.tzinfo is None:
                        received = received.replace(tzinfo=zone)
                    received_dates[uid] = received
                messages = [uid for uid in messages if start <= received_dates[uid] < end]
            if not messages:
                return []
            if limit is not None:
                messages = sorted(messages)[-limit:]

            response = {}
            for offset in range(0, len(messages), 20):
                response.update(client.fetch(messages[offset:offset + 20], ["BODY.PEEK[]"]))

            emails: List[Email] = []

            for uid, data in response.items():
                raw = data.get(b"BODY[]") or data.get("BODY[]")
                if not raw:
                    continue
                msg = email.message_from_bytes(raw)

                subject = str(make_header(decode_header(msg.get("subject", ""))))
                sender = str(make_header(decode_header(msg.get("from", ""))))

                # 解析收件时间，便于后续按“每天”统计
                raw_date = msg.get("date")
                received_at = received_dates.get(uid)
                if raw_date and received_at is None:
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
                                body = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                                break
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")

                emails.append(
                    Email(
                        subject=subject,
                        sender=sender,
                        body=body,
                        received_at=received_at,
                        uid=int(uid) if uid is not None else None,
                    )
                )

            return emails
