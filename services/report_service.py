import os
from collections import Counter
from datetime import datetime
from typing import Iterable
from zoneinfo import ZoneInfo

from models.email import Email
from models.report import DailySummary, SenderSummary
from services.llm_service import LLMService


class ReportService:
    """
    负责构建“每日邮件总结”，聚合统计逻辑与待办事项抽取逻辑集中在这里，
    便于今后扩展不同类型的报表而不影响核心 Agent。
    """

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self._llm = llm_service or LLMService()

    def build_daily_summary(self, emails: Iterable[Email]) -> DailySummary:
        zone = ZoneInfo(os.getenv("EMAIL_TIMEZONE", "Asia/Shanghai"))
        today = datetime.now(zone).date()
        todays_emails = [
            e for e in emails
            if e.received_at is not None
            and (e.received_at.astimezone(zone) if e.received_at.tzinfo
                 else e.received_at.replace(tzinfo=zone)).date() == today
        ]

        total = len(todays_emails)
        sender_counter = Counter(e.sender for e in todays_emails)

        sender_summaries = [
            SenderSummary(sender=sender, count=count)
            for sender, count in sorted(
                sender_counter.items(), key=lambda item: item[1], reverse=True
            )
        ]

        todos = []
        for offset in range(0, len(todays_emails), 10):
            todos.extend(self._llm.extract_todos(todays_emails[offset:offset + 10]))

        return DailySummary(
            date=today,
            total_emails=total,
            sender_summaries=sender_summaries,
            todos=todos,
        )

