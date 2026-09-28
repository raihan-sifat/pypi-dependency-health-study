# Silent Abandonment in the Python Ecosystem

**An Empirical Study of Maintenance Risk in Critical PyPI Dependencies**

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.23007343.svg)](https://doi.org/10.5281/zenodo.23007343)

## Abstract

Modern software systems heavily depend on open-source packages distributed
through ecosystem registries such as PyPI. When upstream maintainers silently
abandon a package — ceasing development without formal deprecation — every
downstream project inherits unpatched vulnerabilities and compatibility risks.
This study empirically analyses the top 1,000 most-downloaded PyPI packages and
their transitive dependency trees to quantify single-maintainer prevalence,
silent abandonment rates, and the statistical association between maintenance
inactivity and known security advisories. Our dataset, analysis scripts, and
all figures are released under an open licence for full reproducibility.

## Research Questions

| #       | Question                                                                                                                            |
| ------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| **RQ1** | What proportion of critical PyPI packages depend on packages maintained by a single developer?                                      |
| **RQ2** | How prevalent is silent abandonment (≥18 months of inactivity) among transitive dependencies of the top 1,000 PyPI packages?        |
| **RQ3** | Is there a statistically significant association between abandonment indicators and the presence of known security vulnerabilities? |

## Repository Structure

```
.
├── README.md
├── requirements.txt
├── .gitignore
├── config.py                          # Shared constants & helpers
├── scripts/
│   ├── 01_collect_top_packages.py     # Fetch top-1000 PyPI packages
│   ├── 02_resolve_dependencies.py     # Build transitive dependency trees
│   ├── 03_collect_github_metadata.py  # Gather repo-level health signals
│   ├── 04_collect_vulnerabilities.py  # Query OSV.dev for advisories
│   ├── 05_classify_packages.py        # Label healthy / at-risk / abandoned
│   └── 06_analyze_and_visualize.py    # Statistics & figures
├── data/                              # Collected datasets (CSV)
├── figures/                           # Generated charts (PNG/SVG)
└── paper/
    └── paper.md                       # Full manuscript (Markdown source)
```

## Reproduction

### Prerequisites

- Python 3.10+
- A GitHub Personal Access Token (for API rate limits)

### Setup

```bash
git clone https://github.com/raihan-sifat/pypi-dependency-health-study.git
cd pypi-dependency-health-study
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
# source .venv/bin/activate
pip install -r requirements.txt
```

### Configure

Create a `.env` file in the project root:

```
GITHUB_TOKEN=ghp_YOUR_PERSONAL_ACCESS_TOKEN
```

### Run the pipeline

Execute the scripts in order:

```bash
python scripts/01_collect_top_packages.py
python scripts/02_resolve_dependencies.py
python scripts/03_collect_github_metadata.py
python scripts/04_collect_vulnerabilities.py
python scripts/05_classify_packages.py
python scripts/06_analyze_and_visualize.py
```

## Licence

- **Code**: MIT Licence
- **Dataset & Paper**: CC BY 4.0

## Author

**Sifat Raihan** — [github.com/raihan-sifat](https://github.com/raihan-sifat)
