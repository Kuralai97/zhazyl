"""12-ЗЖ: хабарламаларды жіктеу — AI-сыз ереже мен LLM-ді eval жиынтығында өлшеу.

Іске қосу (Ollama іске қосылған болуы керек, bash scripts/ai_setup.sh):
    python scripts/ai_eval.py
Нәтиже: evals/runs/*.jsonl (шикі жауаптар), evals/results.md (метрикалар).
"""
import json
import time
from datetime import datetime
from pathlib import Path

import requests
from sklearn.metrics import accuracy_score, confusion_matrix, f1_score

MODEL = "qwen2.5:3b"
OLLAMA = "http://localhost:11434"
OPTIONS = {"temperature": 0, "seed": 42}
LABELS = ["жазылу", "ауыстыру", "бас тарту", "сұрақ", "басқа"]
ROOT = Path(__file__).resolve().parent.parent
RUNS = ROOT / "evals" / "runs"
RUNS.mkdir(parents=True, exist_ok=True)

DATA = [json.loads(s) for s in open(ROOT / "evals" / "dataset.jsonl", encoding="utf-8")]
TRUE = [x["label"] for x in DATA]

# ---------- 1. AI-сыз базалық шешім: кілт сөздер ережелері ----------
RULES = [  # ретімен тексеріледі, бірінші сәйкес келгені таңдалады
    ("ауыстыру", ["ауыстыр", "жылжыт", "кейінге", "перенес", "перенос", "давайте на"]),
    ("бас тарту", ["бас тарт", "алып таст", "жойыңыз", "келмеймін", "келе алмаймын", "отмен", "не смогу"]),
    ("жазылу", ["жазыл", "запис", "бос орын", "бос па", "окна", "окно", "келсек"]),
    ("сұрақ", ["қанша", "баға", "стоит", "цена", "мекенжай", "адрес", "қай жерде", "жұмыс істей",
               "нешеге", "картой", "оплат", "?"]),
    ("басқа", ["рахмет", "рақмет", "спасибо"]),
]


def rules(text):
    t = text.lower()
    for label, words in RULES:
        if any(w in t for w in words):
            return label
    return "басқа"


# ---------- 2. LLM промпттары ----------
DEFS = """Сен — барбершопқа WhatsApp-қа келген хабарламаны бір топқа жатқызатын көмекшісің.
Топтар:
- жазылу: адам жаңадан жазылғысы келеді
- ауыстыру: бұрынғы жазылудың күнін не уақытын өзгерткісі келеді
- бас тарту: бұрынғы жазылудан бас тартады, келмейді
- сұрақ: баға, мекенжай, жұмыс уақыты, төлем, ережелер туралы сұрайды
- басқа: алғыс, шағым, басқа тақырып
Екі сұраныс болса, басты ниетті таңда. Тек топтың атауын жаз, басқа ештеңе жазба."""

ZERO = DEFS + "\n\nХабарлама: {text}\nТоп:"

# Мысалдар eval жиынтығына кірмейді
SHOTS = [
    ("Бейсенбіге кешкі уақытқа жазып қойыңызшы", "жазылу"),
    ("Можно сдвинуть мою запись на час позже?", "ауыстыру"),
    ("Ертеңгі жазылуды тоқтатыңыз, жоспар өзгерді", "бас тарту"),
    ("Сақал түзету неше минут алады?", "сұрақ"),
    ("Вчера очень понравилось, спасибо мастеру", "басқа"),
    ("Сенбіде келе алмаймын, жексенбіден кейінгі күнге қойсаңыз", "ауыстыру"),
]
FEW = DEFS + "\n\nМысалдар:\n" + "\n".join(f"Хабарлама: {t}\nТоп: {lb}" for t, lb in SHOTS) + \
    "\n\nХабарлама: {text}\nТоп:"


def parse(raw):
    r = raw.lower()
    hits = [(r.find(lb), lb) for lb in LABELS if lb in r]
    return min(hits)[1] if hits else "жарамсыз"


def ask(prompt):
    t0 = time.time()
    r = requests.post(f"{OLLAMA}/api/generate", timeout=300, json={
        "model": MODEL, "prompt": prompt, "stream": False, "options": OPTIONS})
    r.raise_for_status()
    return r.json()["response"].strip(), time.time() - t0


def run(name, template):
    out, preds, secs = [], [], []
    for x in DATA:
        raw, s = ask(template.format(text=x["text"]))
        p = parse(raw)
        preds.append(p)
        secs.append(s)
        out.append({"id": x["id"], "text": x["text"], "label": x["label"], "raw": raw, "pred": p, "sec": round(s, 2)})
        print(f"{name} {x['id']:>2}: {p:<10} ← {raw[:40]!r}")
    with open(RUNS / f"{name}.jsonl", "w", encoding="utf-8") as f:
        for o in out:
            f.write(json.dumps(o, ensure_ascii=False) + "\n")
    return preds, sum(secs) / len(secs)


