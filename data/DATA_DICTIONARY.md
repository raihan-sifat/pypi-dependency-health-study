# Data Dictionary

Documentation for every CSV in `data/`, produced by the six-stage pipeline in
`scripts/`.

| | |
|---|---|
| **Data snapshot** | **2026-09-28** |
| **Packages covered** | 1,303 (1,000 seeds + transitive dependencies) |
| **Dependency edges** | 3,022 |
| **Total advisories recorded** | 3,007 (not deduplicated — see [Caveats](#caveats)) |
| **Licence** | CC BY 4.0 (see `LICENSE-CC-BY-4.0`) |

## Pipeline stages and file provenance

| Stage | Script | Writes | Data sources |
|---|---|---|---|
| 01 | `01_collect_top_packages.py` | `top_packages.csv` | [hugovk top-pypi-packages](https://hugovk.github.io/top-pypi-packages/) |
| 02 | `02_resolve_dependencies.py` | `dependencies.csv`, `package_metadata.csv` | PyPI JSON API |
| 03 | `03_collect_github_metadata.py` | `github_metadata.csv` | GitHub REST API |
| 04 | `04_collect_vulnerabilities.py` | `vulnerabilities.csv` | [OSV.dev](https://osv.dev/) |
| 05 | `05_classify_packages.py` | `classified_packages.csv` | 02 + 03 + 04 (local join) |
| 06 | `06_analyze_and_visualize.py` | `statistics_summary.csv`, `figures/*` | 05 (local analysis) |

`statistics_summary.csv` documents 10 aggregate metrics derived by stage 06.

---

## Conventions used across all files

### Null and sentinel values

| Value | Meaning |
|---|---|
| *(empty cell)* | The field is genuinely absent upstream (e.g. a PyPI project with no declared author). |
| **`-1`** | **An API call failed** and no value could be retrieved. `-1` is the initialiser in `03_collect_github_metadata.py:173-183`, so it means "not measured", **not** a real count of −1. |
| **`False`** for a boolean signal | Default initialiser, not an observed `False`. See [Caveats](#caveats) — `is_archived` was never actually observed. |
| **`UNKNOWN`** | Severity could not be categorised (see `categorize_cvss`). |
| *(empty)* for `latest_vuln_date` | The package has zero known advisories. |

### Identifier normalisation

- Package names are stored **lowercased** with `_` normalised to `-` (PEP 503
  normalisation) in `dependencies.csv` and `package_metadata.csv`.
- `top_packages.csv` preserves the **original** `project` casing from the
  source snapshot. Join on the normalised form.

### Dates

All timestamps are ISO 8601 UTC strings (`YYYY-MM-DDTHH:MM:SS.ffffffZ`).
`latest_vuln_date` is date-only (`YYYY-MM-DD`).

### Threshold constants

Defined in `config.py` and applied in `05_classify_packages.py`:

| Constant | Value | Meaning |
|---|---|---|
| `TOP_N_PACKAGES` | 1,000 | Number of seed packages |
| `ABANDONMENT_MONTHS` | 18 | Implemented as `18 × 30 = 540 days` (**17.7 months**) |
| `AT_RISK_MONTHS` | 12 | Implemented as `12 × 30 = 360 days` (**11.8 months**) |
| `LOOKBACK_MONTHS` | 24 | Contributor activity window |
| `SINGLE_MAINTAINER_COMMIT_THRESHOLD` | 10 | **Declared but never used** — see [Caveats](#caveats) |
| `MAX_DEPTH` (in script 02) | 5 | Intended max depth; **max depth actually reached is 2** |

---

## `top_packages.csv` — 1,000 rows

Seed set: the 1,000 most-downloaded PyPI packages in the 30-day window
ending 2026-09-28.

| Column | Type | Nulls | Unique | Description | Example |
|---|---|---|---|---|---|
| `rank` | int | 0 | 1,000 | Download rank, 1 = most downloaded | `1` |
| `package_name` | str | 0 | 1,000 | Package name as published (original casing) | `boto3` |
| `download_count` | int | 0 | 1,000 | Downloads in the 30-day window | `3206668324` |

**Range:** 20,352,774 (rank 1,000) → 3,206,668,324 (rank 1). Sum = **156.59 B/month**.

Produced by: `01_collect_top_packages.py`

---

## `dependencies.csv` — 3,022 rows

Directed edges. One row per `(parent_package → dependency_name)` pair.

| Column | Type | Nulls | Unique | Description | Example |
|---|---|---|---|---|---|
| `parent_package` | str | 0 | 688 | Package that declares the dependency | `boto3` |
| `dependency_name` | str | 0 | 904 | Package being depended upon (normalised) | `botocore` |
| `depth` | int | 0 | **2** | Recursion depth from the seed (`1` = direct) | `1` |
| `is_direct` | bool | 0 | 2 | `True` iff `depth == 1` | `True` |

**Observed depth distribution:**

| Depth | Edges |
|---|---|
| 1 | 2,550 |
| 2 | 472 |
| 3–5 | **0** |

**Derived facts:** 688 distinct parents, of which 63 are not seeds — meaning
**375 of the 1,000 seeds produced zero dependency edges**. See
[Caveats](#caveats) for why depth 3+ is empty.

Produced by: `02_resolve_dependencies.py`

---

## `package_metadata.csv` — 1,303 rows

PyPI metadata for every package in the study (seeds ∪ dependencies).

| Column | Type | Nulls | Unique | Description | Example |
|---|---|---|---|---|---|
| `package_name` | str | 0 | 1,303 | Normalised package name | `idna` |
| `version` | str | 0 | 707 | Latest version on PyPI | `3.20` |
| `summary` | str | 12 | 1,246 | Short description, truncated to 200 chars | `Internationalized Domain Names in Application (IDNA)` |
| `home_page` | str | **704** | 398 | `info.home_page` from PyPI | `https://github.com/certifi/python-certifi` |
| `repo_url` | str | 117 | 855 | GitHub/GitLab repo, scraped from `project_urls` then `home_page` | `https://github.com/kjd/idna` |
| `author` | str | **577** | 373 | `info.author`, falling back to `info.maintainer` | `Kenneth Reitz` |
| `license` | str | **555** | 117 | SPDX or free-text licence string, truncated to 100 chars | `MPL-2.0` |
| `requires_python` | str | 86 | 69 | PEP 440 Python requirement specifier | `>=3.9` |
| `last_release_date` | str | 0 | 1,290 | Upload timestamp of the **most recent file across all releases** | `2026-09-17T14:11:04.752193Z` |

> **Note on `home_page` nulls (704/1,303 = 54%).** PyPI deprecated the
> `home_page` field; modern metadata lives in `project_urls`, which
> `extract_repo_url` reads in preference. A null `home_page` is normal and
> does not imply a missing repository.

> **Note on `author` nulls (577/1,303 = 44%).** This is the single most
> consequential gap in the dataset — see [Caveats](#caveats).

Produced by: `02_resolve_dependencies.py`

---

## `github_metadata.csv` — 1,303 rows

Intended GitHub health signals. **This file is effectively empty — see
[Caveats](#caveats) before using any column other than `last_commit_date`.**

| Column | Type | Nulls | Unique | Description | Example |
|---|---|---|---|---|---|
| `package_name` | str | 0 | 1,303 | Join key | `amqp` |
| `github_url` | str | 118 | 854 | Repo URL carried over from `package_metadata` | `http://github.com/celery/py-amqp` |
| `has_github` | bool | 0 | 2 | `True` for 1,185 rows | `True` |
| `stars` | int | 0 | **1** | Always **`-1`** — API call failed | `-1` |
| `forks` | int | 0 | **1** | Always **`-1`** — API call failed | `-1` |
| `open_issues` | int | 0 | **1** | Always **`-1`** — API call failed | `-1` |
| `active_contributors_24m` | int | 0 | **1** | Always **`1`** — stats endpoint returned nothing usable | `1` |
| `last_commit_date` | str | 0 | 1,290 | Committer date of HEAD on the default branch (**populated**) | `2026-09-19T08:39:40.147670Z` |
| `is_archived` | bool | 0 | **1** | Always **`False`** — default, never observed | `False` |
| `is_fork` | bool | 0 | **1** | Always **`False`** — default, never observed | `False` |

> **Column count mismatch.** This file has **10 columns**. The current
> `03_collect_github_metadata.py` emits **13** — it also writes `open_prs`,
> `total_contributors`, and `default_branch`. The shipped CSV was therefore not
> produced by the shipped script. Re-running the pipeline will change this
> file's shape and contents.

Produced by: `03_collect_github_metadata.py`

---

## `vulnerabilities.csv` — 1,303 rows

Known advisories from OSV.dev, which aggregates GHSA, PYSEC, and CVE records.

| Column | Type | Nulls | Unique | Description | Example |
|---|---|---|---|---|---|
| `package_name` | str | 0 | 1,303 | Join key | `pluggy` |
| `vuln_count` | int | 0 | 43 | Number of advisory records returned (**not deduplicated**) | `4` |
| `vuln_ids` | str | 1,097 | 203 | `; `-separated OSV advisory IDs | `GHSA-65pc-fj4g-8rjx; GHSA-jjg7-2v4v-x38h; PYSEC-...` |
| `has_critical` | bool | 0 | 2 | Any advisory categorised `CRITICAL` (**unreliable**) | `False` |
| `has_high` | bool | 0 | 2 | Any advisory categorised `HIGH` (**unreliable**) | `False` |
| `latest_vuln_date` | str | 1,097 | 75 | Most recent `published` date | `2026-06-05` |

**206 packages (15.8%)** have at least one advisory, totalling **3,007 records**.

> **Counts are inflated.** Records are not deduplicated across GHSA/PYSEC/CVE, so
> a single CVE mirrored in three databases counts three times. Highest counts —
> `django` 321, `apache-airflow` 288, `mlflow` 162, `pillow` 153, `nltk` 100 —
> are not plausible as distinct vulnerabilities.

> **`has_critical` / `has_high` are unreliable.** `extract_severity` returns a
> CVSS *vector string* (e.g. `CVSS:3.1/AV:N/AC:L/...`), which `categorize_cvss`
> then tries to match against literal labels. Vectors never match, so CVSS-scored
> advisories resolve to `UNKNOWN` and the two flags undercount.

Produced by: `04_collect_vulnerabilities.py`

---

## `classified_packages.csv` — 1,303 rows

**The primary analytical dataset.** A left-join of `package_metadata` +
`github_metadata` + `vulnerabilities`, enriched with derived fields. All columns
from those three files are present; the derived columns are documented below.

### Derived columns

| Column | Type | Nulls | Unique | Description | Example |
|---|---|---|---|---|---|
| `is_top_package` | bool | 0 | 2 | `True` for the 1,000 seed packages | `True` |
| `dependent_count` | int | 0 | 37 | Number of distinct packages that depend on this one (**fan-in**) | `11` |
| `is_single_maintainer` | bool | 0 | 2 | `True` if no team/org signal was found (**keyword heuristic**) | `True` |
| `health_status` | str | 0 | 3 | `healthy` / `at_risk` / `silently_abandoned` | `at_risk` |

### `health_status` distribution

| Value | Count | Share | Definition (`05_classify_packages.py:63-84`) |
|---|---|---|---|
| `healthy` | 257 | 19.7% | Active (< 12 mo) **and** team/org-backed |
| `at_risk` | 861 | 66.1% | 12–18 mo inactive, **or** active but single-maintainer |
| `silently_abandoned` | 185 | 14.2% | ≥ 18 mo inactive, **or** repo archived |

These three categories are **mutually exclusive and exhaustive**
(257 + 861 + 185 = 1,303). Total unhealthy = **80.3%**.

Precedence in `classify()`: `is_archived` → age of most recent activity →
single-maintainer check.

---

## `statistics_summary.csv` — 10 rows

Aggregate metrics from stage 06, in `Metric` / `Value` form.

| Metric | Value |
|---|---|
| Total Packages Analysed | 1,303 |
| Direct and Transitive Dependencies | 3,022 |
| Single-Maintainer Packages | 989 (75.9%) |
| Silently Abandoned (≥18 mo inactive) | 185 (14.2%) |
| At-Risk (12–18 mo or single maintainer) | 861 (66.08%) |
| Healthy Maintenance State | 257 (19.72%) |
| Packages with Known Vulnerabilities | 206 (15.8%) |
| Chi-Square Test (Abandonment vs Vuln) | 8.0513 |
| p-value | 4.55e-03 |
| Odds Ratio | 0.60 |

> The chi-square is **`scipy`'s default Yates continuity-corrected** value for a
> 2×2 table, not uncorrected Pearson (which is 8.6019, p = 0.00336). **Cramér's V
> = 0.0786** is computed by stage 06 but not written to this file.

---

## Caveats

These are known limitations of the collected data. They are documented here so
that anyone reusing the dataset is not surprised.

1. **GitHub enrichment failed wholesale.** `stars`, `forks`, and `open_issues`
   are `-1` for all 1,303 rows; `active_contributors_24m` is `1` for all rows;
   `is_archived` and `is_fork` are the default `False` for all rows. Only
   `last_commit_date` carries usable data. Consequently **no column in this
   dataset reflects real commit-topology or contributor information.**

2. **`is_single_maintainer` is a keyword heuristic, not a measurement.** It is
   computed by substring-matching the PyPI `author` string and `repo_url`
   against 25 hardcoded tokens (`TEAM_KEYWORDS`). **522 of the 989**
   single-maintainer packages have an **empty `author`** and are labelled single
   by default; 47 have neither author nor GitHub data. Known misclassifications
   include `numpy` (author "Travis E. Oliphant *et al.*"), `typing-extensions`
   (`github.com/python/...` — `python` is not in the token list), `urllib3`,
   `cryptography`, and `pydantic`.

3. **The dependency graph reaches depth 2, not the intended 5.** `02_resolve_dependencies.py:189`
   pre-seeds the recursion guard with all 1,000 seed names, so any dependency
   that is itself a top-1,000 package is never expanded. Depths 3–5 contain zero
   edges, and 375 of 1,000 seeds yielded no edges at all.

4. **The 18- and 12-month thresholds are 17.7 and 11.8 months.** They are
   computed as `months * 30` days (`config.py:37-38`) rather than calendar
   months.

5. **Cut-offs are relative to `datetime.now()` at run time**, not to the fixed
   snapshot date of 2026-09-28. Re-running the pipeline will shift the
   185 / 861 / 257 partition.

6. **`vuln_count` is not deduplicated and severity flags are unreliable** — see
   the notes on `vulnerabilities.csv`.

7. **`SINGLE_MAINTAINER_COMMIT_THRESHOLD` is dead code.** It is declared in
   `config.py` but referenced by no script.

8. **RQ3's abandoned-vs-vulnerability contrast rests on 10 events.** Only
   10 of 185 abandoned packages have an advisory (5.4%), versus 56 of 257
   healthy packages (21.8%). This single thin cell drives the reported
   logistic-regression coefficient (β = −1.4901). No exact test or sensitivity
   analysis accompanies it.

For the full audit, including manuscript-level errors, see the "Threats to
Validity" section of `paper/paper.md`.

---

## Reuse

```python
import pandas as pd

df = pd.read_csv("data/classified_packages.csv")

# Abandoned packages that are depended upon by many others — highest blast radius
high_risk = df[
    (df["health_status"] == "silently_abandoned")
    & (df["dependent_count"] >= 5)
].sort_values("dependent_count", ascending=False)

print(len(high_risk))
```

Always re-check `is_archived` / `stars` / `active_contributors_24m` against the
sentinel conventions above before filtering on them.