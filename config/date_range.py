"""邮件分析窗口：包含今天在内的最近 1–7 个自然日。"""
import os
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


def validate_days(days: int) -> None:
    if type(days) is not int or not 1 <= days <= 7:
        raise ValueError('分析天数必须为 1–7 的整数')


def date_range(days: int = 1):
    validate_days(days)
    zone = ZoneInfo(os.getenv('EMAIL_TIMEZONE', 'Asia/Shanghai'))
    today = datetime.now(zone).date()
    start = datetime.combine(today - timedelta(days=days - 1), time.min, tzinfo=zone)
    end = datetime.combine(today + timedelta(days=1), time.min, tzinfo=zone)
    return start, end
