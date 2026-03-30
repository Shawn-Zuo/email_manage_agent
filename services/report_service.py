from collections import Counter
from datetime import date
from typing import Iterable, List

from models.email import Email
from models.report import DailySummary, SenderSummary, TodoItem
from services.llm_service import LLMService


class ReportService:
    """
    负责构建“每日邮件总结”，聚合统计逻辑与待办事项抽取逻辑集中在这里，
    便于今后扩展不同类型的报表而不影响核心 Agent。
    """

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self._llm = llm_service or LLMService()

    def build_daily_summary(self, emails: Iterable[Email]) -> DailySummary:
        # 只统计“今天”的邮件
        today = date.today()
        todays_emails: List[Email] = []
        for e in emails:
            if e.received_at and e.received_at.date() == today:
                todays_emails.append(e)

        # 如果没有时间信息，退化为“所有传入邮件”
        if not todays_emails:
            todays_emails = list(emails)

        total = len(todays_emails)
        sender_counter = Counter(e.sender for e in todays_emails)

        sender_summaries = [
            SenderSummary(sender=sender, count=count)
            for sender, count in sorted(
                sender_counter.items(), key=lambda item: item[1], reverse=True
            )
        ]

        todos = self._llm.extract_todos(todays_emails)

        return DailySummary(
            date=today,
            total_emails=total,
            sender_summaries=sender_summaries,
            todos=todos,
        )

