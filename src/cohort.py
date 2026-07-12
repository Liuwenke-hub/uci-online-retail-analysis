# -*- coding: utf-8 -*-
"""Cohort 留存 + 简化版 LTV（含折现与毛利率假设）。"""
import pandas as pd
import numpy as np
from src import config as C


def build_cohort(sales):
    """按首购月份划分 Cohort，计算留存矩阵与累计人均收入。"""
    sales = sales.copy()
    first = sales.groupby("CustomerID")["InvoiceDate"].min().dt.to_period("M")
    sales["Cohort"] = sales["CustomerID"].map(first).astype(str)
    sales["OrderPeriod"] = sales["InvoiceDate"].dt.to_period("M").astype(str)

    def midx(p):
        y, m = map(int, p.split("-"))
        return y * 12 + m
    sales["CohortIndex"] = sales.apply(lambda r: midx(r["OrderPeriod"]) - midx(r["Cohort"]), axis=1)

    cohort_users = sales.groupby(["Cohort", "CohortIndex"])["CustomerID"].nunique().reset_index()
    retention = cohort_users.pivot(index="Cohort", columns="CohortIndex", values="CustomerID")
    cohort_size = retention[0]
    ret_pct = retention.divide(cohort_size, axis=0) * 100

    cohort_rev = sales.groupby(["Cohort", "CohortIndex"])["Revenue"].sum().reset_index()
    rev_pivot = cohort_rev.pivot(index="Cohort", columns="CohortIndex", values="Revenue")
    ltv_cum = rev_pivot.cumsum(axis=1).divide(cohort_size, axis=0)  # 累计人均收入

    return retention, ret_pct, ltv_cum, cohort_size


def ltv_with_assumptions(ltv_cum):
    """在累计人均收入基础上，给出两种「更接近真 LTV」的视图：

    1) 折现 LTV：按月度折现率贴现未来月份贡献
    2) 毛利 LTV：收入 × 毛利率假设
    两者均为简化口径，假设在报告中显式标注。
    """
    disc = (1 + C.MONTHLY_DISCOUNT) ** np.arange(ltv_cum.shape[1])
    ltv_disc = ltv_cum.divide(disc, axis=1)
    ltv_margin = ltv_cum * C.MARGIN_ASSUMPTION
    return ltv_disc, ltv_margin


def m1_insight(ret_pct):
    """找出 M1 留存最低 / 最高的 cohort（数据绑定的具体洞察）。"""
    m1 = ret_pct[1].dropna()
    low = m1.idxmin()
    high = m1.idxmax()
    return dict(low_cohort=str(low), low_m1=round(float(m1.min()), 1),
                high_cohort=str(high), high_m1=round(float(m1.max()), 1))
