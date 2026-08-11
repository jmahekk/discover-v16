"""Writes the pipeline's results out to Excel and CSV."""

import pandas as pd
import os

def export_results(rows, out_dir):
    os.makedirs(out_dir, exist_ok=True)

    df = pd.DataFrame(rows)

    csv_path = os.path.join(out_dir, "extracted_papers.csv")
    xlsx_path = os.path.join(out_dir, "extracted_papers.xlsx")

    df.to_csv(csv_path, index=False)
    df.to_excel(xlsx_path, index=False)

    return csv_path, xlsx_path
