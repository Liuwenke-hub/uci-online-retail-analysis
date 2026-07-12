# -*- coding: utf-8 -*-
"""RFM 分群（规则法）+ K-Means 聚类验证。"""
import pandas as pd
import numpy as np
from src import config as C


def build_rfm(sales, snapshot=None):
    """计算 R/F/M 并做五分位打分（参数依据见报告）。"""
    if snapshot is None:
        snapshot = sales["InvoiceDate"].max() + pd.Timedelta(days=1)
    rfm = sales.groupby("CustomerID").agg(
        Recency=("InvoiceDate", lambda x: (snapshot - x.max()).days),
        Frequency=("InvoiceNo", "nunique"),
        Monetary=("Revenue", "sum"),
    ).reset_index()
    rfm["R"] = pd.qcut(rfm["Recency"], 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["F"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["M"] = pd.qcut(rfm["Monetary"], 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["RFM"] = rfm["R"] + rfm["F"] + rfm["M"]
    return rfm, snapshot


def rule_segment(r):
    """基于 R/F/M 分档组合映射到 8 个业务标签。"""
    R, F, M = r["R"], r["F"], r["M"]
    if R >= 4 and F >= 4: return "冠军客户"
    if R >= 3 and F >= 3: return "忠诚客户"
    if R >= 4 and F <= 2: return "新客户"
    if R >= 3 and M >= 4: return "高潜力客户"
    if R <= 2 and F >= 3: return "流失预警"
    if R <= 2 and F <= 2 and M >= 4: return "重要挽回"
    if R <= 2: return "已流失/沉睡"
    return "一般客户"


def segment_stats(rfm):
    """各分群的人数/贡献占比统计。"""
    rfm = rfm.copy()
    rfm["Segment"] = rfm.apply(rule_segment, axis=1)
    seg = rfm.groupby("Segment").agg(
        人数=("CustomerID", "count"),
        平均R=("Recency", "mean"),
        平均F=("Frequency", "mean"),
        平均M=("Monetary", "mean"),
        总贡献=("Monetary", "sum"),
    ).reset_index().sort_values("总贡献", ascending=False)
    seg["人数占比"] = (seg["人数"] / seg["人数"].sum() * 100)
    seg["贡献占比"] = (seg["总贡献"] / seg["总贡献"].sum() * 100)
    return seg, rfm


def _standardize(X):
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    return (X - mu) / sd, mu, sd


def _kmeans(X, k=5, seed=42, max_iter=100):
    """纯 numpy K-Means（k-means++ 初始化）。返回标签与质心。"""
    rng = np.random.default_rng(seed)
    n = X.shape[0]
    # k-means++ 初始化
    centers = [X[rng.integers(n)]]
    for _ in range(1, k):
        d2 = np.min([np.sum((X - c) ** 2, axis=1) for c in centers], axis=0)
        probs = d2 / d2.sum()
        centers.append(X[rng.choice(n, p=probs)])
    centers = np.array(centers, dtype=float)
    labels = np.zeros(n, dtype=int)
    for _ in range(max_iter):
        dist = np.linalg.norm(X[:, None, :] - centers[None, :, :], axis=2)
        new_labels = dist.argmin(axis=1)
        if np.array_equal(new_labels, labels):
            break
        labels = new_labels
        for j in range(k):
            m = labels == j
            if m.any():
                centers[j] = X[m].mean(axis=0)
    return labels, centers


def _silhouette(X, labels, sample=600, seed=1):
    """轮廓系数（在抽样点上计算，保证性能）。"""
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(X), size=min(sample, len(X)), replace=False)
    Xs, ls = X[idx], labels[idx]
    s, n = [], len(Xs)
    for i in range(n):
        a = np.mean(np.linalg.norm(Xs[i] - Xs[ls == ls[i]], axis=1)[1:]) if (ls == ls[i]).sum() > 1 else 0.0
        bs = []
        for c in np.unique(ls):
            if c == ls[i]:
                continue
            bs.append(np.mean(np.linalg.norm(Xs[i] - Xs[ls == c], axis=1)))
        b = min(bs) if bs else 0.0
        s.append((b - a) / max(a, b, 1e-9))
    return float(np.mean(s))


def kmeans_validate(rfm, k=5, seed=42):
    """用 K-Means 在标准化 R/F/M 上聚类，作为规则分群的交叉验证（纯 numpy 实现）。

    返回：每客户聚类标签、聚类画像（人数/平均R/F/M/贡献）、轮廓系数。
    """
    X = rfm[["Recency", "Frequency", "Monetary"]].values.astype(float)
    Xs, _, _ = _standardize(X)
    labels, _ = _kmeans(Xs, k=k, seed=seed)
    rfm = rfm.copy()
    rfm["Cluster"] = labels
    prof = rfm.groupby("Cluster").agg(
        人数=("CustomerID", "count"),
        平均R=("Recency", "mean"),
        平均F=("Frequency", "mean"),
        平均M=("Monetary", "mean"),
        总贡献=("Monetary", "sum"),
    ).reset_index().sort_values("总贡献", ascending=False)
    prof["贡献占比"] = (prof["总贡献"] / prof["总贡献"].sum() * 100)
    prof["人数占比"] = (prof["人数"] / prof["人数"].sum() * 100)
    sil = _silhouette(Xs, labels)
    return rfm, prof, round(sil, 3)
