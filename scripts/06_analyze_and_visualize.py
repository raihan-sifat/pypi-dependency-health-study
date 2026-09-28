"""
Script 06 — Statistical analysis and visualization for research paper.

Computes metrics for RQ1, RQ2, and RQ3:
  - Chi-squared test of independence
  - Odds ratios and Cramér's V
  - Logistic regression
  - Generates 4 publication-quality figures (300 DPI)

Outputs:
  data/statistics_summary.csv
  data/detailed_statistics.csv
  figures/fig1_maintainer_distribution.png
  figures/fig2_health_distribution.png
  figures/fig3_vulnerability_analysis.png
  figures/fig4_vuln_count_boxplot.png
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
from scipy import stats
import statsmodels.api as sm
from config import DATA_DIR, FIGURES_DIR, setup_logging

matplotlib.rcParams.update({
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "font.size": 10,
    "axes.titlesize": 12,
    "axes.labelsize": 11,
    "font.family": "sans-serif",
})

log = setup_logging("06_analyze_and_visualize")


def run_analysis():
    class_path = DATA_DIR / "classified_packages.csv"
    deps_path = DATA_DIR / "dependencies.csv"

    if not class_path.exists():
        log.error("Run 05_classify_packages.py first!")
        return

    df = pd.read_csv(class_path)
    deps_df = pd.read_csv(deps_path) if deps_path.exists() else pd.DataFrame()

    total_pkgs = len(df)
    log.info("Analyzing %d classified packages...", total_pkgs)

    # RQ1: Single-maintainer analysis
    single_count = df["is_single_maintainer"].sum()
    single_pct = round(100 * single_count / total_pkgs, 2)

    # RQ2: Silent abandonment
    status_counts = df["health_status"].value_counts()
    abandoned_count = status_counts.get("silently_abandoned", 0)
    abandoned_pct = round(100 * abandoned_count / total_pkgs, 2)
    at_risk_count = status_counts.get("at_risk", 0)
    at_risk_pct = round(100 * at_risk_count / total_pkgs, 2)
    healthy_count = status_counts.get("healthy", 0)
    healthy_pct = round(100 * healthy_count / total_pkgs, 2)

    # RQ3: Association between Abandonment & Vulnerabilities
    df["has_vuln"] = df["vuln_count"] > 0
    df["is_abandoned_or_risk"] = df["health_status"].isin(["at_risk", "silently_abandoned"])

    # Contingency Table
    ct = pd.crosstab(df["is_abandoned_or_risk"], df["has_vuln"])
    chi2, p_val, dof, ex = stats.chi2_contingency(ct)
    n = len(df)
    cramers_v = np.sqrt(chi2 / (n * 1))

    # Odds ratio
    if ct.shape == (2, 2) and (ct.values > 0).all():
        odds_ratio = (ct.iloc[1, 1] * ct.iloc[0, 0]) / (ct.iloc[1, 0] * ct.iloc[0, 1])
    else:
        odds_ratio = 1.0

    log.info("RQ1: Single-maintainer packages: %d (%.1f%%)", single_count, single_pct)
    log.info("RQ2: Silently abandoned: %d (%.1f%%) | At-risk: %d (%.1f%%)", abandoned_count, abandoned_pct, at_risk_count, at_risk_pct)
    log.info("RQ3: Chi2 = %.4f, p = %.6e, Cramér's V = %.4f, Odds Ratio = %.2f", chi2, p_val, cramers_v, odds_ratio)

    # Logistic Regression
    try:
        df["abandoned_flag"] = (df["health_status"] == "silently_abandoned").astype(int)
        df["at_risk_flag"] = (df["health_status"] == "at_risk").astype(int)
        df["single_maint_flag"] = df["is_single_maintainer"].astype(int)
        X = sm.add_constant(df[["abandoned_flag", "at_risk_flag", "single_maint_flag"]])
        y = df["has_vuln"].astype(int)
        logit_model = sm.Logit(y, X).fit(disp=0)
        logit_summary = logit_model.summary2().as_text()
        log.info("Logistic regression converged:\n%s", logit_summary)
    except Exception as e:
        log.warning("Logistic regression warning: %s", e)

    # Summary table
    summary_data = {
        "Metric": [
            "Total Packages Analysed",
            "Direct and Transitive Dependencies",
            "Single-Maintainer Packages",
            "Silently Abandoned (>=18 mo inactive)",
            "At-Risk (12-18 mo or single maintainer)",
            "Healthy Maintenance State",
            "Packages with Known Vulnerabilities",
            "Chi-Square Test (Abandonment vs Vuln)",
            "p-value",
            "Odds Ratio"
        ],
        "Value": [
            str(total_pkgs),
            str(len(deps_df)),
            f"{single_count} ({single_pct}%)",
            f"{abandoned_count} ({abandoned_pct}%)",
            f"{at_risk_count} ({at_risk_pct}%)",
            f"{healthy_count} ({healthy_pct}%)",
            f"{df['has_vuln'].sum()} ({round(100*df['has_vuln'].mean(), 1)}%)",
            f"{chi2:.4f}",
            f"{p_val:.2e}",
            f"{odds_ratio:.2f}"
        ]
    }
    pd.DataFrame(summary_data).to_csv(DATA_DIR / "statistics_summary.csv", index=False)

    # ── Figures Generation ───────────────────────────────────────────────
    # Fig 1: Maintainer Distribution
    fig, ax = plt.subplots(figsize=(6, 4))
    sizes = [single_count, total_pkgs - single_count]
    ax.pie(sizes, labels=["Single Maintainer", "Multi/Team Maintainer"],
           autopct="%1.1f%%", colors=["#e74c3c", "#2ecc71"], startangle=140, explode=(0.06, 0))
    ax.set_title("Single vs. Multi-Maintainer Dependency Proportion (RQ1)")
    fig.savefig(FIGURES_DIR / "fig1_maintainer_distribution.png")
    plt.close(fig)

    # Fig 2: Health Status Distribution
    fig, ax = plt.subplots(figsize=(7, 4.5))
    categories = ["Healthy", "At-Risk", "Silently Abandoned"]
    values = [healthy_count, at_risk_count, abandoned_count]
    colors = ["#2ecc71", "#f39c12", "#c0392b"]
    bars = ax.bar(categories, values, color=colors, width=0.55)
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + max(values)*0.015,
                f"{height} ({round(100*height/total_pkgs, 1)}%)", ha="center", va="bottom", fontsize=10)
    ax.set_ylabel("Number of Packages")
    ax.set_title("Dependency Health State Classification (RQ2)")
    ax.set_ylim(0, max(values) * 1.15)
    fig.savefig(FIGURES_DIR / "fig2_health_distribution.png")
    plt.close(fig)

    # Fig 3: Vulnerability Rate by Health Status
    fig, ax = plt.subplots(figsize=(7, 4.5))
    rates = df.groupby("health_status")["has_vuln"].mean() * 100
    stat_order = ["healthy", "at_risk", "silently_abandoned"]
    rates = [rates.get(s, 0) for s in stat_order]
    bars = ax.bar(["Healthy", "At-Risk", "Silently Abandoned"], rates, color=["#27ae60", "#e67e22", "#d35400"], width=0.55)
    for bar in bars:
        h = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., h + 0.5, f"{h:.1f}%", ha="center", va="bottom", fontsize=10, fontweight="bold")
    ax.set_ylabel("Vulnerability Prevalence (%)")
    ax.set_title("Vulnerability Occurrence by Dependency Health Status (RQ3)")
    ax.set_ylim(0, max(rates) * 1.25 if max(rates) > 0 else 10)
    fig.savefig(FIGURES_DIR / "fig3_vulnerability_analysis.png")
    plt.close(fig)

    # Fig 4: Boxplot of Vulnerability Counts
    fig, ax = plt.subplots(figsize=(7, 4.5))
    vuln_sub = df[df["vuln_count"] > 0]
    if len(vuln_sub) > 0:
        sns.boxplot(x="health_status", y="vuln_count", data=vuln_sub, order=["healthy", "at_risk", "silently_abandoned"],
                    palette=["#2ecc71", "#f39c12", "#e74c3c"], ax=ax)
        ax.set_xticklabels(["Healthy", "At-Risk", "Silently Abandoned"])
        ax.set_ylabel("Known Vulnerability Count")
        ax.set_title("Severity & Defect Distribution Across Health States")
    fig.savefig(FIGURES_DIR / "fig4_vuln_count_boxplot.png")
    plt.close(fig)

    log.info("Analysis and 4 publication charts successfully generated!")


if __name__ == "__main__":
    run_analysis()
