"""Why a cascade? Toy data, no API calls, no model downloads.

Run: .venv/bin/python scratch/why_cascade.py
"""

# Six notes. `truth` is what the simulator knows. `local` is what a local
# classifier returned: its pick plus how confident it was (q).
NOTES = [
    ("Checked the upstream flank of g12, ~500 bp before the start.", "upstream", "upstream", 0.98),
    ("Read the gene body of g40; domain looks typical.",             "gene",     "gene",     0.96),
    ("Looked at the downstream flank after g7 ends.",                "downstream","downstream",0.94),
    # harder: implicit notes. the local model gets shaky, and one is wrong.
    ("Scanned what precedes g12 on its strand for anything odd.",    "upstream", "upstream", 0.71),
    ("Glanced past the end of g55 toward the next ORF.",             "downstream","downstream",0.58),
    ("Looked just before the start codon of g3; promoter-like.",     "upstream", "gene",     0.54),
]

CLAUDE_COST = 0.002   # dollars per note, pretend
LOCAL_COST = 0.0      # runs on your laptop


def claude_label(truth):
    """Pretend Claude. Accurate but not free."""
    return truth


def run(tau):
    correct = escalated = 0
    cost = 0.0
    for _note, truth, local_pick, q in NOTES:
        if q >= tau:
            label, cost = local_pick, cost + LOCAL_COST
        else:
            label, cost = claude_label(truth), cost + CLAUDE_COST
            escalated += 1
        correct += label == truth
    return correct / len(NOTES), escalated, cost


print(f"{len(NOTES)} notes. Claude-only would cost ${len(NOTES) * CLAUDE_COST:.3f} "
      f"at 100% accuracy.\n")
print(f"  {'tau':>5} {'accuracy':>9} {'escalated':>10} {'cost':>8}   what happens")
print(f"  {'-'*5} {'-'*9} {'-'*10} {'-'*8}   {'-'*40}")

for tau, comment in [
    (0.00, "accept everything -> free, but keeps the wrong one"),
    (0.60, "escalate the two shakiest -> fixes the error"),
    (0.90, "escalate anything implicit -> safe, pricier"),
    (1.01, "escalate everything = Claude-only"),
]:
    acc, esc, cost = run(tau)
    print(f"  {tau:5.2f} {acc:8.0%} {esc:10d} {cost:8.3f}   {comment}")

print("\nThe cascade bets that high q means probably right.")
print("Check that on this data: the only wrong local pick had q=0.54, the lowest.")
print("So a tau near 0.6 buys full accuracy while paying for only 2 of 6 notes.")
