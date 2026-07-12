# -*- coding: utf-8 -*-
"""分析流程编排入口。

运行：python main.py
输出：outputs/stats.json + outputs/figs/*.html + outputs/images/*.png
"""
import json
import warnings
import pandas as pd
import numpy as np

from src import config as C
from src import io_clean, metrics, rfm as rfm_mod, cohort as cohort_mod, \
    anomaly as anomaly_mod, insights, predict, viz

warnings.filterwarnings("ignore")


def main():
    print("1/8 加载数据 (latin-1) ...")
    df = io_clean.load_raw()
    S = {}
    S["raw_rows"] = len(df)
    S["time_min"] = str(df["InvoiceDate"].min())
    S["time_max"] = str(df["InvoiceDate"].max())
    S["n_customers_raw"] = int(df["CustomerID"].nunique())
    S["n_countries_raw"] = int(df["Country"].nunique())
    S["n_invoices_raw"] = int(df["InvoiceNo"].nunique())
    S["n_products"] = int(df["StockCode"].nunique())
    S["profile"] = io_clean.profile(df)

    print("2/8 质量审计 ...")
    S["audit"] = io_clean.audit(df)
    print(f"   取消单 {S['audit']['cancel_pct']}% · CustomerID缺失 {S['audit']['cust_missing_pct']}%")

    print("3/8 清洗 ...")
    clean_full, sales, cancels, steps, drop_cust = io_clean.clean(df)
    S["clean_steps"] = steps
    S["drop_cust_missing"] = drop_cust
    S["sales_rows"] = len(sales)
    S["cancel_valid_rows"] = len(cancels)

    print("4/8 月度指标 ...")
    monthly, monthly_rep, summary = metrics.monthly_metrics(sales, cancels)
    S["monthly"] = monthly.round(2).to_dict("records")
    S["monthly_repurchase"] = monthly_rep
    S.update({k: v for k, v in summary.items()})
    S["country_dist"] = {str(k): int(v) for k, v in sales["Country"].value_counts().head(15).items()}

    ov, pivot, cc_gmv, prod, order_med = metrics.distributions(sales)
    S["order_val_median"] = order_med
    # 供 PNG 导出：星期×小时热力
    S["heat_pivot"] = [[round(float(v), 1) for v in row] for row in pivot.values]
    S["heat_cols"] = [f"{h}:00" for h in pivot.columns]
    S["heat_rows"] = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][:pivot.shape[0]]
    S["top_country"] = {str(k): round(float(v), 2) for k, v in cc_gmv.head(10).items()}
    S["top_product"] = [dict(desc=str(i), gmv=round(float(r["GMV"]), 2), qty=int(r["Qty"]))
                        for i, r in prod.head(10).iterrows()]

    print("5/8 RFM 分群 + K-Means 验证 ...")
    rfm_df, snapshot = rfm_mod.build_rfm(sales)
    S["snapshot"] = str(snapshot.date())
    seg_stat, rfm_labeled = rfm_mod.segment_stats(rfm_df)
    S["rfm_segments"] = seg_stat.round(2).to_dict("records")
    S["rfm_overall"] = dict(recency_median=round(float(rfm_df["Recency"].median()), 1),
                            freq_median=round(float(rfm_df["Frequency"].median()), 1),
                            monetary_median=round(float(rfm_df["Monetary"].median()), 2))
    rfm_km, km_prof, sil = rfm_mod.kmeans_validate(rfm_df, k=5)
    S["kmeans"] = dict(silhouette=sil,
                       profile=km_prof.round(2).to_dict("records"))

    print("6/8 Cohort LTV (含折现/毛利) ...")
    retention, ret_pct, ltv_cum, cohort_size = cohort_mod.build_cohort(sales)
    S["cohort_sizes"] = {str(k): int(v) for k, v in cohort_size.items()}
    # 供 PNG 导出：留存 / LTV 矩阵
    S["cohort_rows"] = list(ltv_cum.index)
    S["cohort_cols"] = [f"M{c}" for c in ltv_cum.columns]
    S["ret_pct"] = [[round(float(v), 1) for v in row] for row in ret_pct.values]
    S["ltv_cum"] = [[round(float(v), 2) for v in row] for row in ltv_cum.values]
    ltv_disc, ltv_margin = cohort_mod.ltv_with_assumptions(ltv_cum)
    S["ltv_m1"] = {str(c): round(float(ltv_cum.loc[c, 1]), 2)
                   for c in ltv_cum.index if 1 in ltv_cum.columns}
    S["m1_insight"] = cohort_mod.m1_insight(ret_pct)

    print("7/8 异常检测 (去季节性) ...")
    daily = sales.groupby(sales["InvoiceDate"].dt.date).agg(
        GMV=("Revenue", "sum"), Orders=("InvoiceNo", "nunique")).reset_index()
    daily["Date"] = pd.to_datetime(daily["InvoiceDate"])
    daily = daily.sort_values("Date")
    d_seas, anom = anomaly_mod.detect(daily)
    S["anomalies"] = [dict(date=str(r["Date"].date()), gmv=round(float(r["GMV"]), 0),
                           expected=round(float(r["expected"]), 0),
                           z=round(float(r["z"]), 2), typ=("高峰" if r["z"] > 0 else "骤降"))
                      for _, r in anom.sort_values("z", key=lambda s: s.abs(), ascending=False).head(12).iterrows()]
    # 对照：未去季节性的误报数
    naive = anomaly_mod.naive_detect(daily)
    S["anomaly_naive_count"] = int(len(naive))
    S["anomaly_seasonal_count"] = int(len(anom))
    # 供 PNG 导出：日度序列（日期/GMV/期望/残差/z）
    S["anomaly_series"] = dict(
        dates=[str(x.date()) for x in d_seas["Date"]],
        gmv=[round(float(v), 1) for v in d_seas["GMV"]],
        expected=[round(float(v), 1) for v in d_seas["expected"]],
        z=[round(float(v), 2) for v in d_seas["z"]],
        anom_idx=[int(i) for i in anom.index],
    )

    print("8/8 洞察 + 预测模型 ...")
    # 缺失 CustomerID 偏差：需用含全部行的原始数据（clean_full 已剔除缺失行）
    raw_full = df.copy()
    raw_full["Revenue"] = raw_full["Quantity"] * raw_full["UnitPrice"]
    raw_full["is_sales"] = ~raw_full["is_cancel"] & (raw_full["Quantity"] > 0) & (raw_full["UnitPrice"] > 0)
    S["missing_bias"] = metrics.missing_bias(raw_full)
    S["country_cancel"] = insights.country_cancel(sales, cancels)
    S["overseas"] = insights.overseas_value(sales)
    S["concentration"] = insights.concentration(seg_stat)
    churn = predict.churn_model(rfm_df)
    clv = predict.clv_model(rfm_df)
    S["churn"] = churn
    S["clv"] = clv

    # ---------- 可视化 ----------
    viz.gmv_trend(monthly)
    viz.buyer_aov(monthly)
    viz.repurchase_cancel(monthly, monthly_rep)
    viz.top_country(cc_gmv)
    viz.top_country_overseas(cc_gmv)
    viz.top_product(prod)
    viz.order_dist(ov)
    viz.heatmap_time(pivot)
    viz.rfm_segments(seg_stat)
    viz.rfm_bubble(seg_stat)
    viz.kmeans_view(km_prof)
    viz.cohort_retention(ret_pct)
    viz.cohort_ltv(ltv_cum, suffix="", title="Cohort 累计人均收入 LTV (£)")
    viz.cohort_ltv(ltv_disc, suffix="_disc", title="Cohort 折现后 LTV (£, 月折现1%)")
    viz.anomaly_view(d_seas, anom, residual=False)
    viz.predict_view(churn, clv)
    viz.importance_view(churn, clv)

    with open(C.STATS, "w", encoding="utf-8") as f:
        json.dump(S, f, ensure_ascii=False, indent=2, default=str)
    print(f"\n完成. 图表数: {len([f for f in __import__('os').listdir(C.FIGS) if f.endswith('.html')])}")
    print(f"GMV: £{S['gmv_total']/1e6:.2f}M · 订单: {S['n_orders']:,} · 客户: {S['n_customers']:,}")
    print(f"流失模型 AUC={churn['auc']} · CLV R²={clv['r2']} · KMeans轮廓={sil}")


if __name__ == "__main__":
    main()
