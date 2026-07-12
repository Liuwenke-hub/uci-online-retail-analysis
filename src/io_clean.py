# -*- coding: utf-8 -*-
"""数据加载、编码修复、清洗与质量审计。"""
import pandas as pd
import numpy as np
from src import config as C


def load_raw():
    """加载原始 CSV。

    关键坑：原始文件含 £ 符号，必须用 latin-1 读取（utf-8 会在 0xa3 处报解码错误）。
    """
    df = pd.read_csv(C.DATA, dtype={"InvoiceNo": str, "StockCode": str}, encoding="latin-1")
    df.columns = [c.strip() for c in df.columns]
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], format="%m/%d/%Y %H:%M", errors="coerce")
    df["is_cancel"] = df["InvoiceNo"].str.startswith("C", na=False)
    return df


def profile(df):
    """生成字段画像（类型/唯一值/缺失率），供数据字典使用。"""
    raw = len(df)
    prof = []
    for col in df.columns:
        s = df[col]
        nn = int(s.notna().sum())
        prof.append(dict(col=col, dtype=str(s.dtype), non_null=nn,
                         miss=raw - nn, miss_pct=round((raw - nn) / raw * 100, 2),
                         nunique=int(s.nunique(dropna=True))))
    return prof


def audit(df):
    """质量审计：缺失率、异常值、取消单、重复、特殊编码。"""
    raw = len(df)
    a = {}
    a["cancel_rows"] = int(df["is_cancel"].sum())
    a["cancel_pct"] = round(df["is_cancel"].mean() * 100, 2)
    a["qty_neg"] = int((df["Quantity"] < 0).sum())
    a["qty_zero"] = int((df["Quantity"] == 0).sum())
    a["price_neg"] = int((df["UnitPrice"] < 0).sum())
    a["price_zero"] = int((df["UnitPrice"] == 0).sum())
    a["cust_missing"] = int(df["CustomerID"].isna().sum())
    a["cust_missing_pct"] = round(df["CustomerID"].isna().mean() * 100, 2)
    a["desc_missing"] = int(df["Description"].isna().sum())
    a["dup_rows"] = int(df.duplicated().sum())
    a["dup_pct"] = round(df.duplicated().mean() * 100, 2)
    for col in ["Quantity", "UnitPrice"]:
        q = df[col].describe(percentiles=[.01, .25, .5, .75, .99]).to_dict()
        a[col + "_stats"] = {k: round(float(v), 3) for k, v in q.items()}
    special = df[df["StockCode"].str.match(r"^[A-Za-z]", na=False)]["StockCode"].value_counts().head(12)
    a["special_codes"] = {str(k): int(v) for k, v in special.items()}
    return a


def clean(df):
    """五步可回滚清洗，返回 (clean_full, sales, cancels, steps)。

    清洗策略全部以「打标签 / 条件过滤」实现，原始 df 不被破坏，可完整回滚。
    """
    steps = []
    n0 = len(df)
    clean = df.drop_duplicates()
    steps.append(("去除完全重复记录", n0 - len(clean)))
    n0 = len(clean)

    clean_cust = clean.dropna(subset=["CustomerID"]).copy()
    drop_cust_missing = n0 - len(clean_cust)
    clean_cust["CustomerID"] = clean_cust["CustomerID"].astype(int).astype(str)

    sales = clean_cust[~clean_cust["is_cancel"]].copy()
    cancels = clean_cust[clean_cust["is_cancel"]].copy()

    before = len(sales)
    sales = sales[(sales["Quantity"] > 0) & (sales["UnitPrice"] > 0)].copy()
    steps.append(("剔除非正数量/单价(有效销售)", before - len(sales)))

    sales["Revenue"] = sales["Quantity"] * sales["UnitPrice"]
    cancels["Revenue"] = cancels["Quantity"] * cancels["UnitPrice"]

    clean_full = clean_cust.copy()
    clean_full["Revenue"] = clean_full["Quantity"] * clean_full["UnitPrice"]
    clean_full["is_sales"] = ~clean_full["is_cancel"] & (clean_full["Quantity"] > 0) & (clean_full["UnitPrice"] > 0)

    return clean_full, sales, cancels, steps, drop_cust_missing
