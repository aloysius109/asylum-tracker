"""Turn a refresh audit into a source-watch report, without publishing anything.

`scripts/refresh_report.py --refresh` downloads the current UNHCR data into a
separate review run and writes `audit.json`. This script reads that audit and
says, in one short message, whether the accepted edition now disagrees with the
source. It changes no accepted file, adopts nothing and publishes nothing.

A missing audit means the refresh itself failed; that failure is already
reported by the job, so nothing is raised here.
"""
import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

QUIET = "NO ACTIVITY REVISIONS DETECTED"


def fingerprint(audit):
    """A stable identifier for this finding, so the same state is reported once."""
    state = json.dumps({key: audit.get(key) for key in
                        ("status", "new_years", "changed_application_cells",
                         "changed_decision_cells", "pending_changed")},
                       sort_keys=True)
    return hashlib.sha256(state.encode("utf-8")).hexdigest()[:12]


def report_markdown(audit, run_url):
    stamp = datetime.now(timezone.utc).strftime("%d %B %Y")
    years = ", ".join(str(year) for year in audit.get("new_years", [])) or "none"
    return "\n".join([
        f"## UNHCR source check — {stamp}", "",
        f"**{audit['status']}**", "",
        f"- New years in the candidate: {years}",
        f"- Revised application cells: {audit.get('changed_application_cells', 0):,}",
        f"- Revised decision cells: {audit.get('changed_decision_cells', 0):,}",
        f"- Pending-stock series changed: {'yes' if audit.get('pending_changed') else 'no'}",
        f"- Accepted common year {audit.get('accepted_common_year')}, "
        f"candidate common year {audit.get('candidate_common_year')}", "",
        "Nothing has been published and no accepted file was replaced. The review preview, the exact candidate",
        f"sources and the full audit are attached to [this run]({run_url}) as the `unhcr-refresh-review` artifact,",
        "kept for 30 days. Adopting an edition means rebuilding the authored report against the candidate sources",
        "and approving it explicitly, as `scripts/refresh_report.py` describes.", "",
        f"<!-- source-watch:{fingerprint(audit)} -->", ""])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("audit", type=Path, help="Path to the audit.json written by the refresh run")
    parser.add_argument("--report", type=Path, required=True, help="Where to write the Markdown report")
    parser.add_argument("--run-url", default="", help="Link to the workflow run holding the review artifact")
    args = parser.parse_args()

    drift = False
    if not args.audit.exists():
        message = "No audit was written: the source check did not complete, and its own failure is the notification."
    else:
        audit = json.loads(args.audit.read_text(encoding="utf-8"))
        if audit["status"] == QUIET:
            message = f"{QUIET}. The accepted edition still matches the UNHCR source."
        else:
            message = report_markdown(audit, args.run_url)
            args.report.write_text(message, encoding="utf-8")
            drift = True

    print(message)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(message + "\n")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write(f"drift={'true' if drift else 'false'}\n")


if __name__ == "__main__":
    main()
