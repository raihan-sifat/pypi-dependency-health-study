"""
Script 01 — Collect the top 1,000 most-downloaded PyPI packages.

Data source
-----------
https://hugovk.github.io/top-pypi-packages/
  → A community-maintained JSON snapshot of the most-downloaded packages
    over the past 30 days, updated daily.

Output
------
data/top_packages.csv
    Columns: rank, package_name, download_count
"""

import sys
from pathlib import Path

# Add project root to path so we can import config
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from config import (
    DATA_DIR,
    TOP_N_PACKAGES,
    TOP_PACKAGES_URL,
    get_default_session,
    setup_logging,
)

log = setup_logging("01_collect_top_packages")


def fetch_top_packages(n: int = TOP_N_PACKAGES) -> pd.DataFrame:
    """Download the top-N PyPI packages by 30-day download count."""
    session = get_default_session()
    log.info("Fetching top packages list from %s", TOP_PACKAGES_URL)

    resp = session.get(TOP_PACKAGES_URL, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    rows = data.get("rows", [])
    log.info("Total packages in source: %d", len(rows))

    records = []
    for i, row in enumerate(rows[:n], start=1):
        records.append({
            "rank": i,
            "package_name": row["project"],
            "download_count": row["download_count"],
        })

    df = pd.DataFrame(records)
    log.info("Selected top %d packages", len(df))
    log.info(
        "Download range: %s (rank 1) → %s (rank %d)",
        f"{df['download_count'].iloc[0]:,}",
        f"{df['download_count'].iloc[-1]:,}",
        len(df),
    )
    return df


def main() -> None:
    df = fetch_top_packages()
    out_path = DATA_DIR / "top_packages.csv"
    df.to_csv(out_path, index=False)
    log.info("Saved to %s (%d rows)", out_path, len(df))


if __name__ == "__main__":
    main()

