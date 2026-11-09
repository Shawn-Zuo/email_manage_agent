#!/bin/zsh
cd -- "${0:A:h}" || exit 1
if [[ -x .venv/bin/python ]]; then
  .venv/bin/python gui.py
elif [[ -x "$HOME/.local/bin/uv" ]]; then
  "$HOME/.local/bin/uv" run python gui.py
elif command -v uv >/dev/null 2>&1; then
  uv run python gui.py
else
  print '未找到项目 Python 环境或 uv，请先安装 uv 并执行 uv sync。'
  read '?按回车关闭…'
  exit 1
fi
