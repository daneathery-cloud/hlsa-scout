"""Command line for the phone edition: scan, check the scan is complete, build
the site folder. Used by the scheduled GitHub workflow.

    python build_site_cli.py --out site
    python build_site_cli.py --out site --from-cache _cache/scan.pkl   (testing)
"""
import argparse
import os
import pickle
import sys

import store
import scan_runner
import site_builder


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site")
    ap.add_argument("--from-cache", help="reuse a pickled scan instead of scanning (testing)")
    ap.add_argument("--save-cache", help="pickle the scan here (testing)")
    ap.add_argument("--no-free", action="store_true", help="skip the free-version lookups")
    ap.add_argument("--force", action="store_true", help="publish even if the quality check fails")
    args = ap.parse_args()

    if args.from_cache:
        with open(args.from_cache, "rb") as f:
            result = pickle.load(f)
    else:
        conn = store.get_conn(":memory:")   # nothing to keep between cloud runs except npi_seen.json
        result = scan_runner.run_full_scan(conn, progress_cb=lambda m: print(m, flush=True))
        if args.save_cache:
            os.makedirs(os.path.dirname(args.save_cache) or ".", exist_ok=True)
            with open(args.save_cache, "wb") as f:
                pickle.dump(result, f)

    problems = site_builder.check_quality(result)
    if problems:
        print("QUALITY CHECK FAILED: " + "; ".join(problems), flush=True)
        if not args.force:
            print("Not publishing: the last good scan stays up.", flush=True)
            return 1

    info = site_builder.build_site(result, args.out, look_up_free=not args.no_free,
                                   progress=lambda m: print(m, flush=True))
    print(f"Built phone site {info['build_id']} (scanned {info['scan_label']}); {len(result['stories'])} stories, "
          f"{len(result['orgs'])} organizations ({info['new_orgs']} new this week); sizes {info['sizes']}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
