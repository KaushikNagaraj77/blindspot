"""Static HTML report: coverage per run, run-to-run divergence, hotspots.

Reads the DuckDB store and the eval rows, computes every number in Python,
and writes a single self-contained HTML file. No JS dependencies.

Usage: python -m act.report.build
"""

import html
import itertools
import json
import statistics
from pathlib import Path

import duckdb

from act.config import DATA, DB_PATH, REGIONS
from act.coverage.metrics import coverage, diff, hotspots
from act.eval.analysis import accuracy_by_bucket, recall_upstream, tau_sweep
from act.genomes.parse import load_loci
from act.labeler.cascade import pick_tau

OUT = Path("report/out/index.html")
TAUS = [0.7, 0.8, 0.9, 0.95]


def gather() -> dict:
    """Every number the report shows. Code computes; the template only formats."""
    loci = load_loci()
    n_loci = len(loci)
    high_value = {lo.locus_id for lo in loci if lo.high_value}

    # The store holds both simulated and real campaigns, over different loci.
    # Report on the real ones alone, so hotspot shares are not diluted by a set
    # of runs that never touched these loci.
    con = duckdb.connect()
    con.execute(f"ATTACH '{DB_PATH}' AS disk (READ_ONLY)")
    runs = [r[0] for r in con.execute(
        "SELECT DISTINCT run_id FROM disk.inspections ORDER BY run_id").fetchall()]
    shown = [r for r in runs if r.startswith("real")] or runs
    con.execute(
        "CREATE TABLE inspections AS SELECT * FROM disk.inspections "
        f"WHERE run_id IN ({','.join('?' * len(shown))})", shown)

    cov = {r: coverage(con, r, n_loci) for r in shown}

    overlaps, per_run = [], []
    for a, b in itertools.combinations(shown, 2):
        d = diff(con, a, b)
        size_a = con.execute(
            "SELECT count(DISTINCT (locus_id, region)) FROM inspections WHERE run_id=?",
            [a]).fetchone()[0]
        shared = size_a - len(d["only_a"])
        overlaps.append(shared / (len(d["only_a"]) + len(d["only_b"]) + shared))
    for r in shown:
        per_run.append(con.execute(
            "SELECT count(DISTINCT (locus_id, region)) FROM inspections WHERE run_id=?",
            [r]).fetchone()[0])
    union = con.execute(
        "SELECT count(DISTINCT (locus_id, region)) FROM inspections WHERE run_id IN "
        f"({','.join('?' * len(shown))})", shown).fetchone()[0]

    hs = hotspots(con, high_value, max_share=0.2)
    n_insp = con.execute(  # only the runs this report charts
        f"SELECT count(*) FROM inspections WHERE run_id IN ({','.join('?' * len(shown))})",
        shown).fetchone()[0]
    con.close()

    data = {
        "n_loci": n_loci, "n_units": n_loci * 3, "runs": shown,
        "coverage": cov, "n_inspections": n_insp,
        "mean_overlap": statistics.mean(overlaps) if overlaps else None,
        "scaling": union / statistics.mean(per_run) if per_run else None,
        "union": union, "mean_per_run": statistics.mean(per_run) if per_run else 0,
        "hotspots": sorted(hs), "n_hotspots": len(hs),
        "n_hv_units": len(high_value) * 3,
        "eval": None,
    }

    rows_path = DATA / "eval_rows.jsonl"
    if rows_path.exists():
        rows = [json.loads(line) for line in rows_path.read_text().splitlines() if line]
        split = len(rows) // 5
        chosen = pick_tau(rows[:split], TAUS)
        data["eval"] = {
            "n": len(rows),
            "raw_accuracy": sum(r["pred"] == r["truth"] for r in rows) / len(rows),
            "sweep": tau_sweep(rows[split:], TAUS),
            "chosen_tau": chosen,
            "at_chosen": tau_sweep(rows[split:], [chosen])[0],
            "buckets": accuracy_by_bucket(rows, [0.0, 0.5, 0.7, 0.9, 1.0]),
            "upstream": recall_upstream(rows),
        }
    return data


# --- rendering ---------------------------------------------------------------

