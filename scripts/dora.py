"""DORA-ның төрт метрикасы — репозиторийдің өз тарихынан (10-ЗЖ).

Анықтамалар: docs/ops/dora-anyqtamalar.md
- Орналастыру: main бұтағындағы CI-дың сәтті өтуі (артефакт жарияланады).
- Сәтсіз өзгеріс: орналастырудан кейін 24 сағат ішінде түзету не кері қайтару
  керек болған өзгеріс. Олар docs/ops/incidents.csv журналына қолмен жазылады.
- Қалпына келтіру уақыты: журналдағы «Басталды» мен «Қалпына келді» арасы.

Іске қосу: GitHub Actions → DORA → Run workflow. Токен кодта жоқ,
ол репозиторий секретінде (GH_TOKEN) тұрады.
"""
import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402
import requests  # noqa: E402

REPO = os.environ.get("GITHUB_REPOSITORY", "Kuralai97/zhazyl")
API = f"https://api.github.com/repos/{REPO}"
H = {"Accept": "application/vnd.github+json"}
if os.environ.get("GH_TOKEN"):
    H["Authorization"] = f"Bearer {os.environ['GH_TOKEN']}"
OUT = Path("dora-out")
OUT.mkdir(exist_ok=True)


def get(url, **params):
    r = requests.get(url, headers=H, params=params, timeout=30)
    r.raise_for_status()
    return r.json()


def all_runs():
    runs, page = [], 1
    while True:
        data = get(f"{API}/actions/workflows/ci.yml/runs", branch="main", per_page=100, page=page)
        runs += data["workflow_runs"]
        if len(data["workflow_runs"]) < 100:
            return runs
        page += 1


def first_commit_time(run):
    """Өзгеріс басталған уақыт: PR болса — оның бірінші коммиті, болмаса — коммиттің өзі."""
    pulls = get(f"{API}/commits/{run['head_sha']}/pulls")
    if pulls:
        commits = get(f"{API}/pulls/{pulls[0]['number']}/commits", per_page=100)
        return min(pd.Timestamp(c["commit"]["committer"]["date"]) for c in commits), pulls[0]["number"]
    return pd.Timestamp(run["head_commit"]["timestamp"]), None


runs = [r for r in all_runs() if r["event"] == "push"]
rows = []
for r in runs:
    started, pr = first_commit_time(r) if r["conclusion"] == "success" else (pd.NaT, None)
    rows.append({
        "sha": r["head_sha"][:7],
        "Хабарлама": r["head_commit"]["message"].splitlines()[0][:60],
        "Нәтиже": r["conclusion"],
        "Коммит": started,
        "Аяқталды": pd.Timestamp(r["updated_at"]),
        "PR": pr,
    })
df = pd.DataFrame(rows).sort_values("Аяқталды")
dep = df[df["Нәтиже"] == "success"].copy()
dep["Lead time, сағ"] = (dep["Аяқталды"] - dep["Коммит"]).dt.total_seconds() / 3600

inc = pd.read_csv("docs/ops/incidents.csv")
for c in ["Басталды", "Қалпына келді"]:
    inc[c] = pd.to_datetime(inc[c])

# 1. Орналастыру жиілігі
days = max((dep["Аяқталды"].max() - dep["Аяқталды"].min()).total_seconds() / 86400, 1) if len(dep) else 1
per_week = len(dep) / days * 7
# 2. Коммиттен орналастыруға дейінгі уақыт
lead_med = dep["Lead time, сағ"].median()
# 3. Сәтсіз өзгерістер үлесі
failed = dep["sha"].isin(inc["Қай коммит (sha)"].astype(str).str[:7]).sum()
cfr = 100 * failed / len(dep) if len(dep) else float("nan")
# 4. Қалпына келтіру уақыты
mttr = ((inc["Қалпына келді"] - inc["Басталды"]).dt.total_seconds() / 3600).median() if len(inc) else None


