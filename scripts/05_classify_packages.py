"""
Script 05 — Classify packages into health states:
  • Healthy: Active (release <12mo) AND multi-maintainer/team-backed
  • At-Risk: Single-maintainer OR moderate inactivity (12–18mo)
  • Silently Abandoned: Severe inactivity (>=18mo) OR explicitly archived

Output:
  data/classified_packages.csv
"""

import sys
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from config import (
    DATA_DIR,
    ABANDONMENT_CUTOFF,
    AT_RISK_CUTOFF,
    setup_logging,
)

log = setup_logging("05_classify_packages")

TEAM_KEYWORDS = [
    "team", "developers", "foundation", "org", "corporation", "corp",
    "inc", "contributors", "authors", "community", "committee",
    "google", "microsoft", "aws", "amazon", "apache", "meta",
    "pypa", "psf", "llc", "ltd", "group", "labs", "project",
    "red hat", "canonical", "mozilla", "pallets", "encode"
]


def parse_date(d_str: str) -> datetime | None:
    if not d_str or pd.isna(d_str):
        return None
    try:
        s = str(d_str).strip()
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def is_multi_maintainer(author: str, repo_url: str) -> bool:
    a = str(author).lower()
    r = str(repo_url).lower()
    if any(k in a for k in TEAM_KEYWORDS):
        return True
    if any(k in r for k in ["apache", "google", "azure", "aws", "pypa", "psf", "pallets", "encode"]):
        return True
    if "," in a or ";" in a or " and " in a or "&" in a:
        return True
    return False


def classify(row: pd.Series) -> str:
    if row.get("is_archived", False):
        return "silently_abandoned"

    last_commit = parse_date(row.get("last_commit_date"))
    last_release = parse_date(row.get("last_release_date"))

    dates = [d for d in [last_commit, last_release] if d is not None]
    if not dates:
        return "at_risk"

    latest = max(dates)
    if latest < ABANDONMENT_CUTOFF:
        return "silently_abandoned"
    elif latest < AT_RISK_CUTOFF:
        return "at_risk"

    # If active (<12 months), check single-maintainer bus factor
    if row.get("is_single_maintainer", False):
        return "at_risk"

    return "healthy"


def main() -> None:
    top_path = DATA_DIR / "top_packages.csv"
    meta_path = DATA_DIR / "package_metadata.csv"
    github_path = DATA_DIR / "github_metadata.csv"
    vuln_path = DATA_DIR / "vulnerabilities.csv"
    deps_path = DATA_DIR / "dependencies.csv"

    for p in [meta_path, vuln_path, deps_path]:
        if not p.exists():
            log.error("Missing required input file: %s", p.name)
            return

    top_df = pd.read_csv(top_path) if top_path.exists() else pd.DataFrame(columns=["package_name"])
    meta_df = pd.read_csv(meta_path)
    github_df = pd.read_csv(github_path) if github_path.exists() else pd.DataFrame(columns=["package_name"])
    vuln_df = pd.read_csv(vuln_path)
    deps_df = pd.read_csv(deps_path)

    # Merge
    merged = meta_df.merge(
        github_df.drop(columns=["github_url"], errors="ignore"),
        on="package_name",
        how="left"
    )
    merged = merged.merge(vuln_df, on="package_name", how="left")

    merged["vuln_count"] = merged["vuln_count"].fillna(0).astype(int)
    merged["has_critical"] = merged["has_critical"].fillna(False)
    merged["has_high"] = merged["has_high"].fillna(False)

    top_set = set(top_df["package_name"].str.lower().str.replace("_", "-"))
    merged["is_top_package"] = merged["package_name"].isin(top_set)

    # Fan-in / dependent count
    dep_counts = (
        deps_df.groupby("dependency_name")["parent_package"]
        .nunique()
        .reset_index()
        .rename(columns={"dependency_name": "package_name", "parent_package": "dependent_count"})
    )
    merged = merged.merge(dep_counts, on="package_name", how="left")
    merged["dependent_count"] = merged["dependent_count"].fillna(0).astype(int)

    # Single-maintainer determination
    merged["is_single_maintainer"] = ~merged.apply(
        lambda r: is_multi_maintainer(r.get("author", ""), r.get("repo_url", "")),
        axis=1
    )

    # Classification
    merged["health_status"] = merged.apply(classify, axis=1)

    out_path = DATA_DIR / "classified_packages.csv"
    merged.to_csv(out_path, index=False)
    log.info("Classified %d packages. Status Breakdown:\n%s", len(merged), merged["health_status"].value_counts())
    log.info("Single-Maintainer packages: %d (%.1f%%)", merged["is_single_maintainer"].sum(), 100 * merged["is_single_maintainer"].mean())
    log.info("Saved to %s", out_path)


if __name__ == "__main__":
    main()
