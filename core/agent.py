from config.date_range import date_range
from services.email_service import EmailService
from services.llm_service import LLMService
from services.report_service import ReportService


class MailAgent:
    """
    应用入口 Agent：
    - 拉取当天全部邮件
    - 对每封邮件调用 LLM 分析
    - 生成并输出“邮件分析汇总”和待办事项
    """

    def __init__(self) -> None:
        self.email_service = EmailService()
        self.llm = LLMService()
        self.report_service = ReportService(self.llm)

    def run(self, limit: int | None = None, days: int = 1) -> None:
        start, end = date_range(days)
        from datetime import timedelta
        print(f"分析范围：{start.date()} 至 {(end - timedelta(days=1)).date()}（包含今天，共 {days} 天）", flush=True)
        print("正在读取所选范围邮件（包含已读和未读）…", flush=True)
        emails = self.email_service.fetch_recent(days=days, limit=limit)

        if not emails:
            print("📭 所选范围没有邮件")
            return

        print(f"📬 共 {len(emails)} 封邮件\n")

        results = []
        failures = []
        for index, email in enumerate(emails, 1):
            try:
                result = self.llm.analyze(email)
            except Exception as exc:
                failures.append((email, f"{type(exc).__name__}: {exc}"))
            else:
                results.append((email, result))
            print(f"进度: {index}/{len(emails)}", flush=True)

        priority_order = {"高": 0, "中": 1, "低": 2}
        results.sort(key=lambda item: priority_order.get(item[1].priority.strip(), 3))
        print("\n分析结果（优先级：高 → 中 → 低；未知优先级置后）")
        for email, result in results:
            print("=" * 40)
            print(f"标题: {email.subject}")
            print(f"发件人: {email.sender}")
            print(f"分类: {result.category}")
            print(f"优先级: {result.priority}")
            print(f"总结: {result.summary}")
            print()

        if failures:
            print("\n未能完成分析的邮件：")
            for email, error in failures:
                print(f"标题: {email.subject}")
                print(f"分析失败: {error}")

        # 生成并展示“今日邮件总结”
        summary = self.report_service.build_daily_summary(emails, days=days)

        print("#" * 40)
        print(f"📅 邮件分析汇总（{summary.date.isoformat()}）")
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