def level_freq(w):
    return "Elite" if w >= 7 else "High" if w >= 1 else "Medium" if w >= 0.25 else "Low"


def level_lead(h):
    return "Elite" if h < 24 else "High" if h < 24 * 7 else "Medium" if h < 24 * 30 else "Low"


def level_cfr(p):
    return "Elite" if p <= 5 else "High" if p <= 10 else "Medium" if p <= 15 else "Low"


def level_mttr(h):
    return "Elite" if h < 1 else "High" if h < 24 else "Medium" if h < 24 * 7 else "Low"


summary = pd.DataFrame([
    ["Орналастыру жиілігі", f"{len(dep)} орналастыру / {days:.1f} күн = {per_week:.1f} аптасына", level_freq(per_week)],
    ["Коммиттен орналастыруға дейін (медиана)", f"{lead_med:.2f} сағ", level_lead(lead_med)],
    ["Сәтсіз өзгерістер үлесі", f"{failed} / {len(dep)} = {cfr:.0f} %", level_cfr(cfr)],
    ["Қалпына келтіру уақыты (медиана)",
     "оқиға болған жоқ" if mttr is None else f"{mttr:.2f} сағ",
     "—" if mttr is None else level_mttr(mttr)],
], columns=["Метрика", "Мәні", "Деңгей"])

df.to_csv(OUT / "ci-runs.csv", index=False)
summary.to_csv(OUT / "dora-summary.csv", index=False)

fig, ax = plt.subplots(2, 2, figsize=(11, 7))
d = dep.set_index("Аяқталды").resample("D").size()
ax[0, 0].bar(d.index.strftime("%d.%m"), d.values, color="#2e9e5b")
ax[0, 0].set_title(f"Орналастыру жиілігі: {per_week:.1f} аптасына")
ax[0, 1].bar(dep["sha"], dep["Lead time, сағ"], color="#5b8def")
ax[0, 1].set_title(f"Коммиттен орналастыруға дейін, сағ (медиана {lead_med:.2f})")
ax[0, 1].tick_params(axis="x", rotation=45)
ax[1, 0].bar(["Сәтті", "Сәтсіз"], [len(dep) - failed, failed], color=["#2e9e5b", "#d9534f"])
ax[1, 0].set_title(f"Сәтсіз өзгерістер үлесі: {cfr:.0f} %")
ax[1, 1].axis("off")
ax[1, 1].text(0.5, 0.6, "Қалпына келтіру уақыты", ha="center", fontsize=13)
ax[1, 1].text(0.5, 0.35, "оқиға болған жоқ" if mttr is None else f"{mttr:.2f} сағ", ha="center", fontsize=18)
fig.suptitle(f"DORA дашборды — {REPO} (CI: {len(df)} іске қосу main-де)")
plt.tight_layout()
plt.savefig(OUT / "dora.png", dpi=150)

md = "## DORA метрикалары\n\n| Метрика | Мәні | Деңгей |\n|---|---|---|\n"
md += "".join(f"| {a} | {b} | {c} |\n" for a, b, c in summary.values)
md += "\n### main-дегі CI іске қосулары\n\n"
md += "| sha | Хабарлама | Нәтиже | Коммит | Аяқталды | Lead time, сағ |\n|---|---|---|---|---|---|\n"
for _, r in df.merge(dep[["sha", "Lead time, сағ"]], on="sha", how="left").iterrows():
    lt = "" if pd.isna(r["Lead time, сағ"]) else f"{r['Lead time, сағ']:.2f}"
    md += f"| {r['sha']} | {r['Хабарлама']} | {r['Нәтиже']} | {r['Коммит']} | {r['Аяқталды']} | {lt} |\n"
(OUT / "dora.md").write_text(md, encoding="utf-8")
if os.environ.get("GITHUB_STEP_SUMMARY"):
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
        f.write(md)
print(md)
