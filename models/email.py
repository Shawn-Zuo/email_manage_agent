from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Email:
    """
    领域模型：一封邮件的核心信息。
    """

    subject: str
    sender: str
    body: str
    received_at: Optional[datetime] = None
    uid: Optional[int] = None