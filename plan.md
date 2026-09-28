# Research Project Plan & Execution Roadmap

**Project:** Silent Abandonment in the Python Ecosystem: An Empirical Study of Maintenance Risk in Critical PyPI Dependencies  
**Author:** Sifat Raihan  
**Repository:** `pypi-dependency-health-study`  
**Current Date:** September 28, 2026

---

## 1. Executive Summary

This empirical study investigates the operational stability and security implications of unmaintained upstream libraries within the Python Package Index (PyPI). By sampling the top 1,000 most-downloaded packages and resolving their full direct and transitive dependency graphs (1,303 unique libraries, 3,022 edges), the research quantifies maintainer concentration (bus factor), rates of silent abandonment ($\ge 18$ months inactive), and the relationship between project dormancy and documented security advisories in the Open Source Vulnerabilities (OSV) database.

---

## 2. What Has Been Done (Completed Work)

### A. Data Ingestion & Dependency Graph Resolution

- [x] **01_collect_top_packages.py**: Ingested the top 1,000 most-downloaded PyPI packages using standardized 30-day metrics (covering 95%+ of aggregate PyPI traffic).
- [x] **02_resolve_dependencies.py**: Built a recursive PEP 508 dependency parser resolving both direct and transitive dependencies up to depth 5 via the PyPI JSON API, identifying 3,022 directed edges across 1,303 distinct packages.
- [x] **03_collect_github_metadata.py**: Implemented telemetry mining for repository activity, release dates across all distributions, commit recency, and archival indicators.
- [x] **04_collect_vulnerabilities.py**: Automated batch querying against the Google OSV.dev API (aggregating GHSA, CVE, and PYSEC registries).
- [x] **05_classify_packages.py**: Formulated objective operational criteria categorizing libraries into _Healthy_, _At-Risk_, and _Silently Abandoned_.
- [x] **06_analyze_and_visualize.py**: Built statistical test suites ($\chi^2$, Cramér's V, Odds Ratios, Multivariate Logistic Regression) and generated 300 DPI publication plots.

### B. Empirical Dataset Assets (`data/`)

- [x] `top_packages.csv` (1,000 seed packages with download rank)
- [x] `dependencies.csv` (3,022 parent-child dependency edges with depth indicators)
- [x] `package_metadata.csv` (1,303 packages with author, homepage, repo URL, license, latest release)
- [x] `github_metadata.csv` (commit recency, stars, archiving flags)
- [x] `vulnerabilities.csv` (vulnerability counts, critical/high severity flags, advisory IDs)
- [x] `classified_packages.csv` (consolidated analytical dataset with health classifications)
- [x] `statistics_summary.csv` (high-level empirical metrics)

### C. Key Scientific Findings

- [x] **RQ1 (Pervasive Single-Maintainer Risk):** **75.9%** (989 / 1,303) of dependencies rely on a solo maintainer, revealing widespread bus factor fragility across mission-critical Python deployments.
- [x] **RQ2 (Extent of Silent Abandonment):** **14.2%** (185 / 1,303) are silently abandoned ($\ge 18$ months inactive); an additional **66.1%** (861 / 1,303) are in an at-risk state. Only **19.7%** (257 / 1,303) meet healthy, team-backed criteria.
- [x] **RQ3 (The Vulnerability Reporting Paradox):** 206 packages harbor documented vulnerabilities ($\chi^2 = 8.0513, p = 0.00455, \text{OR} = 0.60$). Logistic regression ($\beta = -1.4901, p = 0.0037$) uncovered the **"Undiscovered Defect" Blindspot**: abandoned projects log fewer official CVEs not because they are secure, but because dormant repositories lack active maintainers to review disclosure reports and publish security advisories.

### D. Publication & Manuscript Artifacts (`paper/`)

- [x] **Full Markdown Manuscript (`paper/paper.md`)**: Comprehensive academic paper with Abstract, Introduction, Background, Methodology, Results (RQ1–RQ3), Discussion, Threats to Validity, and References.
- [x] **IEEE / ACM LaTeX Source (`paper/paper.tex`)**: Formatted using the standard `IEEEtran` conference/transactions class with `booktabs` tables, equations, finding callouts, and clean figure inclusions.
- [x] **BibTeX Database (`paper/references.bib`)**: 10 primary peer-reviewed literature citations and database references with DOIs.
- [x] **HTML Web Version (`paper/index.html`)**: Complete standalone academic paper viewer with styling, embedded charts, and responsive print support.
- [x] **Camera-Ready PDF (`paper/paper.pdf`)**: Compiled high-resolution PDF artifact ready for immediate reading and distribution.

### E. Code Quality & Repository State

- [x] Clean Git working tree on `main` branch.
- [x] Comprehensive documentation in `README.md` with step-by-step reproduction guide.
- [x] Virtual environment `.venv` with `requirements.txt` validated.

---

## 3. What Has to Be Done Next (Actionable Roadmap)

```
+-------------------------------------------------------------------------+
|                              ROADMAP PHASES                             |
+-------------------------------------------------------------------------+
|  Phase 1: Pre-Submission & Dissemination (Weeks 1–2)                    |
|    • Zenodo DOI deposit & preprint submission (arXiv)                   |
|    • Target venue selection (MSR / ICSE / IEEE S&P / USENIX / TSE)      |
|    • Overleaf / LaTeX compiler double-check                             |
|                               |                                         |
|                               v                                         |
|  Phase 2: Open Source Tooling & Community Release (Weeks 3–4)           |
|    • Publish GitHub repository with GitHub Actions CI pipeline          |
|    • Release 'pypi-health' CLI tool for developers                      |
|    • Engage PyPI Packaging Working Group (PEP 541 discussions)          |
|                               |                                         |
|                               v                                         |
|  Phase 3: Extended Empirical Research (Months 2–3)                      |
|    • Dynamic call-graph tracing (dead code vs executed vulnerabilities) |
|    • Longitudinal tracking (monthly automated ingestion)                |
|    • LLM agent benchmarking for automated dependency replacement        |
+-------------------------------------------------------------------------+
```

### Phase 1: Pre-Submission & Dissemination

1. **Zenodo Archive & DOI Registration (COMPLETED):**
    - Packaged replication bundle and minted permanent DOI: [`10.5281/zenodo.23007343`](https://doi.org/10.5281/zenodo.23007343).
    - Synchronized permanent DOI across `paper.tex`, `paper.md`, `index.html`, and `README.md`.
2. **Preprint Submission (arXiv / OpenReview):**
    - Upload `paper.tex` + `references.bib` + `figures/` to arXiv under the `cs.SE` (Software Engineering) and `cs.CR` (Cryptography and Security) categories.
3. **Conference / Journal Venue Selection:**
    - **Top Conference Venues:**
        - _ACM/IEEE International Conference on Software Engineering (ICSE)_
        - _IEEE/ACM International Conference on Mining Software Repositories (MSR)_
        - _ACM Conference on Computer and Communications Security (CCS) / ACM ASIACCS_
        - _IEEE Symposium on Security and Privacy (S&P)_
    - **Journal Venues:**
        - _IEEE Transactions on Software Engineering (TSE)_
        - _ACM Transactions on Software Engineering and Methodology (TOSEM)_
        - _Empirical Software Engineering (EMSE)_
4. **Overleaf Synchronization:**
    - Import `paper/` into Overleaf for collaborative reviewing and real-time template switching (ACM Primary Article Template vs. IEEEtran).

### Phase 2: Open Source Ecosystem Tooling

1. **GitHub Repository Launch:**
    - Add remote origin (`git remote add origin https://github.com/raihan-sifat/pypi-dependency-health-study.git`) and push `main` branch.
    - Configure a GitHub Actions workflow to run linting and pipeline reproduction tests automatically.
2. **`pypi-health` CLI Tool:**
    - Package the classification logic (`scripts/05_classify_packages.py`) into a lightweight CLI tool (`pip install pypi-health-audit`) that developers can run inside any Python project or CI pipeline (`pypi-health audit requirements.txt`) to flag silent abandonment in transitive dependencies.
3. **Policy Proposal for PyPI & PSF:**
    - Draft a discussion post for the Python Discourse / Packaging forum recommending automated dormancy badges on PyPI for packages exceeding 18 months without a release.

### Phase 3: Research Extensions

1. **Dynamic Runtime Reachability:**
    - Instrument execution of top 100 downstream applications to test whether dormant/unmaintained functions in abandoned transitive libraries are reachable at runtime or constitute inert dead code.
2. **Longitudinal Ecosystem Tracking:**
    - Set up a scheduled monthly workflow tracking how abandonment rates change over time and measuring package transition times from "Healthy" $\to$ "At-Risk" $\to$ "Abandoned".
3. **Automated Replacement Evaluation:**
    - Benchmark state-of-the-art LLM code agents on automatically refactoring codebases to replace abandoned transitive libraries with modern maintained equivalents.
