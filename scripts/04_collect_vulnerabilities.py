"""
Script 04 — Collect known vulnerability data from OSV.dev.

For every unique package in the dataset, queries the OSV.dev API
to find known security advisories (CVEs, GHSAs, PYSAs).

OSV.dev aggregates data from:
  - GitHub Security Advisories (GHSA)
  - PyPI Advisory Database (PYSEC)
  - NVD / CVE

Output
------
data/vulnerabilities.csv
    Columns: package_name, vuln_count, vuln_ids, severity_levels,
             has_critical, has_high, earliest_vuln_date, latest_vuln_date
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from tqdm import tqdm
from config import DATA_DIR, OSV_API_URL, get_default_session, setup_logging

log = setup_logging("04_collect_vulnerabilities")

OSV_DELAY = 0.2  # Seconds between API calls


def query_osv(session, package_name: str) -> list[dict]:
    """Query OSV.dev for all known vulnerabilities of a PyPI package."""
    payload = {
        "package": {
            "name": package_name,
            "ecosystem": "PyPI",
        }
    }

    try:
        resp = session.post(OSV_API_URL, json=payload, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("vulns", [])
        return []
    except Exception as exc:
        log.warning("OSV query failed for %s: %s", package_name, exc)
        return []


def extract_severity(vuln: dict) -> str:
    """Extract the highest severity level from a vulnerability entry."""
    # Check database_specific or ecosystem_specific severity
    severity_entries = vuln.get("severity", [])
    for sev in severity_entries:
        if sev.get("type") == "CVSS_V3":
            score_str = sev.get("score", "")
            # Parse CVSS vector to get base score
            # CVSS:3.x/AV:N/AC:L/... format
            # We can categorize by the vector or just store as-is
            return score_str

    # Check database_specific for severity
    db_specific = vuln.get("database_specific", {})
    severity = db_specific.get("severity")
    if severity:
        return severity.upper()

    return "UNKNOWN"


def categorize_cvss(score_str: str) -> str:
    """
    Categorize a CVSS v3 vector string or plain severity label
    into CRITICAL / HIGH / MEDIUM / LOW / UNKNOWN.
    """
    score_str = score_str.upper().strip()

    if score_str in ("CRITICAL", "HIGH", "MEDIUM", "MODERATE", "LOW"):
        return "CRITICAL" if score_str == "CRITICAL" else score_str
    if score_str.replace("MODERATE", "MEDIUM") == "MEDIUM":
        return "MEDIUM"

    return "UNKNOWN"


def process_vulns(vulns: list[dict]) -> dict:
    """Process a list of OSV vulnerability records into summary metrics."""
    if not vulns:
        return {
            "vuln_count": 0,
            "vuln_ids": "",
            "severity_levels": "",
            "has_critical": False,
            "has_high": False,
            "earliest_vuln_date": "",
            "latest_vuln_date": "",
        }

    vuln_ids = []
    severities = []
    dates = []

    for v in vulns:
        vid = v.get("id", "")
        vuln_ids.append(vid)

        sev = extract_severity(v)
        cat = categorize_cvss(sev)
        severities.append(cat)

        published = v.get("published", "")
        if published:
            dates.append(published[:10])  # YYYY-MM-DD

    has_critical = "CRITICAL" in severities
    has_high = "HIGH" in severities

    return {
        "vuln_count": len(vulns),
        "vuln_ids": "; ".join(vuln_ids),
        "severity_levels": "; ".join(severities),
        "has_critical": has_critical,
        "has_high": has_high,
        "earliest_vuln_date": min(dates) if dates else "",
        "latest_vuln_date": max(dates) if dates else "",
    }


def main() -> None:
    meta_path = DATA_DIR / "package_metadata.csv"
    if not meta_path.exists():
        log.error("Run 02_resolve_dependencies.py first!")
        return

    meta_df = pd.read_csv(meta_path)
    package_names = meta_df["package_name"].unique().tolist()

    log.info("Querying OSV.dev for %d packages...", len(package_names))

    session = get_default_session()
    results = []

    for pkg in tqdm(package_names, desc="Vulnerability scan"):
        vulns = query_osv(session, pkg)
        summary = process_vulns(vulns)
        summary["package_name"] = pkg
        results.append(summary)
        time.sleep(OSV_DELAY)

    out_df = pd.DataFrame(results)
    out_path = DATA_DIR / "vulnerabilities.csv"
    out_df.to_csv(out_path, index=False)

    vuln_count = (out_df["vuln_count"] > 0).sum()
    total_vulns = out_df["vuln_count"].sum()
    log.info(
        "Saved vulnerability data to %s — %d packages have ≥1 advisory (%d total advisories)",
        out_path, vuln_count, total_vulns,
    )


if __name__ == "__main__":
    main()