CSS = """
:root {
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb;
  --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --border: rgba(11,11,11,0.10);
  --gene: #2a78d6; --upstream: #eb6834; --downstream: #1baf7a;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19;
    --ink: #ffffff; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --border: rgba(255,255,255,0.10);
    --gene: #3987e5; --upstream: #d95926; --downstream: #199e70;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; padding: 40px 16px 64px; background: var(--page); color: var(--ink);
  font: 15px/1.55 ui-sans-serif, -apple-system, "Segoe UI", system-ui, sans-serif;
}
.wrap { max-width: 880px; margin: 0 auto; }
h1 { font-size: 26px; margin: 0 0 6px; letter-spacing: -0.01em; }
h2 { font-size: 17px; margin: 40px 0 4px; letter-spacing: -0.005em; }
.sub, .note { color: var(--ink-2); font-size: 13.5px; margin: 0 0 18px; }
.note { margin: 10px 0 0; }
.card {
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 10px; padding: 20px; margin-top: 14px;
}
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 12px; }
.kpi { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 16px; }
.kpi .v { font-size: 30px; font-weight: 600; letter-spacing: -0.02em; line-height: 1.1; }
.kpi .l { color: var(--ink-2); font-size: 12.5px; margin-top: 6px; }
table { width: 100%; border-collapse: collapse; font-size: 13.5px; }
th { text-align: left; font-weight: 600; color: var(--ink-2); font-size: 12px;
     text-transform: uppercase; letter-spacing: 0.04em; padding: 0 10px 8px 0; }
td { padding: 7px 10px 7px 0; border-top: 1px solid var(--grid); font-variant-numeric: tabular-nums; }
.num { text-align: right; }
.legend { display: flex; gap: 18px; flex-wrap: wrap; font-size: 13px; color: var(--ink-2); margin-bottom: 14px; }
.swatch { display: inline-block; width: 11px; height: 11px; border-radius: 3px; margin-right: 6px; vertical-align: -1px; }
.bars { display: grid; gap: 14px; }
.row-label { font-size: 13px; color: var(--ink-2); margin-bottom: 5px; font-variant-numeric: tabular-nums; }
.track { display: grid; gap: 2px; }
.bar { height: 13px; border-radius: 0 4px 4px 0; position: relative; }
.bar span { position: absolute; left: calc(100% + 8px); top: -2px; font-size: 11.5px;
            color: var(--ink-2); font-variant-numeric: tabular-nums; white-space: nowrap; }
code { font: 12.5px ui-monospace, SFMono-Regular, Menlo, monospace; color: var(--ink-2); }
footer { margin-top: 48px; color: var(--muted); font-size: 12.5px; }
"""


def bar_group(label: str, cov: dict, scale: float) -> str:
    bars = "".join(
        f'<div class="bar" style="width:{max(cov[r] / scale * 100, 0.6):.2f}%;'
        f'background:var(--{r})"><span>{cov[r]:.2%}</span></div>'
        for r in REGIONS
    )
    return (f'<div><div class="row-label">{html.escape(label)}</div>'
            f'<div class="track">{bars}</div></div>')


