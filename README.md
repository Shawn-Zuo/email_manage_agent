# Email Manage Agent

基于 IMAP 和 DeepSeek 的命令行邮件助手。默认分析上海时区当天收到的全部邮件，包含已读和未读邮件。

## 运行

需要 Python 3.13+，在项目根目录执行：

```bash
uv sync --locked
uv run python -u main.py

# 仅处理当天最新的 5 封邮件（结果为部分汇总）
uv run python -u main.py --limit 5
```

程序按邮件输出分类、优先级和摘要，然后输出当天邮件数量、发件人统计及含时间的待办。没有当天邮件时直接结束，不调用模型。

## 配置

在 `.env` 中设置（不要提交凭据）：

```env
EMAIL_USER=your_email_address
EMAIL_PASS=your_app_password
EMAIL_IMAP_HOST=imap.gmail.com
EMAIL_IMAP_PORT=993
EMAIL_IMAP_SSL=true
EMAIL_TIMEZONE=Asia/Shanghai
DEEPSEEK_API_KEY=your_deepseek_api_key
MODEL=deepseek-chat
OPENAI_BASE_URL=https://api.deepseek.com
```

可选 `EMAIL_FOLDER` 指定分析的邮箱文件夹。默认优先选择 IMAP `\\All`（Gmail 的“所有邮件”，包含已归档邮件），服务商不提供时使用 INBOX。Gmail“所有邮件”不包含垃圾邮件和垃圾箱，也可能包含当天的发件副本；不是遍历所有文件夹。指定文件夹后仅分析该文件夹。

## 实现

- 使用服务器 `INTERNALDATE` 收件时间，而不是发件人可设置的 `Date` 邮件头。
- IMAP 日期搜索先扩大范围，再按指定时区的当天零点至次日零点精确筛选。
- 只读打开文件夹，使用 `BODY.PEEK[]`，保持邮件已读状态。
- 先取日期元数据，再每批下载 20 封正文，避免下载历史邮件。
- 每封邮件独立调用 DeepSeek，一封分析失败会显示错误并继续后续邮件。
- 汇总按当天邮件统计，待办每批 10 封提取；旧邮件不再回退计入日报。
- 正文不再截断为 1000 字符；目前主要读取纯文本，不分析附件，超长邮件或大量正文仍可能触及模型上下文限制。
- `tools/email_actions.py` 提供手动标记已读和移入垃圾箱的工具，主流程没有调用这些操作。

## 测试

```bash
uv run python -m unittest discover -s tests -v
```

测试覆盖日期边界、UTC 到上海时区转换、只读拉取、已归档文件夹选择、日报过滤及待办分批处理。测试使用模拟 IMAP/LLM，不访问真实邮箱或产生模型费用。

## 结构

- `main.py`：CLI 参数。
- `core/agent.py`：邮件分析与输出编排。
- `services/email_service.py`：邮件筛选和解析。
- `services/llm_service.py`：分类、摘要、待办抽取。
- `services/report_service.py`：统计汇总。
- `models/`：邮件与报告数据模型。

## 点击启动的可视化界面

在 Finder 中双击项目根目录的 `启动邮件助手.command`，会打开本机浏览器界面。选择分析范围并点击“开始分析”；可查看实时输出、停止分析，并通过“退出应用”关闭服务。

也可以执行 `uv run python gui.py`。服务仅监听 `127.0.0.1`，使用随机端口和会话令牌；没有外部网页资源。界面不会自动开始分析，结果仅保存在进程内存中。分析时仍通过原有 DeepSeek API 发送邮件内容。

## GitHub 凭据检查（2026-11-09）

已通过 `git fetch origin` 更新远端引用，并检查 Git 跟踪状态、可达历史文件及本地已知凭据的匹配情况。

- 当前 `.env` 未被跟踪且已被忽略。
- 历史提交 `d0e38802` 曾包含 `.env`，并且仍可从 GitHub 远端 `origin/main` 访问。
- 该历史文件包含邮箱授权码和 DeepSeek API Key；历史 API Key 与检查时本地配置相同。
- 已补充忽略 `.env.*`、本地日志和 `local_reports/` 的规则，并添加不含凭据的 `.env.example`。

请先在服务商后台撤销历史 Gmail 授权码并更换 DeepSeek API Key，再更新本地 `.env`。删除当前文件或添加忽略规则不会清除提交历史中的凭据。本次没有改写历史或强制推送。扫描针对本仓库当前可见引用及已知凭据，不能证明不存在其他副本或从未发生访问。

## 分析最近 1–7 天

界面新增“分析天数”选项，可选择当天或最近 2–7 天，默认当天。最近 N 天指包含今天在内的 N 个自然日，按 `EMAIL_TIMEZONE`（默认上海时区）计算，不是滚动的 N×24 小时。

```bash
# 最近七天全部邮件
uv run python -u main.py --days 7

# 最近三天中最新的五封邮件
uv run python -u main.py --days 3 --limit 5
```

界面、命令行和邮件读取入口均限制最多 7 天；汇总及待办覆盖同一日期范围。修改后请退出旧界面并重新双击启动文件。
