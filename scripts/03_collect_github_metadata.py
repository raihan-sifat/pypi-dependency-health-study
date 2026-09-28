"""
Script 03 — Collect GitHub repository health metadata.

For every package with a known GitHub repo URL (from package_metadata.csv),
this script queries the GitHub REST API to gather:
  - contributor count and per-contributor commit counts (past 24 months)
  - date of the most recent commit
  - open issue and pull-request counts
  - stargazer and fork counts

Output
------
data/github_metadata.csv
    One row per package with GitHub health signals.
"""

import re
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from tqdm import tqdm
from config import (
    DATA_DIR,
    GITHUB_API_URL,
    CONTRIBUTOR_WINDOW_START,
    DATA_COLLECTION_DATE,
    get_github_session,
    rate_limited_get,
    setup_logging,
)

log = setup_logging("03_collect_github_metadata")

GITHUB_DELAY = 0.8  # Seconds between API calls (stay under 5000/hr)


def parse_github_owner_repo(url: str) -> tuple[str, str] | None:
    """Extract (owner, repo) from a GitHub URL."""
    # Match patterns like github.com/owner/repo[/...]
    match = re.search(r"github\.com/([^/]+)/([^/\s#?]+)", url)
    if match:
        owner = match.group(1)
        repo = match.group(2).rstrip("/").removesuffix(".git")
        return owner, repo
    return None


def get_repo_info(session, owner: str, repo: str) -> dict | None:
    """Fetch basic repository info (stars, forks, open_issues, etc.)."""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}"
    resp = rate_limited_get(session, url)
    if resp is None:
        return None
    return resp.json()


def get_latest_commit_date(session, owner: str, repo: str) -> str:
    """Return ISO date of the most recent commit on the default branch."""
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/commits"
    resp = rate_limited_get(session, url, params={"per_page": 1})
    if resp is None or not resp.json():
        return ""
    commit = resp.json()[0]
    date_str = (
        commit.get("commit", {}).get("committer", {}).get("date", "")
    )
    return date_str


def get_contributor_stats(
    session, owner: str, repo: str
) -> tuple[int, int, list[int]]:
    """
    Return (total_contributors, active_contributors_in_window,
            list_of_commit_counts_per_contributor_in_window).

    Uses the /contributors endpoint (up to 500 contributors).
    For very large repos this may be truncated — acceptable for our study.
    """
    contributors = []
    page = 1

    while page <= 10:  # cap at 10 pages = 1000 contributors max
        url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/contributors"
        resp = rate_limited_get(
            session, url, params={"per_page": 100, "page": page, "anon": "false"}
        )
        time.sleep(GITHUB_DELAY)

        if resp is None:
            break

        page_data = resp.json()
        if not page_data:
            break

        contributors.extend(page_data)
        if len(page_data) < 100:
            break
        page += 1

    total_contributors = len(contributors)

    # For active-contributor analysis, we check commit activity
    # We use the /stats/contributors endpoint which gives weekly data
    url = f"{GITHUB_API_URL}/repos/{owner}/{repo}/stats/contributors"
    resp = rate_limited_get(session, url)
    time.sleep(GITHUB_DELAY)

    active_count = 0
    commit_counts = []

    if resp is not None and isinstance(resp.json(), list):
        stats = resp.json()
        window_start_ts = int(CONTRIBUTOR_WINDOW_START.timestamp())

        for contributor in stats:
            weeks = contributor.get("weeks", [])
            commits_in_window = sum(
                w.get("c", 0)
                for w in weeks
                if w.get("w", 0) >= window_start_ts
            )
            if commits_in_window > 0:
                active_count += 1
                commit_counts.append(commits_in_window)

    return total_contributors, active_count, commit_counts


def get_open_issues_count(session, owner: str, repo: str) -> int:
    """Get the count of open issues (GitHub counts PRs as issues too)."""
    url = f"{GITHUB_API_URL}/search/issues"
    params = {
        "q": f"repo:{owner}/{repo} is:issue is:open",
        "per_page": 1,
    }
    resp = rate_limited_get(session, url, params=params)
    time.sleep(GITHUB_DELAY)
    if resp is None:
        return -1
    return resp.json().get("total_count", -1)


