# -*- coding: utf-8 -*-
"""路径与全局常量配置（集中管理，避免硬编码）。"""
import os

# 项目根目录 = src 的父目录
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "OnlineRetail.csv")
OUT = os.path.join(ROOT, "outputs")
FIGS = os.path.join(OUT, "figs")          # plotly HTML 片段
IMGS = os.path.join(OUT, "images")        # README 静态截图 PNG
STATS = os.path.join(OUT, "stats.json")

for _d in (OUT, FIGS, IMGS):
    os.makedirs(_d, exist_ok=True)

# 主题色板
C = dict(primary="#2563eb", accent="#0ea5e9", green="#16a34a", red="#dc2626",
         amber="#d97706", purple="#7c3aed", slate="#475569", teal="#0d9488")
PALETTE = ["#2563eb", "#0ea5e9", "#16a34a", "#d97706", "#7c3aed", "#dc2626",
           "#0d9488", "#db2777", "#65a30d", "#475569"]

# 业务假设（在报告中显式标注，便于评审质疑/调整）
MARGIN_ASSUMPTION = 0.30     # 零售业贡献毛利率假设 30%
MONTHLY_DISCOUNT = 0.01      # 月度折现率 1%（年化约 12%）
CHURN_RECENCY_DAYS = 180     # 流失定义：快照日往前 180 天无交易
