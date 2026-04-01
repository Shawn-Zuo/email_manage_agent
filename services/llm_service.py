import json
import os
from typing import Iterable, List

from dotenv import load_dotenv
from openai import OpenAI

from models.email import Email
from models.report import TodoItem
from models.results import EmailAnalysis

load_dotenv()


class LLMService:
    """
    负责与大模型交互的应用服务。

    - analyze: 对单封邮件做分类 / 优先级 / 总结
    - extract_todos: 针对多封邮件抽取含时间点的待办事项
    """

    def __init__(self) -> None:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY 未配置，请在 .env 或环境变量中设置。")

        self.client = OpenAI(api_key=api_key)
        # 模型名称通过环境变量可配置，便于以后切换模型
        self.model = os.getenv("MODEL", "deepseek-chat")

    def analyze(self, email_obj: Email) -> EmailAnalysis:
        """
        对单封邮件进行结构化分析。
        """
        system_prompt = (
            "你是一个邮件助理，需要帮用户对单封邮件进行分类、优先级评估并生成简短总结。"
            "请返回 JSON 格式，字段为：category（字符串）、priority（高/中/低）、summary（字符串）。"
        )

        user_prompt = (
            f"邮件主题: {email_obj.subject}\n"
            f"发件人: {email_obj.sender}\n"
            f"正文:\n{email_obj.body}\n\n"
            "请分析这封邮件。"
        )

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )

        content = completion.choices[0].message.content or "{}"

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            # 如果模型没有按 JSON 返回，则做一次简单的降级处理
            return EmailAnalysis(
                category="未分类",
                priority="中",
                summary=content.strip()[:200],
            )

        return EmailAnalysis(
            category=str(data.get("category", "未分类")),
            priority=str(data.get("priority", "中")),
            summary=str(data.get("summary", "")),
        )

    def extract_todos(self, emails: Iterable[Email]) -> List[TodoItem]:
        """
        从多封邮件中抽取所有“含有具体时间点”的待办事项。
        """
        emails_list = list(emails)
        if not emails_list:
            return []

        system_prompt = (
            "你是一个时间与任务抽取助手。"
            "用户会给你一天内的多封邮件，请你找出所有包含【具体时间点】的安排，"
            "例如开会、电话、截止日期等，并统一整理成待办事项列表。"
            "只返回 JSON 数组，每个元素包含字段："
            "description（任务描述，字符串），"
            "due_time（尽量从邮件中提取的时间点，如 '今天 15:00' 或 '2026-03-30 18:00'，如果无法确定则为 null），"
            "related_senders（相关发件人列表，字符串数组）。"
        )

        # 为了控制 token，传入精简的文本视图
        lines = []
        for idx, e in enumerate(emails_list, start=1):
            lines.append(f"邮件 {idx}:")
            lines.append(f"  主题: {e.subject}")
            lines.append(f"  发件人: {e.sender}")
            lines.append(f"  正文: {e.body}")
            lines.append("")

        user_prompt = "\n".join(lines)

        completion = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )

        content = completion.choices[0].message.content or "[]"

        try:
            raw_list = json.loads(content)
        except json.JSONDecodeError:
            return []

        todos: List[TodoItem] = []
        if isinstance(raw_list, list):
            for item in raw_list:
                if not isinstance(item, dict):
                    continue
                todos.append(
                    TodoItem(
                        description=str(item.get("description", "")).strip(),
                        due_time=item.get("due_time"),
                        related_senders=item.get("related_senders") or None,
                    )
                )

        return todos

