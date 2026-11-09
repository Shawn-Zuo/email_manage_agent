import argparse
import sys

from imapclient.exceptions import LoginError

from core.agent import MailAgent


def main():
    parser = argparse.ArgumentParser(description="邮件智能分析与待办提取")
    parser.add_argument("--limit", type=int, help="仅分析当天最新的 N 封邮件（默认处理当天全部邮件）")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit 必须大于 0")
    agent = MailAgent()
    try:
        agent.run(limit=args.limit)
    except LoginError:
        print(
            "邮箱登录失败：请确认 EMAIL_USER 为完整邮箱地址，EMAIL_PASS 为该邮箱的 "
            "IMAP 客户端授权码（不是网页登录密码），并检查 IMAP 服务已开启。"
            "如仍失败，请重新生成授权码并更新 .env。",
            file=sys.stderr,
        )
        sys.exit(1)

if __name__ == "__main__":
    main()