def metrics(pred, idx=None):
    idx = idx if idx is not None else range(len(DATA))
    t = [TRUE[i] for i in idx]
    p = [pred[i] for i in idx]
    return {
        "acc": accuracy_score(t, p),
        "f1": f1_score(t, p, labels=LABELS, average="macro", zero_division=0),
        "per": f1_score(t, p, labels=LABELS, average=None, zero_division=0),
    }


if __name__ == "__main__":
    tags = requests.get(f"{OLLAMA}/api/tags", timeout=30).json()["models"]
    digest = next((m["digest"][:12] for m in tags if m["name"] == MODEL), "?")
    version = requests.get(f"{OLLAMA}/api/version", timeout=30).json().get("version", "?")
    started = datetime.now().strftime("%Y-%m-%d %H:%M")

    base = [rules(x["text"]) for x in DATA]
    with open(RUNS / "rules.jsonl", "w", encoding="utf-8") as f:
        for x, p in zip(DATA, base):
            f.write(json.dumps({"id": x["id"], "text": x["text"], "label": x["label"], "pred": p},
                               ensure_ascii=False) + "\n")
    zero, zsec = run("zero_shot", ZERO)
    few, fsec = run("few_shot", FEW)

    # Бас тарту ережесі: екі промпт келіспесе — «белгісіз», өріс бос қалады
    final = [f if (f == z and f in LABELS) else "белгісіз" for f, z in zip(few, zero)]
    answered = [i for i, p in enumerate(final) if p != "белгісіз"]

    hard = [i for i, x in enumerate(DATA) if x["hard"]]
    rows = [("AI-сыз ережелер", base), ("Zero-shot", zero), ("Few-shot", few)]
    md = ["# 12-ЗЖ: eval нәтижелері", "",
          f"- Модель: {MODEL} (digest {digest}), Ollama {version}",
          f"- Параметрлер: temperature={OPTIONS['temperature']}, seed={OPTIONS['seed']}",
          f"- Іске қосылған уақыты: {started}",
          f"- Мысалдар: {len(DATA)} (оның қиыны {len(hard)})",
          f"- Орташа жауап уақыты: zero-shot {zsec:.1f} с, few-shot {fsec:.1f} с", "",
          "## Жалпы метрикалар", "",
          "| Тәсіл | Accuracy | Macro F1 | Қиын мысалдарда accuracy |", "|---|---|---|---|"]
    for name, p in rows:
        m, mh = metrics(p), metrics(p, hard)
        md.append(f"| {name} | {m['acc']:.3f} | {m['f1']:.3f} | {mh['acc']:.3f} |")
    md += ["", "## Әр топ бойынша F1", "", "| Тәсіл | " + " | ".join(LABELS) + " |",
           "|---|" + "---|" * len(LABELS)]
    for name, p in rows:
        md.append(f"| {name} | " + " | ".join(f"{v:.2f}" for v in metrics(p)["per"]) + " |")
    wrong_few = sum(1 for i in range(len(DATA)) if few[i] != TRUE[i])
    wrong_final = sum(1 for i in answered if final[i] != TRUE[i])
    md += ["", "## Бас тарту ережесі (zero-shot пен few-shot келіспесе — «белгісіз»)", "",
           f"- Жауап берілгені: {len(answered)} / {len(DATA)} ({len(answered) / len(DATA):.0%})",
           f"- Жауап берілгендердің ішінде дұрысы: "
           f"{sum(1 for i in answered if final[i] == TRUE[i])} / {len(answered)}",
           f"- Қате ұсыныс саны: few-shot жалғыз — {wrong_few}, ережемен — {wrong_final}", "",
           "## Few-shot қателері", "", "| № | Хабарлама | Эталон | Модель | Шикі жауап |", "|---|---|---|---|---|"]
    fs = [json.loads(s) for s in open(RUNS / "few_shot.jsonl", encoding="utf-8")]
    for o in fs:
        if o["pred"] != o["label"]:
            md.append(f"| {o['id']} | {o['text']} | {o['label']} | {o['pred']} | {o['raw'][:40]} |")
    md += ["", "## Few-shot шатасу матрицасы (жол — эталон, баған — модель)", "",
           "| | " + " | ".join(LABELS) + " |", "|---|" + "---|" * len(LABELS)]
    cm = confusion_matrix(TRUE, few, labels=LABELS)
    for lb, r in zip(LABELS, cm):
        md.append(f"| {lb} | " + " | ".join(str(v) for v in r) + " |")
    (ROOT / "evals" / "results.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print("\n".join(md))
