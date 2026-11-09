"""仅在本机运行的邮件助手界面；结果保存在内存，不写入日志文件。"""
import argparse
import json
import secrets
import subprocess
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from config.date_range import validate_days

ROOT = Path(__file__).resolve().parent


class AnalysisRun:
    def __init__(self):
        self.lock = threading.Lock()
        self.process = None
        self.lines = []
        self.status = 'idle'
        self.code = None

    def start(self, limit=None, days=1):
        validate_days(days)
        with self.lock:
            if self.status == 'running':
                return False
            args = [sys.executable, '-u', str(ROOT / 'main.py'), '--days', str(days)]
            if limit is not None:
                if type(limit) is not int or limit < 1:
                    raise ValueError('邮件数量必须为正整数')
                args.extend(['--limit', str(limit)])
            self.process = subprocess.Popen(args, cwd=ROOT, stdout=subprocess.PIPE,
                                            stderr=subprocess.STDOUT, text=True)
            self.lines, self.status, self.code = [], 'running', None
            threading.Thread(target=self._read, args=(self.process,), daemon=True).start()
            return True

    def _read(self, process):
        from dotenv import dotenv_values
        values = dotenv_values(ROOT / '.env')
        credentials = [v for k, v in values.items() if v and any(x in k.upper() for x in ('PASS', 'KEY', 'TOKEN'))]
        for line in process.stdout:
            for value in credentials:
                line = line.replace(value, '[已隐藏]')
            with self.lock:
                self.lines.append(line.rstrip())
        code = process.wait()
        process.stdout.close()
        with self.lock:
            self.code = code
            self.status = 'done' if code == 0 else 'error'

    def snapshot(self):
        with self.lock:
            return dict(status=self.status, lines=list(self.lines), code=self.code)

    def stop(self):
        with self.lock:
            if self.process and self.process.poll() is None:
                self.process.terminate()


def make_handler(run, token):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def send(self, code, data, content_type='application/json; charset=utf-8'):
            payload = data if isinstance(data, bytes) else json.dumps(data, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(payload)))
            self.send_header('Cache-Control', 'no-store')
            self.send_header('X-Content-Type-Options', 'nosniff')
            self.send_header('Referrer-Policy', 'no-referrer')
            self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; frame-ancestors 'none'; base-uri 'none'")
            self.end_headers()
            self.wfile.write(payload)

        def authorized(self):
            query = parse_qs(urlparse(self.path).query)
            return secrets.compare_digest(query.get('token', [''])[0], token)

        def do_GET(self):
            if not self.authorized():
                return self.send(403, {'error': '请通过本机启动链接打开界面'})
            path = urlparse(self.path).path
            if path == '/':
                return self.send(200, (ROOT / 'ui/index.html').read_bytes(), 'text/html; charset=utf-8')
            if path == '/api/state':
                return self.send(200, run.snapshot())
            return self.send(404, {'error': '不存在'})

        def do_POST(self):
            if not self.authorized():
                return self.send(403, {'error': '无效的会话'})
            origin = self.headers.get('Origin')
            if origin and origin != f'http://127.0.0.1:{self.server.server_port}':
                return self.send(403, {'error': '请求来源无效'})
            path = urlparse(self.path).path
            if path == '/api/start':
                try:
                    length = int(self.headers.get('Content-Length', '0'))
                    if not 0 < length <= 1024:
                        raise ValueError('请求大小无效')
                    body = json.loads(self.rfile.read(length))
                    started = run.start(body.get('limit'), days=body.get('days', 1))
                    return self.send(200 if started else 409, {'started': started})
                except (ValueError, AttributeError) as exc:
                    return self.send(400, {'error': str(exc)})
            if path == '/api/stop':
                run.stop()
                return self.send(200, {'ok': True})
            if path == '/api/quit':
                run.stop()
                self.send(200, {'ok': True})
                threading.Thread(target=self.server.shutdown, daemon=True).start()
                return
            return self.send(404, {'error': '不存在'})
    return Handler


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    token = secrets.token_urlsafe(32)
    run = AnalysisRun()
    server = ThreadingHTTPServer(('127.0.0.1', 0), make_handler(run, token))
    url = f'http://127.0.0.1:{server.server_port}/?token={token}'
    print('邮件助手已启动，仅本机可访问。关闭时请点击界面右上角“退出应用”。', flush=True)
    if args.no_browser:
        print(url, flush=True)
    else:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        run.stop()
        server.server_close()


if __name__ == '__main__':
    main()
