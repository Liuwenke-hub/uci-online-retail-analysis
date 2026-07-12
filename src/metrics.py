# -*- coding: utf-8 -*-
"""核心指标看板（按月）、分布与 Top 维度分析。"""
import pandas as pd
import numpy as np
from src import config as C


def monthly_metrics(sales, cancels):
    """月度核心指标：GMV / 订单数 / 活跃买家 / 客单价 / 复购率 / 取消率。"""
    sales = sales.copy()
    sales["YM"] = sales["InvoiceDate"].dt.to_period("M").astype(str)
    cancels = cancels.copy()
    cancels["YM"] = cancels["InvoiceDate"].dt.to_period("M").astype(str)

    g = sales.groupby("YM")
    monthly = pd.DataFrame({
        "GMV": g["Revenue"].sum(),
        "Orders": g["InvoiceNo"].nunique(),
        "Buyers": g["CustomerID"].nunique(),
    })
    monthly["AOV"] = monthly["GMV"] / monthly["Orders"]
    cm = cancels.groupby("YM")["Revenue"].sum().abs()
    monthly["RefundAmt"] = cm.reindex(monthly.index).fillna(0)
    monthly["CancelRate"] = monthly["RefundAmt"] / monthly["GMV"] * 100
    monthly = monthly.reset_index()

    def repurchase_rate(sub):
        oc = sub.groupby("CustomerID")["InvoiceNo"].nunique()
        return (oc >= 2).mean() * 100
    monthly_rep = sales.groupby("YM").apply(repurchase_rate).reindex(monthly["YM"]).values
    monthly_rep = [round(float(x), 2) for x in monthly_rep]

    oc_all = sales.groupby("CustomerID")["InvoiceNo"].nunique()
    overall_repurchase = round(float((oc_all >= 2).mean() * 100), 2)

    summary = dict(
        gmv_total=round(float(sales["Revenue"].sum()), 2),
        n_orders=int(sales["InvoiceNo"].nunique()),
        n_customers=int(sales["CustomerID"].nunique()),
        aov=round(float(sales["Revenue"].sum()) / sales["InvoiceNo"].nunique(), 2),
        overall_repurchase=overall_repurchase,
        n_countries=int(sales["Country"].nunique()),
        refund_total=round(float(cancels["Revenue"].sum()), 2),
    )
    return monthly, monthly_rep, summary


def distributions(sales):
    """订单金额分布（截尾99）、星期×小时热力、Top 国家/商品。"""
    order_val = sales.groupby("InvoiceNo")["Revenue"].sum()
    ov = order_val[order_val <= order_val.quantile(0.99)]

    sales = sales.copy()
    sales["dow"] = sales["InvoiceDate"].dt.dayofweek
    sales["hour"] = sales["InvoiceDate"].dt.hour
    heat = sales.groupby(["dow", "hour"])["Revenue"].sum().reset_index()
    pivot = heat.pivot(index="dow", columns="hour", values="Revenue").fillna(0)

    cc_gmv = sales.groupby("Country")["Revenue"].sum().sort_values(ascending=False)
    prod = sales.groupby("Description").agg(GMV=("Revenue", "sum"), Qty=("Quantity", "sum")).sort_values("GMV", ascending=False)

    return ov, pivot, cc_gmv, prod, round(float(order_val.median()), 2)


def missing_bias(raw_full):
    """缺失 CustomerID 偏差分析：对比原始数据中「有ID(用户级)」vs「无ID(游客级)」的客单价/取消率/国家结构。

    注意：传入的是含全部行的 raw_full（含缺失 CustomerID 的行），清洗后的 clean_full 已剔除缺失行。
    """
    has = raw_full[raw_full["CustomerID"].notna() & raw_full["is_sales"]]
    nos = raw_full[raw_full["CustomerID"].isna() & raw_full["is_sales"]]
    has_orders = has.groupby("InvoiceNo")["Revenue"].sum()
    nos_orders = nos.groupby("InvoiceNo")["Revenue"].sum()
    return dict(
        has_orders=int(len(has_orders)),
        nos_orders=int(len(nos_orders)),
        has_aov=round(float(has_orders.mean()), 2),
        nos_aov=round(float(nos_orders.mean()), 2),
        has_top_country=has["Country"].value_counts().head(1).index[0],
        nos_top_country=nos["Country"].value_counts().head(1).index[0],
        has_cancel_share=round(float((~has["is_cancel"]).mean() * 0 + has["is_cancel"].mean() * 100), 2),
        nos_cancel_share=round(float(nos["is_cancel"].mean() * 100), 2),
    )
