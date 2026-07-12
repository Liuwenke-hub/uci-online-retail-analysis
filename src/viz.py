# -*- coding: utf-8 -*-
"""Plotly 图表构建与导出（HTML 片段 + README 静态 PNG）。"""
import os
import plotly.graph_objects as go
import plotly.express as px
from plotly.offline import plot
from src import config as C

LAYOUT = dict(
    template="plotly_white",
    font=dict(family="Inter, 'Segoe UI', 'Microsoft YaHei', sans-serif", size=13, color="#1e293b"),
    paper_bgcolor="white", plot_bgcolor="white",
    margin=dict(l=60, r=30, t=50, b=50),
    colorway=C.PALETTE,
    hoverlabel=dict(bgcolor="white", font_size=12),
    legend=dict(bgcolor="rgba(255,255,255,0.6)"),
)

# kaleido 是否可用（用于可选 PNG 导出）；不可用则静默跳过，不影响 HTML 主产物
try:
    import kaleido  # noqa: F401
    _KALEIDO_OK = True
except Exception:
    _KALEIDO_OK = False


def _save(fig, name, png=False, width=900, height=460):
    """保存为 HTML 片段；可选导出 PNG（供 README 静态展示，需 kaleido）。"""
    fig.update_layout(**LAYOUT)
    html = plot(fig, include_plotlyjs=False, output_type="div",
                config={"displayModeBar": False, "responsive": True})
    with open(os.path.join(C.FIGS, name + ".html"), "w", encoding="utf-8") as f:
        f.write(html)
    if png and _KALEIDO_OK:
        try:
            fig.write_image(os.path.join(C.IMGS, name + ".png"), width=width, height=height, scale=2)
        except Exception as e:  # kaleido 不可用时不阻塞主流程
            print(f"  [warn] PNG 导出失败 {name}: {e}")


# ---------- 月度指标 ----------
def gmv_trend(monthly):
    mo = monthly
    fig = go.Figure()
    fig.add_bar(x=mo["YM"], y=mo["GMV"], name="GMV(£)", marker_color=C.C["primary"], opacity=0.85)
    fig.add_trace(go.Scatter(x=mo["YM"], y=mo["Orders"], name="订单数", yaxis="y2",
                             mode="lines+markers", line=dict(color=C.C["amber"], width=3)))
    fig.update_layout(title="月度 GMV 与订单数趋势", yaxis=dict(title="GMV(£)"),
                      yaxis2=dict(title="订单数", overlaying="y", side="right", showgrid=False),
                      hovermode="x unified")
    _save(fig, "gmv_trend", png=True)
    return "gmv_trend"


def buyer_aov(monthly):
    mo = monthly
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=mo["YM"], y=mo["Buyers"], name="活跃买家", mode="lines+markers",
                             line=dict(color=C.C["teal"], width=3), fill="tozeroy", fillcolor="rgba(13,148,136,0.1)"))
    fig.add_trace(go.Scatter(x=mo["YM"], y=mo["AOV"], name="客单价(£)", yaxis="y2",
                             mode="lines+markers", line=dict(color=C.C["purple"], width=3)))
    fig.update_layout(title="月度活跃买家数与客单价", yaxis=dict(title="活跃买家"),
                      yaxis2=dict(title="客单价(£)", overlaying="y", side="right", showgrid=False),
                      hovermode="x unified")
    _save(fig, "buyer_aov")
    return "buyer_aov"


def repurchase_cancel(monthly, monthly_rep):
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=monthly["YM"], y=monthly_rep, name="当月复购率(%)",
                             mode="lines+markers", line=dict(color=C.C["green"], width=3)))
    fig.add_trace(go.Scatter(x=monthly["YM"], y=monthly["CancelRate"], name="取消/退款率(%)",
                             mode="lines+markers", line=dict(color=C.C["red"], width=3, dash="dot")))
    fig.update_layout(title="月度复购率与取消/退款率", yaxis=dict(title="百分比 (%)"), hovermode="x unified")
    _save(fig, "repurchase_cancel")
    return "repurchase_cancel"


