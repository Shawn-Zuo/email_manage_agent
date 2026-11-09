import unittest
from datetime import timedelta, timezone
from unittest.mock import Mock, patch

from config.date_range import date_range
from gui import AnalysisRun
from models.email import Email
from services.email_service import EmailService
from services.report_service import ReportService


class DateRangeTests(unittest.TestCase):
    def test_invalid_days_rejected_before_external_calls(self):
        for days in (0, 8, -1, True, '7', 1.5, None):
            with self.subTest(days=days), patch('gui.subprocess.Popen') as process:
                with self.assertRaises(ValueError):
                    AnalysisRun().start(days=days)
                with self.assertRaises(ValueError):
                    EmailService().fetch_recent(days=days)
                process.assert_not_called()

    def test_seven_day_fetch_boundaries(self):
        start, end = date_range(7)
        times = {1: start - timedelta(seconds=1), 2: start,
                 3: end - timedelta(seconds=1), 4: end}
        with patch('services.email_service.IMAPClient') as factory:
            client = factory.return_value.__enter__.return_value
            client.search.return_value = list(times)
            client.fetch.side_effect = [
                {uid: {b'INTERNALDATE': dt.astimezone(timezone.utc)} for uid, dt in times.items()},
                {uid: {b'BODY[]': b'Subject: Test\r\n\r\nBody'} for uid in (2, 3)},
            ]
            service = EmailService()
            service.user, service.password = 'test', 'test'
            emails = service.fetch_recent(days=7)
            self.assertEqual([e.uid for e in emails], [2, 3])
            self.assertEqual(client.search.call_args.args[0],
                             ['SINCE', start.date() - timedelta(days=1), 'BEFORE', end.date() + timedelta(days=1)])

    def test_seven_day_summary_includes_history_but_not_outside_window(self):
        start, end = date_range(7)
        llm = Mock()
        llm.extract_todos.return_value = []
        times = [start - timedelta(seconds=1), start, end - timedelta(seconds=1), end]
        emails = (Email('Test', 'sender', 'body', dt) for dt in times)
        summary = ReportService(llm).build_daily_summary(emails, days=7)
        self.assertEqual(summary.total_emails, 2)
        self.assertEqual(len(llm.extract_todos.call_args.args[0]), 2)

    def test_gui_passes_days_to_cli(self):
        with patch('gui.subprocess.Popen') as process, patch('gui.threading.Thread'):
            run = AnalysisRun()
            self.assertTrue(run.start(days=7))
            args = process.call_args.args[0]
            self.assertEqual(args[-2:], ['--days', '7'])
