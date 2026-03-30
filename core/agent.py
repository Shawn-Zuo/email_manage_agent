from services.email_service import EmailService
from services.llm_service import LLMService
from services.report_service import ReportService


class MailAgent:
    """
    应用入口 Agent：
    - 拉取未读邮件
    - 对每封邮件调用 LLM 分析
    - 生成并输出“每日邮件总结”和待办事项
    """

    def __init__(self) -> None:
        self.email_service = EmailService()
        self.llm = LLMService()
        self.report_service = ReportService(self.llm)

    def run(self) -> None:
        emails = self.email_service.fetch_unread()

        if not emails:
            print("📭 没有未读邮件")
            return

        print(f"📬 共 {len(emails)} 封未读邮件\n")

        for email in emails:
            print("=" * 40)
            print(f"标题: {email.subject}")
            print(f"发件人: {email.sender}")

            result = self.llm.analyze(email)

            print(f"分类: {result.category}")
            print(f"优先级: {result.priority}")
            print(f"总结: {result.summary}")
            print()

        # 生成并展示“今日邮件总结”
        summary = self.report_service.build_daily_summary(emails)

        print("#" * 40)
        print(f"📅 每日邮件总结（{summary.date.isoformat()}）")
        print(f"- 总共邮件数量: {summary.total_emails}")
        print("- 按发件人统计:")
        for sender_summary in summary.sender_summaries:
            print(f"  - {sender_summary.sender}: {sender_summary.count} 封")

        print("\n- 待办事项（含具体时间点）:")
        if not summary.todos:
            print("  暂无自动识别的待办事项。")
        else:
            for idx, todo in enumerate(summary.todos, start=1):
                line = f"  {idx}. {todo.description}"
                if todo.due_time:
                    line += f" （时间: {todo.due_time}）"
                if todo.related_senders:
                    senders = ", ".join(todo.related_senders)
                    line += f" —— 来自: {senders}"
                print(line)