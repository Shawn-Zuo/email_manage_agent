from dataclasses import dataclass
from datetime import date
from typing import List, Optional


@dataclass
class SenderSummary:
    sender: str
    count: int


@dataclass
class TodoItem:
    description: str
    due_time: Optional[str] = None
    related_senders: Optional[List[str]] = None


@dataclass
class DailySummary:
    date: date
    total_emails: int
    sender_summaries: List[SenderSummary]
    todos: List[TodoItem]

