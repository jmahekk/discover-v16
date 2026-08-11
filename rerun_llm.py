"""Fills in keywords, novelty and category for rows a rate-limited run skipped."""

import argparse
import os
import pandas as pd
from llm_module import process_llm, generate_limitations

CONFERENCES = ["acl", "eacl", "emnlp", "naacl", "conll", "findings", "existing"]


def needs_llm(row) -> bool:
    """Returns True if this row is missing LLM-generated fields."""
    for col in ["groq_keywords", "groq_novelty", "groq_category"]:
        val = str(row.get(col, "")).strip()
        if not val or val == "nan":
            return True
    return False


def rerun_llm(conf: str):
    out_dir   = os.path.join("output", conf)
    xlsx_path = os.path.join(out_dir, "extracted_papers.xlsx")

    if not os.path.exists(xlsx_path):
        print(f"File not found: {xlsx_path}")
        return

    df = pd.read_excel(xlsx_path)
    df = df.fillna("")

    # Only look at successfully extracted rows
    if "Extraction_Status" in df.columns:
        mask = (df["Extraction_Status"] == "Success") & df.apply(needs_llm, axis=1)
    else:
        mask = df.apply(needs_llm, axis=1)

    to_fix = df[mask]
    total  = len(to_fix)

    if total == 0:
        print(f"[{conf.upper()}] No missing LLM fields found. Nothing to do.")
        return

    print(f"[{conf.upper()}] {total} rows need LLM re-run.\n")

    for i, (idx, row) in enumerate(to_fix.iterrows(), 1):
        print(f"[{i}/{total}] {str(row.get('title', ''))[:80]}")

        data = {
            "title":        row.get("title",        ""),
            "abstract":     row.get("abstract",     ""),
            "introduction": row.get("introduction", ""),
            "conclusion":   row.get("conclusion",   ""),
            "limitations":  row.get("limitations",  ""),
        }

        # Generate limitations too if missing
        if not str(data["limitations"]).strip():
            print("  Limitations missing, generating...")
            try:
                data["limitations"] = generate_limitations(data)
                df.at[idx, "limitations"] = data["limitations"]
            except Exception as e:
                print(f"  Limitation generation failed: {e}")

        try:
            llm_results = process_llm(data)
            df.at[idx, "groq_keywords"] = llm_results["groq_keywords"]
            df.at[idx, "groq_novelty"]  = llm_results["groq_novelty"]
            df.at[idx, "groq_category"] = llm_results["groq_category"]
            print(f"  Done.")
        except Exception as e:
            print(f"  LLM failed: {e}")

        # Save every 50 rows so progress is not lost
        if i % 50 == 0:
            df.to_excel(xlsx_path, index=False)
            df.to_csv(xlsx_path.replace(".xlsx", ".csv"), index=False)
            print(f"  -- Progress saved ({i}/{total}) --")

    # Final save
    df.to_excel(xlsx_path, index=False)
    df.to_csv(xlsx_path.replace(".xlsx", ".csv"), index=False)
    print(f"\n[{conf.upper()}] Done. Saved -> {xlsx_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf", required=True, choices=CONFERENCES,
                        help="Which conference to patch")
    args = parser.parse_args()

    rerun_llm(args.conf)


if __name__ == "__main__":
    main()
