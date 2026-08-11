"""Combines the cleaned output files from every conference into one file."""

import os
import pandas as pd

CONFERENCES = ["existing", "acl", "eacl", "emnlp", "naacl", "conll", "findings"]

OUT_DIR   = "output/combined"
OUT_EXCEL = os.path.join(OUT_DIR, "all_papers.xlsx")
OUT_CSV   = os.path.join(OUT_DIR, "all_papers.csv")


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    frames = []
    for conf in CONFERENCES:
        path = os.path.join("output", conf, "cleaned_papers.xlsx")
        if os.path.exists(path):
            df = pd.read_excel(path)
            frames.append(df)
            print(f"  [{conf:10s}]  {len(df):5d} papers loaded.")
        else:
            print(f"  [{conf:10s}]  SKIPPED (file not found: {path})")

    if not frames:
        print("\nNo files to merge. Run clean_data.py first.")
        return

    combined = pd.concat(frames, ignore_index=True)

    # Remove duplicate papers by title (keep first occurrence)
    before = len(combined)
    combined.drop_duplicates(subset=["title"], keep="first", inplace=True)
    combined.reset_index(drop=True, inplace=True)
    after = len(combined)

    combined.to_excel(OUT_EXCEL, index=False)
    combined.to_csv(OUT_CSV,    index=False)

    print(f"\nTotal: {before} rows | Duplicates removed: {before - after} | Final: {after} papers")
    print(f"Saved -> {OUT_EXCEL}")


if __name__ == "__main__":
    main()
