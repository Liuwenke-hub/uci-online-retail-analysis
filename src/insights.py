# -*- coding: utf-8 -*-
"""数据绑定的具体洞察：最高取消率国家、最赚钱海外市场、客群贡献集中度等。"""
import pandas as pd
import numpy as np


def country_cancel(sales, cancels):
    """计算各国家（订单口径）取消/退款率，返回最高取消率国家（剔除单量过小）。"""
    sc = sales.groupby("Country")["InvoiceNo"].nunique()
    cc = cancels.groupby("Country")["InvoiceNo"].nunique()
    rate = (cc / (sc + cc) * 100).dropna().sort_values(ascending=False)
    big = rate[sc[rate.index] >= 50]  # 仅看订单量≥50的国家，避免小样本噪声
    if len(big):
        top = big.index[0]
        return dict(top_country=str(top), top_cancel_rate=round(float(big.iloc[0]), 1),
                    uk_cancel_rate=round(float(rate.get("United Kingdom", np.nan)), 1))
    return dict(top_country="-", top_cancel_rate=0.0, uk_cancel_rate=0.0)


def overseas_value(sales, top_n=5):
    """海外市场（剔除UK）按 GMV 排序，返回客单价最高的市场。"""
    g = sales[sales["Country"] != "United Kingdom"].groupby("Country").agg(
        GMV=("Revenue", "sum"), Orders=("InvoiceNo", "nunique"), Buyers=("CustomerID", "nunique"))
    g["AOV"] = g["GMV"] / g["Orders"]
    g = g.sort_values("GMV", ascending=False).head(top_n)
    best_aov = g.sort_values("AOV", ascending=False).head(1)
    return dict(best_aov_country=str(best_aov.index[0]),
                best_aov=round(float(best_aov["AOV"].iloc[0]), 2),
                overseas=round(float(g["GMV"].sum()), 2))


def concentration(seg_stat):
    """头部客群贡献集中度（帕累托）。"""
    s = seg_stat.sort_values("贡献占比", ascending=False)
    top2 = s.head(2)["贡献占比"].sum()
    return dict(top2_contrib=round(float(top2), 1),
                top_segment=str(s.iloc[0]["Segment"]),
                top_segment_contrib=round(float(s.iloc[0]["贡献占比"]), 1))
