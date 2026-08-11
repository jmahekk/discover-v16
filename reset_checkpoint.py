"""Clears specific paper indices from a checkpoint so run_v11.py redoes them."""

import argparse
import json
import os

CONFERENCES = ["acl", "eacl", "emnlp", "naacl", "conll", "findings", "existing"]


def reset_range(conf: str, from_idx: int, to_idx: int):
    out_dir   = os.path.join("output", conf)
    ckpt_path = os.path.join(out_dir, "_checkpoint.json")

    if not os.path.exists(ckpt_path):
        print(f"No checkpoint found at {ckpt_path}. Nothing to do.")
        return

    with open(ckpt_path, "r", encoding="utf-8") as f:
        ckpt = json.load(f)

    done      = set(ckpt["done"])
    results   = ckpt["results"]
    to_remove = set(range(from_idx, to_idx + 1))
    before    = len(done)

    # Remove indices from the done set so run_v11.py processes them again
    done -= to_remove

    # Remove matching rows from results if _idx is stored (new format).
    # Old format checkpoints don't have _idx, so results are left untouched in that case.
    has_idx = len(results) > 0 and "_idx" in results[0]
    if has_idx:
        results = [r for r in results if r.get("_idx") not in to_remove]
        print(f"  Removed {before - len(done)} entries from done set and results list.")
    else:
        print(f"  Removed {before - len(done)} entries from done set.")
        print(f"  Old checkpoint format detected (no _idx), result rows left unchanged.")
        print(f"  Fresh results for these papers will be appended on next run.")

    ckpt["done"]    = list(done)
    ckpt["results"] = results

    with open(ckpt_path, "w", encoding="utf-8") as f:
        json.dump(ckpt, f, ensure_ascii=False, indent=2)

    print(f"\n[{conf.upper()}] Papers {from_idx}–{to_idx} reset. Ready to reprocess.")
    print(f"Run:  python run_v11.py --conf {conf}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--conf", required=True, choices=CONFERENCES)
    parser.add_argument("--from", dest="from_idx", required=True, type=int,
                        help="First paper index to reset (inclusive)")
    parser.add_argument("--to",   dest="to_idx",   required=True, type=int,
                        help="Last paper index to reset (inclusive)")
    args = parser.parse_args()

    if args.from_idx > args.to_idx:
        print("ERROR: --from must be <= --to")
        return

    reset_range(args.conf, args.from_idx, args.to_idx)


if __name__ == "__main__":
    main()
