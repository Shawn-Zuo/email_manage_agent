import unittest
from datetime import datetime, time, timedelta, timezone
from unittest.mock import Mock, patch
from zoneinfo import ZoneInfo

from models.email import Email
from services.email_service import EmailService
from services.report_service import ReportService


class DailyMailTests(unittest.TestCase):
    def test_day_boundary_and_readonly(self):
        zone = ZoneInfo('Asia/Shanghai')
        today = datetime.now(zone).date()
        start = datetime.combine(today, time.min, tzinfo=zone)
        dates = {1: start - timedelta(seconds=1), 2: start,
                 3: start + timedelta(days=1) - timedelta(seconds=1),
                 4: start + timedelta(days=1)}
        with patch('services.email_service.IMAPClient') as factory:
            client = factory.return_value.__enter__.return_value
            client.search.return_value = list(dates)
            client.fetch.side_effect = [
                {uid: {b'INTERNALDATE': dt.astimezone(timezone.utc)} for uid, dt in dates.items()},
                {uid: {b'BODY[]': b'Subject: Test\r\nDate: Mon, 01 Jan 2001 00:00:00 +0000\r\n\r\nBody'} for uid in (2, 3)},
            ]
            service = EmailService()
            service.user, service.password = 'test', 'test'
            messages = service.fetch_today()
            self.assertEqual([e.uid for e in messages], [2, 3])
            self.assertEqual(messages[0].received_at, start)
            self.assertNotIn('UNSEEN', client.search.call_args.args[0])
            client.select_folder.assert_called_once_with('INBOX', readonly=True)
            self.assertEqual(client.fetch.call_args.args, ([2, 3], ['BODY.PEEK[]']))

    def test_all_mail_folder_includes_archived(self):
        with patch('services.email_service.IMAPClient') as factory:
            client = factory.return_value.__enter__.return_value
            client.list_folders.return_value = [((b'\\All',), b'/', '[Gmail]/All Mail')]
            client.search.return_value = []
            service = EmailService()
            service.user, service.password = 'test', 'test'
            self.assertEqual(service.fetch_today(), [])
            client.select_folder.assert_called_once_with('[Gmail]/All Mail', readonly=True)

    def test_summary_never_falls_back_to_old_mail(self):
        llm = Mock()
        old = Email('Old', 'sender', 'body', datetime.now(ZoneInfo('Asia/Shanghai')) - timedelta(days=2))
        result = ReportService(llm).build_daily_summary(iter([old]))
        self.assertEqual(result.total_emails, 0)
        llm.extract_todos.assert_not_called()

    def test_summary_handles_generator_and_batches_todos(self):
        llm = Mock()
        llm.extract_todos.return_value = []
        now = datetime.now(ZoneInfo('Asia/Shanghai'))
        emails = (Email('Test', 'sender', 'body', now) for _ in range(21))
        summary = ReportService(llm).build_daily_summary(emails)
        self.assertEqual(summary.total_emails, 21)
        self.assertEqual(summary.sender_summaries[0].count, 21)
        self.assertEqual([len(c.args[0]) for c in llm.extract_todos.call_args_list], [10, 10, 1])


if __name__ == '__main__':
    unittest.main()
