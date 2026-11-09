from services.email_service import EmailService
from services.llm_service import LLMService
from services.report_service import ReportService


class MailAgent:
    """
    应用入口 Agent：
    - 拉取当天全部邮件
    - 对每封邮件调用 LLM 分析
    - 生成并输出“每日邮件总结”和待办事项
    """

    def __init__(self) -> None:
        self.email_service = EmailService()
        self.llm = LLMService()
        self.report_service = ReportService(self.llm)

    def run(self, limit: int | None = None) -> None:
        print("正在读取当天邮件（包含已读和未读）…", flush=True)
        emails = self.email_service.fetch_today(limit=limit)

        if not emails:
            print("📭 当天没有邮件")
            return

        print(f"📬 共 {len(emails)} 封当天邮件\n")

        for index, email in enumerate(emails, 1):
            print("=" * 40)
            print(f"进度: {index}/{len(emails)}")
            print(f"标题: {email.subject}")
            print(f"发件人: {email.sender}")

            try:
                result = self.llm.analyze(email)
            except Exception as exc:
                print(f"分析失败: {type(exc).__name__}: {exc}")
                continue

            print(f"分类: {result.category}")
            print(f"优先级: {result.priority}")
            print(f"总结: {result.summary}")
            print()

        # 生成并展示“今日邮件总结”
        summary = self.report_service.build_daily_summary(emails)

        print("#" * 40)
        print(f"📅 每日邮件总结（{summary.date.isoformat()}）")
        if limit is not None:
            print(f"注意：本次最多处理 {limit} 封，仅为部分邮件汇总。")
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
