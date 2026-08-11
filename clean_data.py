"""Cleans extracted_papers.xlsx for one or all conferences before merging."""

import argparse
import os
import pandas as pd

CONFERENCES = ["acl", "eacl", "emnlp", "naacl", "conll", "findings", "existing"]

REQUIRED_COLUMNS = [
    "title",
    "authors",
    "abstract",
    "introduction",
    "limitations",
    "conclusion",
    "publication_info",
    "references",
    "groq_keywords",
    "groq_novelty",
    "groq_category",
]

RENAME_MAP = {
    "publication_info": "publication",
    "groq_keywords":    "keywords",
    "groq_novelty":     "novelty",
    "groq_category":    "category",
}


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    # Keep only successfully extracted rows
    if "Extraction_Status" in df.columns:
        df = df[df["Extraction_Status"] == "Success"].copy()

    # Add any missing columns as empty strings
    for col in REQUIRED_COLUMNS:
        if col not in df.columns:
            print(f"  WARNING: column '{col}' missing, filling with empty string.")
            df[col] = ""

    df_clean = df[REQUIRED_COLUMNS].rename(columns=RENAME_MAP)
    return df_clean.reset_index(drop=True)


def clean_one(conf: str):
    out_dir   = os.path.join("output", conf)
    in_excel  = os.path.join(out_dir, "extracted_papers.xlsx")
    out_excel = os.path.join(out_dir, "cleaned_papers.xlsx")
    out_csv   = os.path.join(out_dir, "cleaned_papers.csv")

    print(f"\n[{conf.upper()}] Cleaning...")

    if not os.path.exists(in_excel):
        print(f"  Skipped: {in_excel} not found.")
        return

    df       = pd.read_excel(in_excel)
    df_clean = clean_dataframe(df)

    df_clean.to_excel(out_excel, index=False)
    df_clean.to_csv(out_csv,    index=False)
    print(f"  {len(df_clean)} clean rows -> {out_excel}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf", choices=CONFERENCES, default=None,
                        help="Clean one conference. Omit to clean all.")
    args = parser.parse_args()

    if args.conf:
        clean_one(args.conf)
    else:
        for conf in CONFERENCES:
            clean_one(conf)

    print("\nCleaning complete.")


if __name__ == "__main__":
    main()