def render(d: dict) -> str:
    scale = max(max(c.values()) for c in d["coverage"].values()) * 1.25

    kpis = [
        (f"{d['n_units']:,}", "units in the search space"),
        (f"{d['n_inspections']:,}", "inspections logged"),
        (f"{d['mean_overlap']:.0%}" if d["mean_overlap"] else "-",
         "mean overlap between any two runs"),
        (f"{d['scaling']:.1f}x" if d["scaling"] else "-",
         f"coverage from {len(d['runs'])} runs vs one"),
    ]
    kpi_html = "".join(
        f'<div class="kpi"><div class="v">{v}</div><div class="l">{label}</div></div>'
        for v, label in kpis)

    legend = "".join(
        f'<span><i class="swatch" style="background:var(--{r})"></i>{r}</span>'
        for r in REGIONS)
    bars = "".join(bar_group(r, d["coverage"][r], scale) for r in d["runs"])

    # One row per locus: three rows all reading 0% says less than one row saying
    # "every region of this gene was missed".
    by_locus: dict[str, dict[str, float]] = {}
    for lo, reg, share in d["hotspots"]:
        by_locus.setdefault(lo, {})[reg] = share
    hot_rows = "".join(
        f"<tr><td><code>{html.escape(lo)}</code></td>"
        f'<td>{", ".join(sorted(regs))}</td>'
        f'<td class="num">{max(regs.values()):.0%}</td></tr>'
        for lo, regs in list(by_locus.items())[:12])

    eval_html = "<p class='note'>No eval rows yet. Run <code>python -m act.eval.build_rows</code>.</p>"
    if d["eval"]:
        e = d["eval"]
        sweep = "".join(
            f'<tr><td class="num">{r["tau"]:.2f}</td>'
            f'<td class="num">{r["escalation_rate"]:.1%}</td>'
            f'<td class="num">{r["accuracy"]:.1%}</td>'
            f'<td class="num">{r["cost_vs_claude_only"]:.1%}</td></tr>'
            for r in e["sweep"])
        buckets = "".join(
            f'<tr><td>{"invalid" if b["lo"] is None else f"{b['lo']:.1f} - {b['hi']:.1f}"}</td>'
            f'<td class="num">{b["n"]}</td>'
            f'<td class="num">{"-" if b["accuracy"] is None else f"{b['accuracy']:.1%}"}</td></tr>'
            for b in e["buckets"])
        up = e["upstream"]
        eval_html = f"""
        <div class="card">
          <table>
            <tr><th>tau</th><th class="num">escalated</th><th class="num">accuracy</th>
                <th class="num">cost vs Claude-only</th></tr>
            {sweep}
          </table>
          <p class="note">tau = <strong>{e['chosen_tau']}</strong>, chosen on a 20% selection
          split and reported on the held-out 80%:
          <strong>{e['at_chosen']['accuracy']:.1%}</strong> of Claude-only accuracy at
          <strong>{e['at_chosen']['cost_vs_claude_only']:.0%}</strong> of its cost.
          Raw local-model accuracy with no cascade: {e['raw_accuracy']:.1%}.</p>
        </div>

        <h2>Does confidence predict correctness?</h2>
        <p class="sub">The cascade's load-bearing assumption. If accuracy were flat
        across buckets, thresholding would buy nothing.</p>
        <div class="card">
          <table>
            <tr><th>confidence</th><th class="num">n</th><th class="num">accuracy</th></tr>
            {buckets}
          </table>
        </div>

        <h2>Rebuilding coverage from notes alone</h2>
        <div class="card">
          <p style="margin:0">Of {up['n_truth_upstream']} genuinely upstream inspections,
          the labeller recovered <strong>{up['true_positives']}</strong> from the free-text
          notes: recall <strong>{up['recall']:.1%}</strong> at precision
          <strong>{up['precision']:.1%}</strong>.</p>
        </div>"""

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Campaign Coverage</title>
<style>{CSS}</style></head>
<body><div class="wrap">

<h1>Agent campaign coverage</h1>
<p class="sub">What {len(d['runs'])} reruns of the same search campaign actually
covered, over {d['n_loci']:,} loci from annotated phage genomes.</p>

<div class="kpis">{kpi_html}</div>

<h2>Coverage per run</h2>
<p class="sub">Fraction of loci whose region a run inspected. Runs cover a similar
<em>amount</em>; the overlap figure above shows they cover different <em>things</em>.</p>
<div class="card">
  <div class="legend">{legend}</div>
  <div class="bars">{bars}</div>
</div>

<h2>Cascade labelling</h2>
<p class="sub">Accept the local classifier's label when its confidence clears tau,
otherwise escalate to Claude. Invalid output always escalates.</p>
{eval_html}

<h2>Blind spots</h2>
<p class="sub">{d['n_hotspots']} of {d['n_hv_units']} high-value units
({d['n_hotspots'] / d['n_hv_units']:.0%}) were inspected by under 20% of runs.
The 12 worst-covered loci:</p>
<div class="card">
  <table>
    <tr><th>locus</th><th>regions missed</th><th class="num">best share</th></tr>
    {hot_rows}
  </table>
</div>

<footer>Every number here is computed in Python from the event log.
Generated by <code>act.report.build</code>.</footer>
</div></body></html>"""


def main() -> None:
    data = gather()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(render(data))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
