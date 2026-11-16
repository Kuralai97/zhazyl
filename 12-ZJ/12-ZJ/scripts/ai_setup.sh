#!/usr/bin/env bash
# 12-ЗЖ: Codespaces-те Ollama мен qwen2.5:3b моделін дайындау.
#   bash scripts/ai_setup.sh
set -e
cd "$(dirname "$0")/.."
sudo apt-get update -qq && sudo apt-get install -y -qq zstd > /dev/null
command -v ollama > /dev/null || curl -fsSL https://ollama.com/install.sh | sh
pgrep -x ollama > /dev/null || (nohup ollama serve > ollama.log 2>&1 &)
sleep 5
ollama pull qwen2.5:3b
pip install -q requests scikit-learn tiktoken
ollama --version
echo "Дайын. Енді: python scripts/ai_eval.py"