# ---------- Top 维度 ----------
def top_country(cc_gmv):
    top_c = cc_gmv.head(10)[::-1]
    fig = go.Figure(go.Bar(x=top_c.values, y=top_c.index, orientation="h",
                           marker_color=C.C["primary"],
                           text=[f"£{v/1000:.0f}k" for v in top_c.values], textposition="auto"))
    fig.update_layout(title="Top 10 国家 / 地区 GMV", xaxis_title="GMV(£)")
    _save(fig, "top_country")
    return "top_country"


def top_country_overseas(cc_gmv):
    cc_ov = cc_gmv[cc_gmv.index != "United Kingdom"].head(10)[::-1]
    fig = go.Figure(go.Bar(x=cc_ov.values, y=cc_ov.index, orientation="h", marker_color=C.C["accent"],
                           text=[f"£{v/1000:.0f}k" for v in cc_ov.values], textposition="auto"))
    fig.update_layout(title="Top 10 海外市场 GMV(剔除英国)", xaxis_title="GMV(£)")
    _save(fig, "top_country_overseas")
    return "top_country_overseas"


def top_product(prod):
    top_p = prod.head(12)[::-1]
    fig = go.Figure(go.Bar(x=top_p["GMV"].values, y=[d[:35] for d in top_p.index], orientation="h",
                           marker_color=C.C["purple"], text=[f"£{v/1000:.0f}k" for v in top_p["GMV"].values],
                           textposition="auto"))
    fig.update_layout(title="Top 12 商品 GMV", xaxis_title="GMV(£)", margin=dict(l=240))
    _save(fig, "top_product")
    return "top_product"


# ---------- 分布 / 时段 ----------
def order_dist(ov):
    fig = go.Figure(go.Histogram(x=ov, nbinsx=50, marker_color=C.C["accent"]))
    fig.update_layout(title="订单金额分布 (截尾99分位)", xaxis_title="订单金额(£)", yaxis_title="订单数")
    _save(fig, "order_dist", png=True)
    return "order_dist"


def heatmap_time(pivot):
    dow_names = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    fig = go.Figure(go.Heatmap(z=pivot.values, x=[f"{h}:00" for h in pivot.columns],
                               y=[dow_names[i] for i in pivot.index], colorscale="Blues",
                               colorbar=dict(title="GMV")))
    fig.update_layout(title="下单时段热力图 (星期 × 小时)", xaxis_title="小时", yaxis_title="星期")
    _save(fig, "heatmap_time", png=True)
    return "heatmap_time"


# ---------- RFM ----------
def rfm_segments(seg_stat):
    ss = seg_stat.sort_values("总贡献", ascending=True)
    fig = go.Figure()
    fig.add_bar(y=ss["Segment"], x=ss["人数占比"], name="人数占比(%)", orientation="h",
                marker_color=C.C["slate"], opacity=0.6)
    fig.add_bar(y=ss["Segment"], x=ss["贡献占比"], name="GMV贡献占比(%)", orientation="h",
                marker_color=C.C["primary"])
    fig.update_layout(title="RFM 客户分群: 人数占比 vs GMV贡献占比", barmode="group", xaxis_title="占比 (%)")
    _save(fig, "rfm_segments", png=True)
    return "rfm_segments"


def rfm_bubble(seg_stat):
    fig = px.scatter(seg_stat, x="平均F", y="平均M", size="人数", color="Segment",
                     size_max=60, color_discrete_sequence=C.PALETTE,
                     hover_name="Segment", labels={"平均F": "平均购买频次", "平均M": "平均消费额(£)"})
    fig.update_layout(title="RFM 分群气泡图 (频次 × 金额 × 人数)")
    _save(fig, "rfm_bubble", png=True)
    return "rfm_bubble"


