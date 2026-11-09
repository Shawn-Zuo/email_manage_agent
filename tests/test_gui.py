import io
import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from gui import AnalysisRun, make_handler


class GuiTests(unittest.TestCase):
    def test_run_redacts_credentials(self):
        run = AnalysisRun()
        process = Mock()
        process.stdout = io.StringIO('result: private-test-key\n')
        process.wait.return_value = 0
        with patch('dotenv.dotenv_values', return_value={'DEEPSEEK_API_KEY': 'private-test-key'}):
            run._read(process)
        self.assertEqual(run.snapshot()['lines'], ['result: [已隐藏]'])
        self.assertEqual(run.snapshot()['status'], 'done')

    def test_no_parallel_runs_or_invalid_limit(self):
        run = AnalysisRun()
        with self.assertRaises(ValueError):
            run.start(-1)
        with self.assertRaises(ValueError):
            run.start('1; other command')
        run.status = 'running'
        with patch('gui.subprocess.Popen') as process:
            self.assertFalse(run.start())
            process.assert_not_called()

    def test_stop_terminates_active_process(self):
        run = AnalysisRun()
        run.process = Mock()
        run.process.poll.return_value = None
        run.stop()
        run.process.terminate.assert_called_once()

    def test_http_auth_origin_and_start(self):
        run = Mock()
        run.snapshot.return_value = {'status': 'idle', 'lines': [], 'code': None}
        run.start.return_value = True
        server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(run, 'test-token'))
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            with self.assertRaises(HTTPError) as error:
                urlopen(base + '/api/state')
            self.assertEqual(error.exception.code, 403)
            with urlopen(base + '/api/state?token=test-token') as r:
                self.assertEqual(json.load(r)['status'], 'idle')
            req = Request(base + '/api/start?token=test-token', data=b'{"limit":1}',
                          headers={'Origin': base, 'Content-Type': 'application/json'})
            with urlopen(req) as r:
                self.assertTrue(json.load(r)['started'])
            run.start.assert_called_once_with(1, days=1)
            bad = Request(base + '/api/start?token=test-token', data=b'{}',
                          headers={'Origin': 'https://example.com'})
            with self.assertRaises(HTTPError) as error:
                urlopen(bad)
            self.assertEqual(error.exception.code, 403)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()
