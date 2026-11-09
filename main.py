import argparse

from core.agent import MailAgent


def main():
    parser = argparse.ArgumentParser(description="邮件智能分析与待办提取")
    parser.add_argument("--limit", type=int, help="仅分析当天最新的 N 封邮件（默认处理当天全部邮件）")
    args = parser.parse_args()
    if args.limit is not None and args.limit < 1:
        parser.error("--limit 必须大于 0")
    agent = MailAgent()
    agent.run(limit=args.limit)

if __name__ == "__main__":
    main()
