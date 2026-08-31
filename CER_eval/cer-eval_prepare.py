import pandas as pd
import numpy as np

# --- config ---
FILES = {
    "2.5": "data/raw/_transkription_2.5.csv",
    "3_lite": "data/raw/_transkription_3_lite.csv",
    "3": "data/raw/_transkription_3.csv",
    "3_pro": "data/raw/_transkription_3_pro.csv",
}
ID_COL = "Lfd. Nr."   # <-- your ID column
TEXT_COL = "Titel"
SAMPLE_SIZE = 200
SEED = 42
DRAFT_MODEL = "3_pro"   # <-- used to pre-fill gt_title as a starting draft


# --- load ---
dfs = {}
for name, path in FILES.items():
    df = pd.read_csv(path, dtype={ID_COL: str}, delimiter=";")
    df = df[[ID_COL, TEXT_COL]].rename(columns={TEXT_COL: f"{name}_title"})
    dfs[name] = df

# --- sanity checks ---
ids = {name: set(df[ID_COL]) for name, df in dfs.items()}
all_ids = set.union(*ids.values())
common_ids = set.intersection(*ids.values())

print(f"Total distinct IDs across all files: {len(all_ids)}")
print(f"IDs present in ALL 4 files:          {len(common_ids)}")

for name, id_set in ids.items():
    missing = all_ids - id_set
    if missing:
        print(f"  {name}: missing {len(missing)} IDs that appear elsewhere "
              f"(e.g. {list(missing)[:5]})")

for name, df in dfs.items():
    if df[ID_COL].duplicated().any():
        print(f"  WARNING: {name} has {df[ID_COL].duplicated().sum()} duplicate ID(s)")

# --- merge ---
merged = dfs["2.5"]
for name in ["3_lite", "3", "3_pro"]:
    merged = merged.merge(dfs[name], on=ID_COL, how="inner")

print(f"\nRows usable for comparison (present in all 4): {len(merged)}")

if len(merged) < SAMPLE_SIZE:
    raise ValueError(f"Only {len(merged)} rows available, need {SAMPLE_SIZE}")

# --- sample, then sort by Lfd. Nr. ---
sample = merged.sample(n=SAMPLE_SIZE, random_state=SEED).copy()

sample["_sort_key"] = pd.to_numeric(
    sample[ID_COL].str.extract(r"(\d+)")[0], errors="coerce"
)
sample = sample.sort_values("_sort_key").drop(columns="_sort_key").reset_index(drop=True)

# pre-fill gt_title with the draft model's text, to be hand-corrected
sample.insert(1, "gt_title", sample[f"{DRAFT_MODEL}_title"])

sample.to_csv("cer_eval_sample.csv", index=False, sep=";")
print(f"\nWrote {len(sample)} rows to cer_eval_sample.csv, sorted by {ID_COL}")
print(f"gt_title pre-filled from {DRAFT_MODEL} — remember to hand-correct against scans")
print(sample.head(3))