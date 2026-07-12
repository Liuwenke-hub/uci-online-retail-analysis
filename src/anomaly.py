# -*- coding: utf-8 -*-
"""异常检测：先去除周内/月度季节性，再做稳健 z-score。"""
import pandas as pd
import numpy as np
from src import config as C


def detect(daily, win=28, z_thr=2.5):
    """对日度 GMV 做季节性去趋势后的异常检测。

    步骤：
      1) 计算全局日均值、星期因子（各星期几/全局均值）、月份因子
      2) expected = 全局均值 × 星期因子 × 月份因子
      3) residual = actual - expected
      4) 对 residual 做 28 日滚动中位数 + 稳健 z-score（|z|≥阈值标记）

    这样可避免把「周末单量低」这类规律误判为异常。
    """
    d = daily.copy().sort_values("Date")
    d["dow"] = d["Date"].dt.dayofweek
    d["ym"] = d["Date"].dt.to_period("M").astype(str)
    global_mean = d["GMV"].mean()
    dow_factor = d.groupby("dow")["GMV"].mean() / global_mean
    ym_factor = d.groupby("ym")["GMV"].mean() / global_mean
    d["expected"] = global_mean * d["dow"].map(dow_factor) * d["ym"].map(ym_factor)
    d["residual"] = d["GMV"] - d["expected"]

    d["res_ma"] = d["residual"].rolling(win, min_periods=7, center=True).median()
    d["res_std"] = d["residual"].rolling(win, min_periods=7, center=True).std()
    d["z"] = (d["residual"] - d["res_ma"]) / d["res_std"]
    anom = d[d["z"].abs() >= z_thr].copy()
    return d, anom


def naive_detect(daily, win=28, z_thr=2.5):
    """对照方法：不做季节性调整的直接 z-score（用于对比说明）。"""
    d = daily.copy().sort_values("Date")
    d["gmv_ma"] = d["GMV"].rolling(win, min_periods=7, center=True).median()
    d["gmv_std"] = d["GMV"].rolling(win, min_periods=7, center=True).std()
    d["z"] = (d["GMV"] - d["gmv_ma"]) / d["gmv_std"]
    return d[d["z"].abs() >= z_thr]
