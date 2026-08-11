"""
Main extraction pipeline: downloads each paper, parses it with GROBID,
enriches it with the LLM, and saves progress so an interrupted run can resume.
"""

import argparse
import json
import os
import sys

import pandas as pd

from read_urls    import read_hyperlinks
from downloader   import download_pdf
import extract_core
from extract_core import parse_pdf
from exporter     import export_results
from llm_module   import process_llm, generate_limitations


CONF_INPUT = {
    "acl":      "input/acl_2025_urls.xlsx",
    "eacl":     "input/eacl_2026_urls.xlsx",
    "emnlp":    "input/emnlp_2025_urls.xlsx",
    "naacl":    "input/naacl_2025_urls.xlsx",
    "conll":    "input/conll_2025_urls.xlsx",
    "findings": "input/findings_2026_urls.xlsx",
    "existing": "input/paper_urls.xlsx",
}


def checkpoint_file(out_dir):
    return os.path.join(out_dir, "_checkpoint.json")


def load_checkpoint(out_dir):
    path = checkpoint_file(out_dir)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        data["done"] = set(data["done"])
        print(f"Checkpoint found: {len(data['done'])} papers already processed. Resuming.")
        return data
    return {"done": set(), "results": []}


def save_checkpoint(out_dir, done, results):
    path = checkpoint_file(out_dir)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"done": list(done), "results": results}, f, ensure_ascii=False, indent=2)


def flush_to_excel(results, out_dir):
    df = pd.DataFrame(results)
    df.to_excel(os.path.join(out_dir, "extracted_papers.xlsx"), index=False)
    df.to_csv(os.path.join(out_dir, "extracted_papers.csv"),   index=False)
    print(f"  Flushed {len(results)} rows -> {out_dir}/extracted_papers.xlsx")


def process_one(idx, item, pdf_dir, debug_xml_dir, run_llm=True):
    title = item["title"]
    url   = item["url"]
    print(f"  URL: {url}")

    pdf_path = os.path.join(pdf_dir, f"paper_{idx:04d}.pdf")
    if os.path.exists(pdf_path):
        print("  PDF already exists. Skipping download.")
        dl_error = None
    else:
        pdf_path, dl_error = download_pdf(url, pdf_dir, idx)

    if not pdf_path:
        print(f"  Download failed: {dl_error}")
        return {
            "_idx":              idx,
            "paper_title":       title,
            "url":               url,
            "pdf_path":          "",
            "Extraction_Status": "Download Failed",
            "Failure_Reason":    dl_error,
        }

    try:
        data, tei_xml = parse_pdf(pdf_path)

        if run_llm:
            if not data.get("limitations"):
                print("  Limitations missing, generating with LLM...")
                try:
                    data["limitations"] = generate_limitations(data)
                except Exception as e:
                    print(f"  Limitation generation failed: {e}")

            try:
                data.update(process_llm(data))
            except Exception as e:
                print(f"  LLM failed: {e}")
        else:
            print("  LLM skipped (run rerun_llm.py later to generate keywords/novelty/category).")

        os.makedirs(debug_xml_dir, exist_ok=True)
        with open(os.path.join(debug_xml_dir, f"paper_{idx:04d}.xml"), "w", encoding="utf-8") as f:
            f.write(tei_xml)

        data["_idx"]              = idx
        data["paper_title"]       = title
        data["url"]               = url
        data["pdf_path"]          = pdf_path
        data["Extraction_Status"] = "Success"
        data["Failure_Reason"]    = ""
        print("  Extracted.")
        return data

    except Exception as e:
        print(f"  Extraction failed: {e}")
        return {
            "_idx":              idx,
            "paper_title":       title,
            "url":               url,
            "pdf_path":          pdf_path,
            "Extraction_Status": "Extraction Failed",
            "Failure_Reason":    str(e),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf",         required=True, choices=list(CONF_INPUT.keys()),
                        help="Which conference to process")
    parser.add_argument("--grobid_port",  type=int, default=8070,
                        help="Port of the GROBID instance (default: 8070)")
    parser.add_argument("--batch_size",   type=int, default=100,
                        help="Save checkpoint every N papers (default: 100)")
    parser.add_argument("--llm",          action="store_true", default=False,
                        help="Also run LLM after extraction (keywords, novelty, category). "
                             "If omitted, only extraction is done. "
                             "Run rerun_llm.py separately to fill LLM fields later.")
    args = parser.parse_args()

    extract_core.GROBID_URL = f"http://localhost:{args.grobid_port}/api/processFulltextDocument"
    print(f"GROBID: {extract_core.GROBID_URL}")

    url_file      = CONF_INPUT[args.conf]
    pdf_dir       = os.path.join("pdfs",      args.conf)
    out_dir       = os.path.join("output",    args.conf)
    debug_xml_dir = os.path.join("debug_xml", args.conf)

    os.makedirs(pdf_dir,       exist_ok=True)
    os.makedirs(out_dir,       exist_ok=True)
    os.makedirs(debug_xml_dir, exist_ok=True)

    if not os.path.exists(url_file):
        print(f"ERROR: {url_file} not found.")
        print(f"Run:  python scrape_urls.py --conf {args.conf}  first.")
        sys.exit(1)

    items = read_hyperlinks(url_file)
    total = len(items)
    print(f"\n[{args.conf.upper()}] {total} papers | batch size {args.batch_size}")
    print(f"Mode: {'Extraction + LLM' if args.llm else 'Extraction only (run rerun_llm.py later for LLM)'}\n")

    ckpt    = load_checkpoint(out_dir)
    done    = ckpt["done"]
    results = ckpt["results"]
    batch_n = 0

    for idx, item in enumerate(items, 1):
        if idx in done:
            print(f"[{idx}/{total}] Already done, skipping.")
            continue

        print(f"\n[{idx}/{total}] {item['title'][:80]}")
        result = process_one(idx, item, pdf_dir, debug_xml_dir, run_llm=args.llm)
        results.append(result)
        done.add(idx)
        batch_n += 1

        if batch_n % args.batch_size == 0:
            print(f"\n-- Batch of {args.batch_size} complete. Saving checkpoint --")
            save_checkpoint(out_dir, done, results)
            flush_to_excel(results, out_dir)

    print("\nAll done. Saving final output...")
    save_checkpoint(out_dir, done, results)
    flush_to_excel(results, out_dir)

    success = sum(1 for r in results if r.get("Extraction_Status") == "Success")
    print(f"\n[{args.conf.upper()}] Success: {success}/{total} | Failed: {total - success}/{total}")


if __name__ == "__main__":
    main()
