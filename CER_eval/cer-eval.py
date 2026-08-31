import pandas as pd
import numpy as np

try:
    import Levenshtein as lev
except ImportError:
    raise ImportError("Install with: pip install python-Levenshtein")

# --- config ---
INPUT_FILE = "cer_eval_sample_minus.csv"
GT_COL = "gt_title"
MODEL_COLS = ["2.5_title", "3_lite_title", "3_title", "3_pro_title"]
SEP = ";"

# --- load ---
df = pd.read_csv(INPUT_FILE, sep=SEP, dtype=str).fillna("")

# optional: only use rows you've actually hand-corrected, if you added a
# gt_verified column earlier — uncomment if relevant
# df = df[df["gt_verified"] == True]

def normalize(s: str) -> str:
    """Keep this consistent across GT and all model outputs."""
    s = str(s).strip()
    s = " ".join(s.split())       # collapse whitespace
    # add any other normalization rules you decided on, e.g.:
    # s = s.replace("’", "'").replace("“", '"').replace("”", '"')
    return s

df[GT_COL] = df[GT_COL].apply(normalize)
for col in MODEL_COLS:
    df[col] = df[col].apply(normalize)

# --- per-row edit distance + GT length ---
results = {}
for col in MODEL_COLS:
    dists = [lev.distance(gt, hyp) for gt, hyp in zip(df[GT_COL], df[col])]
    gt_lens = [len(gt) for gt in df[GT_COL]]
    df[f"{col}_edit_dist"] = dists
    df[f"{col}_gt_len"] = gt_lens
    df[f"{col}_cer"] = [d / l if l > 0 else 0 for d, l in zip(dists, gt_lens)]
    results[col] = {"edit_dist": np.array(dists), "gt_len": np.array(gt_lens)}

# --- aggregate CER (sum of distances / sum of GT chars, NOT mean of row CERs) ---
print(f"{'Model':<20} {'Aggregate CER':>15} {'Mean row CER':>15} {'Rows':>6}")
print("-" * 60)
for col in MODEL_COLS:
    r = results[col]
    agg_cer = r["edit_dist"].sum() / r["gt_len"].sum()
    mean_cer = df[f"{col}_cer"].mean()
    print(f"{col:<20} {agg_cer:>14.4%} {mean_cer:>14.4%} {len(df):>6}")

# --- save per-row detail for inspection ---
df.to_csv("cer_eval_results_minus.csv", index=False, sep=SEP)
print("\nWrote per-row detail to cer_eval_results.csv")

# --- worst rows per model, useful for spotting systematic errors ---
for col in MODEL_COLS:
    print(f"\nWorst 5 rows for {col}:")
    worst = df.nlargest(5, f"{col}_cer")[["Lfd. Nr.", GT_COL, col, f"{col}_cer"]]
    print(worst.to_string(index=False))