def get_open_prs_count(session, owner: str, repo: str) -> int:
    """Get the count of open pull requests."""
    url = f"{GITHUB_API_URL}/search/issues"
    params = {
        "q": f"repo:{owner}/{repo} is:pr is:open",
        "per_page": 1,
    }
    resp = rate_limited_get(session, url, params=params)
    time.sleep(GITHUB_DELAY)
    if resp is None:
        return -1
    return resp.json().get("total_count", -1)


def collect_github_metadata(row: pd.Series, session) -> dict:
    """Collect all GitHub metadata for a single package."""
    package_name = row["package_name"]
    repo_url = row.get("repo_url", "")

    result = {
        "package_name": package_name,
        "github_url": repo_url,
        "has_github": False,
        "stars": -1,
        "forks": -1,
        "open_issues": -1,
        "open_prs": -1,
        "total_contributors": -1,
        "active_contributors_24m": -1,
        "last_commit_date": "",
        "is_archived": False,
        "is_fork": False,
        "default_branch": "",
    }

    if not repo_url or "github.com" not in repo_url:
        return result

    parsed = parse_github_owner_repo(repo_url)
    if parsed is None:
        return result

    owner, repo = parsed
    result["has_github"] = True

    # 1. Basic repo info
    repo_info = get_repo_info(session, owner, repo)
    time.sleep(GITHUB_DELAY)

    if repo_info is None:
        result["has_github"] = False
        return result

    result["stars"] = repo_info.get("stargazers_count", -1)
    result["forks"] = repo_info.get("forks_count", -1)
    result["is_archived"] = repo_info.get("archived", False)
    result["is_fork"] = repo_info.get("fork", False)
    result["default_branch"] = repo_info.get("default_branch", "")

    # 2. Latest commit
    result["last_commit_date"] = get_latest_commit_date(session, owner, repo)
    time.sleep(GITHUB_DELAY)

    # 3. Contributor stats
    total, active, _ = get_contributor_stats(session, owner, repo)
    result["total_contributors"] = total
    result["active_contributors_24m"] = active

    # 4. Open issues & PRs
    result["open_issues"] = get_open_issues_count(session, owner, repo)
    result["open_prs"] = get_open_prs_count(session, owner, repo)

    return result


def main() -> None:
    meta_path = DATA_DIR / "package_metadata.csv"
    if not meta_path.exists():
        log.error("Run 02_resolve_dependencies.py first!")
        return

    meta_df = pd.read_csv(meta_path)

    # Filter to packages with a GitHub URL
    has_repo = meta_df["repo_url"].fillna("").str.contains("github.com")
    github_df = meta_df[has_repo].copy()
    no_repo_df = meta_df[~has_repo].copy()

    log.info(
        "%d packages with GitHub URL, %d without",
        len(github_df), len(no_repo_df),
    )

    session = get_github_session()

    # Check rate limit
    rl_resp = session.get(f"{GITHUB_API_URL}/rate_limit")
    if rl_resp.status_code == 200:
        rl = rl_resp.json().get("resources", {}).get("core", {})
        log.info(
            "GitHub API rate limit: %d remaining / %d total",
            rl.get("remaining", 0), rl.get("limit", 0),
        )

    results = []
    for _, row in tqdm(
        github_df.iterrows(), total=len(github_df), desc="GitHub metadata"
    ):
        result = collect_github_metadata(row, session)
        results.append(result)

    # Also add entries for packages without GitHub
    for _, row in no_repo_df.iterrows():
        results.append({
            "package_name": row["package_name"],
            "github_url": "",
            "has_github": False,
            "stars": -1,
            "forks": -1,
            "open_issues": -1,
            "open_prs": -1,
            "total_contributors": -1,
            "active_contributors_24m": -1,
            "last_commit_date": "",
            "is_archived": False,
            "is_fork": False,
            "default_branch": "",
        })

    out_df = pd.DataFrame(results)
    out_path = DATA_DIR / "github_metadata.csv"
    out_df.to_csv(out_path, index=False)
    log.info("Saved GitHub metadata for %d packages to %s", len(out_df), out_path)


if __name__ == "__main__":
    main()

