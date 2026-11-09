import io
import unittest
from contextlib import redirect_stdout
from datetime import date
from unittest.mock import Mock

from core.agent import MailAgent
from models.email import Email
from models.report import DailySummary
from models.results import EmailAnalysis


class PriorityTests(unittest.TestCase):
    def test_results_sorted_stably_and_failure_kept_separate(self):
        agent = MailAgent.__new__(MailAgent)
        agent.email_service = Mock()
        agent.llm = Mock()
        agent.report_service = Mock()
        subjects = ['low', 'high-first', 'unknown', 'failed', 'medium', 'high-second']
        emails = [Email(subject, 'sender', 'body') for subject in subjects]
        agent.email_service.fetch_recent.return_value = emails
        agent.llm.analyze.side_effect = [
            EmailAnalysis('test', '低', 'summary'),
            EmailAnalysis('test', '高', 'summary'),
            EmailAnalysis('test', '未知', 'summary'),
            RuntimeError('test failure'),
            EmailAnalysis('test', '中', 'summary'),
            EmailAnalysis('test', '高', 'summary'),
        ]
        agent.report_service.build_daily_summary.return_value = DailySummary(date.today(), 6, [], [])
        output = io.StringIO()
        with redirect_stdout(output):
            agent.run(days=7)
        titles = [line for line in output.getvalue().splitlines() if line.startswith('标题:')]
        self.assertEqual(titles, ['标题: high-first', '标题: high-second', '标题: medium',
                                  '标题: low', '标题: unknown', '标题: failed'])
        self.assertIn('进度: 6/6', output.getvalue())
        self.assertIn('分析失败: RuntimeError: test failure', output.getvalue())
        agent.report_service.build_daily_summary.assert_called_once_with(emails, days=7)
