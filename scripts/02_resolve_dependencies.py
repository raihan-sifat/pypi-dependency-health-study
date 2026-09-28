"""
Script 02 — Resolve dependency trees for the top PyPI packages.

For each package in data/top_packages.csv, this script:
  1. Fetches its metadata from the PyPI JSON API.
  2. Parses `requires_dist` to extract direct dependencies.
  3. Recursively resolves transitive dependencies (up to depth 5).
  4. Records the source GitHub/GitLab repository URL when available.

Output
------
data/dependencies.csv
    Columns: parent_package, dependency_name, depth, is_direct

data/package_metadata.csv
    Columns: package_name, version, summary, home_page, repo_url,
             author, license, requires_python, last_release_date
"""

import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from tqdm import tqdm
from packaging.requirements import Requirement, InvalidRequirement
from config import (
    DATA_DIR,
    PYPI_BASE_URL,
    get_default_session,
    setup_logging,
)

log = setup_logging("02_resolve_dependencies")

MAX_DEPTH = 5  # Maximum transitive dependency depth
PYPI_DELAY = 0.1  # Seconds between PyPI API calls (be polite)


def extract_repo_url(info: dict) -> str:
    """
    Try to find a GitHub / GitLab repository URL from PyPI metadata.
    Checks project_urls first, then home_page.
    """
    project_urls = info.get("project_urls") or {}

    # Common keys used by package authors
    repo_keys = [
        "Source", "Source Code", "Repository", "GitHub",
        "Code", "Homepage", "Home", "source", "repository",
    ]
    for key in repo_keys:
        url = project_urls.get(key, "")
        if "github.com" in url or "gitlab.com" in url:
            return url.strip().rstrip("/")

    # Fall back to any project_url containing github/gitlab
    for url in project_urls.values():
        if url and ("github.com" in url or "gitlab.com" in url):
            return url.strip().rstrip("/")

    # Fall back to home_page
    home = info.get("home_page") or ""
    if "github.com" in home or "gitlab.com" in home:
        return home.strip().rstrip("/")

    return ""


def parse_dependencies(requires_dist: list[str] | None) -> list[str]:
    """
    Parse PEP 508 dependency strings, keeping only unconditional
    install-time dependencies (skip extras and optional markers).
    """
    if not requires_dist:
        return []

    deps = []
    for spec in requires_dist:
        try:
            req = Requirement(spec)
        except InvalidRequirement:
            continue

        # Skip dependencies that require extras (e.g., 'dev', 'test')
        if req.marker:
            marker_str = str(req.marker)
            # Keep if it's only a python_version constraint
            if "extra" in marker_str:
                continue

        deps.append(req.name.lower())

    return sorted(set(deps))


def fetch_package_info(session, package_name: str) -> dict | None:
    """Fetch metadata for a single package from the PyPI JSON API."""
    url = f"{PYPI_BASE_URL}/{package_name}/json"
    try:
        resp = session.get(url, timeout=20)
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def resolve_tree(
    session,
    root_package: str,
    visited: set[str],
    all_deps: list[dict],
    metadata_cache: dict,
    depth: int = 1,
):
    """Recursively resolve the dependency tree of *root_package*."""
    if depth > MAX_DEPTH:
        return

    info_data = fetch_package_info(session, root_package)
    time.sleep(PYPI_DELAY)

    if info_data is None:
        return

    info = info_data.get("info", {})

    # Cache metadata if not already cached
    if root_package not in metadata_cache:
        releases = info_data.get("releases", {})
        release_dates = []
        for version_files in releases.values():
            for f in version_files:
                if f.get("upload_time_iso_8601"):
                    release_dates.append(f["upload_time_iso_8601"])

        last_release = max(release_dates) if release_dates else ""

        metadata_cache[root_package] = {
            "package_name": root_package,
            "version": info.get("version", ""),
            "summary": (info.get("summary") or "")[:200],
            "home_page": info.get("home_page") or "",
            "repo_url": extract_repo_url(info),
            "author": info.get("author") or info.get("maintainer") or "",
            "license": (info.get("license") or "")[:100],
            "requires_python": info.get("requires_python") or "",
            "last_release_date": last_release,
        }

    direct_deps = parse_dependencies(info.get("requires_dist"))

    for dep in direct_deps:
        dep_lower = dep.lower()
        is_direct = depth == 1

        all_deps.append({
            "parent_package": root_package,
            "dependency_name": dep_lower,
            "depth": depth,
            "is_direct": is_direct,
        })

        if dep_lower not in visited:
            visited.add(dep_lower)
            resolve_tree(
                session, dep_lower, visited, all_deps, metadata_cache, depth + 1
            )


def main() -> None:
    top_packages_path = DATA_DIR / "top_packages.csv"
    if not top_packages_path.exists():
        log.error("Run 01_collect_top_packages.py first!")
        return

    top_df = pd.read_csv(top_packages_path)
    package_names = top_df["package_name"].tolist()

    log.info("Resolving dependencies for %d packages...", len(package_names))

    session = get_default_session()
    all_deps: list[dict] = []
    metadata_cache: dict[str, dict] = {}
    global_visited: set[str] = set(p.lower() for p in package_names)

    for pkg in tqdm(package_names, desc="Resolving deps"):
        pkg_lower = pkg.lower()
        # Ensure root package metadata is also collected
        resolve_tree(session, pkg_lower, global_visited, all_deps, metadata_cache)

    # Save dependency edges
    deps_df = pd.DataFrame(all_deps)
    deps_path = DATA_DIR / "dependencies.csv"
    deps_df.to_csv(deps_path, index=False)

    unique_deps = set(deps_df["dependency_name"].unique())
    log.info(
        "Saved %d dependency edges (%d unique dependencies) to %s",
        len(deps_df), len(unique_deps), deps_path,
    )

    # Save package metadata
    meta_df = pd.DataFrame(list(metadata_cache.values()))
    meta_path = DATA_DIR / "package_metadata.csv"
    meta_df.to_csv(meta_path, index=False)
    log.info("Saved metadata for %d packages to %s", len(meta_df), meta_path)


if __name__ == "__main__":
    main()

