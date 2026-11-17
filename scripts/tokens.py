"""12-ЗЖ: бір сұраныстың ұзындығын токенизатормен өлшеу (tiktoken, o200k_base).
    python scripts/tokens.py
"""
import json
import sys
from pathlib import Path

import tiktoken

sys.path.insert(0, str(Path(__file__).parent))
from ai_eval import DATA, FEW, ZERO  # noqa: E402

enc = tiktoken.get_encoding("o200k_base")
for name, tpl in [("zero-shot", ZERO), ("few-shot", FEW)]:
    n = [len(enc.encode(tpl.format(text=x["text"]))) for x in DATA]
    print(f"{name}: кіріс орташа {sum(n) / len(n):.0f} токен (мин {min(n)}, макс {max(n)})")
out = [len(enc.encode(x["label"])) for x in DATA]
print(f"шығыс (топ атауы): орташа {sum(out) / len(out):.1f} токен")
print(json.dumps({"model_tokenizer": "o200k_base"}))
