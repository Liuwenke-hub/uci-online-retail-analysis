# -*- coding: utf-8 -*-
"""用 matplotlib 生成 README 静态截图（outputs/images/*.png）。

不依赖 kaleido / plotly 导出，纯 matplotlib 渲染，保证任意环境可复现。
图表标签使用英文以避免缺少中文字体时的乱码；交互版中文图表见 outputs/report.html。
"""
import os
import json
import warnings
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

from src import config as C

warnings.filterwarnings("ignore", category=UserWarning)  # 忽略字体/布局告警
plt.rcParams.update({
    "figure.dpi": 110, "font.size": 11,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linestyle": "--",
    "font.family": "DejaVu Sans", "axes.unicode_minus": False,
})
BLUE = "#2563eb"; ACCENT = "#0ea5e9"; GREEN = "#16a34a"; RED = "#dc2626"
AMBER = "#d97706"; PURPLE = "#7c3aed"; TEAL = "#0d9488"; SLATE = "#475569"

# RFM 分群中文→英文（PNG 用，避免缺中文字体时的方框）
SEG_EN = {"冠军客户": "Champions", "忠诚客户": "Loyal", "新客户": "New",
          "高潜力客户": "High-Potential", "流失预警": "At-Risk", "重要挽回": "Win-Back",
          "已流失/沉睡": "Dormant", "一般客户": "General"}
EN_WEEK = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def _save(fig, name):
    path = os.path.join(C.IMGS, name + ".png")
    fig.tight_layout()
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(f"  PNG -> {name}.png")


def main():
    S = json.load(open(C.STATS, encoding="utf-8"))
    os.makedirs(C.IMGS, exist_ok=True)

    # 1. GMV trend
    mo = S["monthly"]
    x = [m["YM"] for m in mo]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.bar(x, [m["GMV"] / 1e6 for m in mo], color=BLUE, alpha=0.85, label="GMV (£M)")
    ax.set_ylabel("GMV (£M)", color=BLUE)
    ax2 = ax.twinx(); ax2.grid(False)
    ax2.plot(x, [m["Orders"] for m in mo], color=AMBER, marker="o", lw=2.5, label="Orders")
    ax2.set_ylabel("Orders", color=AMBER)
    ax.set_title("Monthly GMV & Order Count")
    ax.tick_params(axis="x", rotation=45)
    _save(fig, "gmv_trend")

    # 2. RFM segments grouped bar
    segs = S["rfm_segments"]
    labels = [SEG_EN.get(s["Segment"], s["Segment"]) for s in segs]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    y = np.arange(len(labels)); h = 0.38
    ax.barh(y + h/2, [s["人数占比"] for s in segs], h, color=SLATE, alpha=0.6, label="% of Customers")
    ax.barh(y - h/2, [s["贡献占比"] for s in segs], h, color=BLUE, label="% of GMV")
    ax.set_yticks(y); ax.set_yticklabels(labels)
    ax.invert_yaxis(); ax.set_xlabel("Share (%)"); ax.legend()
    ax.set_title("RFM Segments: Customers vs GMV Contribution")
    _save(fig, "rfm_segments")

    # 3. RFM bubble
    fig, ax = plt.subplots(figsize=(8, 5))
    sizes = [max(40, s["人数"] / 8) for s in segs]
    cols = plt.cm.tab10(np.linspace(0, 1, len(segs)))
    ax.scatter([s["平均F"] for s in segs], [s["平均M"] / 100 for s in segs],
              s=sizes, c=cols, alpha=0.7, edgecolors="white")
    for s in segs:
        ax.annotate(SEG_EN.get(s["Segment"], s["Segment"]), (s["平均F"], s["平均M"] / 100), fontsize=8, ha="center")
    ax.set_xlabel("Avg Frequency"); ax.set_ylabel("Avg Monetary (£100)")
    ax.set_title("RFM Segments Bubble (Freq × Monetary × Size)")
    _save(fig, "rfm_bubble")

    # 4. Time heatmap
    hp = np.array(S["heat_pivot"])
    fig, ax = plt.subplots(figsize=(9, 3.6))
    im = ax.imshow(hp, aspect="auto", cmap="Blues")
    ax.set_xticks(range(len(S["heat_cols"]))); ax.set_xticklabels(S["heat_cols"], rotation=45, fontsize=8)
    wk = EN_WEEK[:len(S["heat_rows"])]
    ax.set_yticks(range(len(wk))); ax.set_yticklabels(wk)
    ax.set_title("Order Time Heatmap (Weekday × Hour, GMV)")
    fig.colorbar(im, ax=ax, fraction=0.025, label="GMV")
    _save(fig, "heatmap_time")

    # 5. Cohort retention
    rp = np.array(S["ret_pct"]); cols = S["cohort_cols"]; rows = S["cohort_rows"]
    fig, ax = plt.subplots(figsize=(9, 5))
    im = ax.imshow(rp, aspect="auto", cmap="Blues", vmin=0, vmax=100)
    ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, rotation=45, fontsize=8)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(rows, fontsize=8)
    for i in range(rp.shape[0]):
        for j in range(rp.shape[1]):
            if not np.isnan(rp[i, j]):
                ax.text(j, i, f"{rp[i,j]:.0f}", ha="center", va="center", fontsize=6)
    ax.set_title("Cohort Retention Rate (%)")
    fig.colorbar(im, ax=ax, fraction=0.025, label="%")
    _save(fig, "cohort_retention")

    # 6. Cohort LTV
    lv = np.array(S["ltv_cum"])
    fig, ax = plt.subplots(figsize=(9, 5))
    im = ax.imshow(lv, aspect="auto", cmap="Greens")
    ax.set_xticks(range(len(cols))); ax.set_xticklabels(cols, rotation=45, fontsize=8)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(rows, fontsize=8)
    ax.set_title("Cohort Cumulative LTV per Capita (£)")
    fig.colorbar(im, ax=ax, fraction=0.025, label="£/capita")
    _save(fig, "cohort_ltv")

    # 7. Anomaly
    a = S["anomaly_series"]
    fig, ax = plt.subplots(figsize=(9, 4))
    ax.plot(a["dates"], a["gmv"], color=BLUE, lw=1.2, label="Daily GMV")
    ax.plot(a["dates"], a["expected"], color=TEAL, lw=2, ls="--", label="Seasonal Expected")
    idx = a["anom_idx"]
    ax.scatter([a["dates"][i] for i in idx], [a["gmv"][i] for i in idx],
               color=RED, marker="x", s=60, label="Anomaly (|z|≥2.5)")
    ax.set_title("Daily GMV Anomaly Detection (seasonality-adjusted)")
    ax.legend(fontsize=8)
    _save(fig, "anomaly")

    # 8. Predict metrics
    ch, cl = S["churn"], S["clv"]
    fig, ax = plt.subplots(figsize=(7, 4))
    names = ["Churn AUC", "Churn Acc", "CLV R²"]
    vals = [ch["auc"], ch["accuracy"], cl["r2"]]
    ax.bar(names, vals, color=[RED, AMBER, GREEN])
    for i, v in enumerate(vals):
        ax.text(i, v + 0.02, f"{v:.3f}", ha="center", fontweight="bold")
    ax.set_ylim(0, 1.08); ax.set_ylabel("Score")
    ax.set_title("Predictive Model Evaluation")
    _save(fig, "predict_metrics")

    print("静态截图已生成至", C.IMGS)


if __name__ == "__main__":
    main()
