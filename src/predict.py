# -*- coding: utf-8 -*-
"""预测性分析：流失预测（逻辑回归）+ CLV 预测（线性回归）。

全部用纯 numpy 实现（不依赖 scikit-learn），便于任意环境复现。
模型评估指标（AUC / 准确率 / R²）与特征重要性均由 numpy 计算。
"""
import numpy as np
from src import config as C


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


def _standardize(X):
    mu = X.mean(axis=0)
    sd = X.std(axis=0)
    sd[sd == 0] = 1.0
    return (X - mu) / sd


def _train_test_split(X, y, test_size=0.3, seed=42):
    rng = np.random.default_rng(seed)
    n = len(y)
    perm = rng.permutation(n)
    k = int(n * test_size)
    te, tr = perm[:k], perm[k:]
    return X[tr], X[te], y[tr], y[te]


def _auc(y_true, y_score):
    """用 Mann-Whitney U 的秩次法计算 AUC（纯 numpy）。"""
    order = np.argsort(y_score)
    ranks = np.empty(len(y_score), dtype=float)
    s = y_score[order]
    r = np.arange(1, len(s) + 1)
    # 处理并列
    i = 0
    while i < len(s):
        j = i
        while j + 1 < len(s) and s[j + 1] == s[i]:
            j += 1
        r[i:j + 1] = (i + j + 2) / 2.0
        i = j + 1
    ranks[order] = r
    n_pos = y_true.sum()
    n_neg = len(y_true) - n_pos
    if n_pos == 0 or n_neg == 0:
        return float("nan")
    return (ranks[y_true == 1].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)


def churn_model(rfm):
    """用客户行为特征预测是否流失（快照日前 CHURN_RECENCY_DAYS 无交易）。

    逻辑回归（梯度下降 + L2 正则），报告 AUC / 准确率 / 特征重要性（|权重|）。

    注意：标签由 Recency 定义，故特征中**排除 Recency** 以避免循环论证/数据泄漏；
    仅用 Frequency、Monetary 两类「事前可观测行为」预测流失，更贴近真实建模场景。
    """
    rfm = rfm.copy()
    rfm["churn"] = (rfm["Recency"] > C.CHURN_RECENCY_DAYS).astype(int)
    Xraw = rfm[["Frequency", "Monetary"]].values.astype(float)
    y = rfm["churn"].values.astype(float)

    Xtr, Xte, ytr, yte = _train_test_split(Xraw, y)
    Xtr_s = _standardize(Xtr)
    Xte_s = (Xte - Xtr.mean(axis=0)) / Xtr.std(axis=0)
    # 加截距
    Xtr_a = np.column_stack([np.ones(len(Xtr_s)), Xtr_s])
    Xte_a = np.column_stack([np.ones(len(Xte_s)), Xte_s])

    # 梯度下降
    w = np.zeros(Xtr_a.shape[1])
    lr, iters, lam = 0.1, 3000, 0.01
    for _ in range(iters):
        z = Xtr_a @ w
        p = _sigmoid(z)
        grad = (Xtr_a.T @ (p - ytr)) / len(ytr) + lam * w
        grad[0] -= lam * w[0]  # 截距不惩罚
        w -= lr * grad

    proba = _sigmoid(Xte_a @ w)
    pred = (proba >= 0.5).astype(int)
    auc = round(float(_auc(yte.astype(bool), proba)), 3)
    acc = round(float((pred == yte).mean()), 3)
    # 特征重要性：标准化后权重的绝对值（排除截距）
    imp = dict(zip(["Frequency", "Monetary"],
                   [round(float(abs(v)), 3) for v in w[1:]]))
    churn_rate = round(float(y.mean() * 100), 1)
    return dict(auc=auc, accuracy=acc, importance=imp, churn_rate=churn_rate, n=len(rfm))


def clv_model(rfm):
    """用 Frequency / Recency 回归预测 Monetary（CLV 代理）。

    线性回归（正规方程闭式解），报告 R² 与系数重要性。
    """
    Xraw = rfm[["Recency", "Frequency"]].values.astype(float)
    y = rfm["Monetary"].values.astype(float)
    Xtr, Xte, ytr, yte = _train_test_split(Xraw, y)
    Xtr_s = _standardize(Xtr)
    Xte_s = (Xte - Xtr.mean(axis=0)) / Xtr.std(axis=0)
    Xtr_a = np.column_stack([np.ones(len(Xtr_s)), Xtr_s])
    Xte_a = np.column_stack([np.ones(len(Xte_s)), Xte_s])

    w = np.linalg.solve(Xtr_a.T @ Xtr_a, Xtr_a.T @ ytr)  # 正规方程
    pred = Xte_a @ w
    ss_res = float(((yte - pred) ** 2).sum())
    ss_tot = float(((yte - yte.mean()) ** 2).sum())
    r2 = round(1 - ss_res / ss_tot, 3) if ss_tot > 0 else 0.0
    imp = dict(zip(["Recency", "Frequency"],
                   [round(float(abs(v)), 3) for v in w[1:]]))
    return dict(r2=r2, importance=imp, n=len(rfm))