def kmeans_view(prof):
    p = prof.sort_values("总贡献", ascending=True)
    fig = go.Figure()
    fig.add_bar(y="Cluster " + p["Cluster"].astype(str), x=p["人数占比"], name="人数占比(%)",
                orientation="h", marker_color=C.C["teal"], opacity=0.6)
    fig.add_bar(y="Cluster " + p["Cluster"].astype(str), x=p["贡献占比"], name="GMV贡献占比(%)",
                orientation="h", marker_color=C.C["purple"])
    fig.update_layout(title=f"K-Means 聚类验证 (轮廓系数见报告): 人数占比 vs 贡献占比",
                      barmode="group", xaxis_title="占比 (%)")
    _save(fig, "kmeans_segments", png=True)
    return "kmeans_segments"


# ---------- Cohort ----------
def cohort_retention(ret_pct):
    rp = ret_pct.round(1)
    fig = go.Figure(go.Heatmap(z=rp.values, x=[f"M{c}" for c in rp.columns], y=rp.index,
                               colorscale="Blues", text=rp.values, texttemplate="%{text}",
                               textfont=dict(size=9), colorbar=dict(title="留存%")))
    fig.update_layout(title="Cohort 留存率热力图 (%)", xaxis_title="首购后第N月", yaxis_title="首购月份")
    _save(fig, "cohort_retention", png=True)
    return "cohort_retention"


def cohort_ltv(ltv_cum, suffix="", title="Cohort 累计人均 LTV 热力图 (£)"):
    lc = ltv_cum.round(2)
    fig = go.Figure(go.Heatmap(z=lc.values, x=[f"M{c}" for c in lc.columns], y=lc.index,
                               colorscale="Greens", text=lc.values, texttemplate="%{text}",
                               textfont=dict(size=8), colorbar=dict(title="£/人")))
    fig.update_layout(title=title, xaxis_title="首购后第N月", yaxis_title="首购月份")
    _save(fig, "cohort_ltv" + suffix, png=True)
    return "cohort_ltv" + suffix


# ---------- 异常检测 ----------
def anomaly_view(daily, anom, residual=False):
    ycol = "residual" if residual else "GMV"
    yname = "去季节化残差(£)" if residual else "日GMV(£)"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily["Date"], y=daily[ycol], name=yname, mode="lines",
                             line=dict(color=C.C["primary"], width=1.2)))
    if not residual:
        fig.add_trace(go.Scatter(x=daily["Date"], y=daily["expected"], name="季节性期望",
                                 mode="lines", line=dict(color=C.C["teal"], width=2, dash="dash")))
    fig.add_trace(go.Scatter(x=anom["Date"], y=anom[ycol], name="异常点(|z|≥2.5)", mode="markers",
                             marker=dict(color=C.C["red"], size=9, symbol="x")))
    fig.update_layout(title="日 GMV 异常检测（已去除周内/月度季节性）", yaxis_title=yname,
                      hovermode="x unified")
    _save(fig, "anomaly", png=True)
    return "anomaly"


# ---------- 预测 ----------
def predict_view(churn, clv):
    fig = go.Figure()
    labels = ["流失模型 AUC", "流失模型 准确率", "CLV模型 R²"]
    vals = [churn["auc"], churn["accuracy"], clv["r2"]]
    fig.add_bar(x=labels, y=vals, marker_color=[C.C["red"], C.C["amber"], C.C["green"]],
                text=[f"{v:.3f}" for v in vals], textposition="auto")
    fig.update_layout(title="预测模型评估指标", yaxis_title="得分", yaxis=dict(range=[0, 1.05]))
    _save(fig, "predict_metrics", png=True)
    return "predict_metrics"


def importance_view(churn, clv):
    fig = go.Figure()
    feats = ["Recency", "Frequency", "Monetary"]
    fig.add_trace(go.Bar(x=feats, y=[churn["importance"].get(f, 0) for f in feats], name="流失模型",
                         marker_color=C.C["red"]))
    fig.add_trace(go.Bar(x=feats, y=[clv["importance"].get(f, 0) for f in feats], name="CLV模型",
                         marker_color=C.C["green"]))
    fig.update_layout(title="特征重要性 (各模型所用特征不同)", barmode="group", yaxis_title="重要性 |权重|")
    _save(fig, "feature_importance", png=True)
    return "feature_importance"
