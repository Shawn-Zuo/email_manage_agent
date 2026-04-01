## 项目简介

`email_manage_agent` 是一个基于 IMAP 与大语言模型的**邮件智能助手**，主要功能包括：

- **多邮箱提供商支持**：通过环境变量配置 IMAP，可支持 Gmail、网易邮箱（163/126）等。
- **未读邮件智能分析**：对每封未读邮件进行分类、优先级评估，并生成简短总结。
- **每日邮件总结**：
  - 统计当天收到的邮件总数。
  - 按发件人聚合展示每个发件人对应的邮件数量。
  - 从邮件正文中抽取包含时间点的事件，生成待办列表（To-do）。

代码采用分层与依赖注入的方式组织，尽量遵循**单一职责原则**与**开闭原则**，方便后续扩展新的邮箱服务商、LLM 提供商或报表类型。

---

## 项目结构

```text
email_manage_agent/
├── core/               # 核心 Agent（业务编排）
│   └── agent.py        # MailAgent：主入口逻辑
├── models/             # 领域模型
│   ├── email.py        # Email：邮件实体（主题、发件人、正文、时间等）
│   ├── results.py      # EmailAnalysis：单封邮件的分析结果
│   └── report.py       # DailySummary / SenderSummary / TodoItem：日报与待办
├── services/           # 应用服务层
│   ├── email_service.py   # EmailService：IMAP 拉取未读邮件
│   ├── llm_service.py     # LLMService：调用大语言模型做分析与待办抽取
│   └── report_service.py  # ReportService：构建每日邮件总结
├── tools/              # 邮件操作工具
│   └── email_actions.py   # EmailActions：标记已读、移动到垃圾箱等
├── config/             # 预留配置目录（当前可按需扩展）
├── main.py             # 程序入口
├── pyproject.toml      # 项目依赖与配置
├── uv.lock             # 依赖锁定文件
└── .env                # 环境变量配置（不建议提交到 Git）
```

---

## 环境准备

### 1. Python 与依赖

本项目基于 **Python 3.13+**：

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

pip install uv              # 如果你打算使用 uv，也可以使用 pip 直接安装依赖
uv sync                     # 或者: pip install -e ".[dev]"（根据你的习惯调整）
```

如果你不打算使用 `uv`，可直接：

```bash
pip install -r <根据 pyproject 生成的 requirements>  # 或使用 `pip install imapclient openai python-dotenv`
```

### 2. 环境变量（.env）

在项目根目录创建 `.env` 文件（**请勿提交到 Git 仓库**），常用配置示例：

```bash
# 邮箱账号
EMAIL_USER="your_name@163.com"
EMAIL_PASS="your_password_or_app_token"

# IMAP 配置 —— 以网易 163 邮箱为例
EMAIL_IMAP_HOST="imap.163.com"
EMAIL_IMAP_PORT="993"
EMAIL_IMAP_SSL="true"

# 垃圾箱文件夹（不同服务商可能不一样）
# Gmail 通常为 "[Gmail]/Trash"
# 网易等可以是 "Trash"、"已删除" 等
EMAIL_TRASH_FOLDER="Trash"

# OpenAI 配置
OPENAI_API_KEY="sk-..."
OPENAI_MODEL="gpt-4.1-mini"  # 可按需替换其他模型
```

若使用 Gmail，可将 `EMAIL_IMAP_HOST` 改为 `imap.gmail.com`，`EMAIL_TRASH_FOLDER` 改为 `[Gmail]/Trash`，其余保持不变。

---

## 运行方式

在虚拟环境已激活、`.env` 已配置好的前提下，在项目根目录执行：

```bash
python main.py
```

执行流程大致如下：

1. `EmailService` 连接 IMAP，拉取所有未读邮件并解析为 `Email` 对象。
2. `MailAgent` 对每封邮件调用 `LLMService.analyze`：  
   - 输出该邮件的 **分类**、**优先级** 与 **简短总结**。
3. 所有邮件处理完毕后，`ReportService` 会基于这些邮件生成 `DailySummary`：  
   - 今日（或传入集合）总邮件数。  
   - 按发件人聚合的统计信息。  
   - 从邮件中抽取的、带有时间点的待办事项列表。
4. 在终端中打印每日总结与待办清单，方便你快速了解当天的邮件情况和关键 todo。

---

## 设计与扩展性说明

- **分层设计**  
  - `core` 只负责流程编排，不关心外部实现细节。  
  - `services` 专注于对外系统（IMAP、LLM）的交互和核心应用逻辑。  
  - `models` 封装领域对象，便于在不同层之间传递。  
  - `tools` 提供对邮件的具体操作（标记已读、移动到垃圾箱等），可以按需集成到 Agent 流程中。

- **开闭原则与可配置性**  
  - 多邮箱支持通过环境变量控制 IMAP 主机、端口、SSL 等参数，而不是写死在代码中。  
  - LLM 模型名称也通过环境变量配置，从而可以独立升级或替换模型。  
  - 如果未来需要接入其他 LLM（如本地模型），可以通过新增/替换 `LLMService` 的实现来完成，而不必修改 `MailAgent`。

- **报表与待办抽取的可扩展性**  
  - 每日总结逻辑集中在 `ReportService` 中，若要新增周报、月报等，只需在该服务中增加新的构建方法。  
  - 待办抽取是通过 `LLMService.extract_todos` 实现的，未来你也可以替换为纯规则引擎或其他 NLP 模块。
