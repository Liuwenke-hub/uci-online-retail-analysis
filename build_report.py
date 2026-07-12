# -*- coding: utf-8 -*-
"""读取 outputs/stats.json 与 figs/*.html，组装单文件 HTML 报告。

图表交互依赖 Plotly.js v3.7.0（与 plotly.py 6.9.0 内置版本一致）。
本报告保持匿名，不含任何个人身份信息。
"""
import json, os

BASE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(BASE, "outputs")
FIGS = os.path.join(OUT, "figs")

with open(os.path.join(OUT, "stats.json"), encoding="utf-8") as f:
    S = json.load(f)

PLOTLY_CDN = "https://cdn.plot.ly/plotly-3.7.0.min.js"

def fig(name):
    p = os.path.join(FIGS, name + ".html")
    if not os.path.exists(p):
        return f"<div class='fig-missing'>[缺失图表 {name}]</div>"
    with open(p, encoding="utf-8") as f:
        return f.read()

def money(v):
    v = float(v)
    if abs(v) >= 1e6: return f"£{v/1e6:.2f}M"
    if abs(v) >= 1e3: return f"£{v/1e3:.1f}k"
    return f"£{v:.0f}"

def num(v):
    return f"{int(v):,}"

# ---------- 组装动态片段 ----------
dict_rows = ""
BIZ = {
    "InvoiceNo": ("发票/订单号", "订单标识；C开头为取消单。同一订单含多行商品", "推断：订单级主键前缀，不确定C是否全部为退货"),
    "StockCode": ("商品编码", "SKU 唯一标识；含 POST/M/DOT 等非商品编码", "不确定字母编码的完整业务口径"),
    "Description": ("商品描述", "商品名称文本，存在缺失与手工备注", "部分为库存调整备注而非商品"),
    "Quantity": ("购买数量", "件数；负数=退货/取消/库存调整", "极端负值可能为批量冲销"),
    "InvoiceDate": ("下单时间", "订单时间戳(分钟级)，时间粒度到分钟", "时区未知，推断为英国本地时间"),
    "UnitPrice": ("商品单价", "单位售价(£英镑)；0或负为异常/调整", "含税与否未标注"),
    "CustomerID": ("客户ID", "客户唯一标识；约25%缺失(游客/未登记)", "缺失单无法做用户级分析"),
    "Country": ("国家/地区", "客户所属国家；UK占绝大多数", "含 Unspecified 等非标准值"),
}
for p in S["profile"]:
    col = p["col"]
    biz = BIZ.get(col, ("-", "-", "-"))
    dict_rows += f"""<tr><td class='mono'>{col}</td><td>{biz[0]}</td><td>{p['dtype']}</td>
    <td>{num(p['nunique'])}</td><td>{p['miss_pct']}%</td><td>{biz[1]}</td><td class='muted'>{biz[2]}</td></tr>"""

a = S["audit"]
audit_cards = f"""
<div class='mini'><span class='mini-v red'>{a['cancel_pct']}%</span><span class='mini-l'>取消单占比 ({num(a['cancel_rows'])} 行, C开头)</span></div>
<div class='mini'><span class='mini-v amber'>{a['cust_missing_pct']}%</span><span class='mini-l'>CustomerID 缺失 ({num(a['cust_missing'])} 行)</span></div>
<div class='mini'><span class='mini-v red'>{num(a['qty_neg'])}</span><span class='mini-l'>Quantity 为负记录</span></div>
<div class='mini'><span class='mini-v red'>{num(a['price_neg']+a['price_zero'])}</span><span class='mini-l'>UnitPrice ≤0 记录</span></div>
<div class='mini'><span class='mini-v amber'>{num(a['dup_rows'])}</span><span class='mini-l'>完全重复记录 ({a['dup_pct']}%)</span></div>
<div class='mini'><span class='mini-v'>{num(a['desc_missing'])}</span><span class='mini-l'>Description 缺失</span></div>
"""
q = a["Quantity_stats"]; up = a["UnitPrice_stats"]
ext_rows = f"""
<tr><td>Quantity</td><td>{q['min']}</td><td>{q['1%']}</td><td>{q['50%']}</td><td>{q['99%']}</td><td>{q['max']}</td><td>{q['mean']}</td></tr>
<tr><td>UnitPrice</td><td>{up['min']}</td><td>{up['1%']}</td><td>{up['50%']}</td><td>{up['99%']}</td><td>{up['max']}</td><td>{up['mean']}</td></tr>
"""
special_rows = "".join([f"<span class='chip'>{k} · {num(v)}</span>" for k, v in a["special_codes"].items()])

clean_rules = [
    ("R1 去重", "存在完全重复的逐行记录，可能为导出重复", f"{num(S['audit']['dup_rows'])} 行", "低-中：不影响业务口径", "保留原始df副本，drop_duplicates可复现"),
    ("R2 分离取消单", "InvoiceNo 以 C 开头为取消/退货，应从GMV剔除并单独统计退款率", f"{num(a['cancel_rows'])} 行", "高：直接影响GMV口径", "以布尔列 is_cancel 标记，不物理删除"),
    ("R3 剔除非正数量/单价", "Quantity≤0 或 UnitPrice≤0 为退货/调整/赠品，非有效销售", "见有效销售行数", "高：影响GMV与客单价", "过滤条件可切换，原始行可回溯"),
    ("R4 缺失CustomerID处理", "约25%订单无客户ID(游客)，用户级分析(RFM/Cohort)需剔除，业务级GMV可保留", f"{num(a['cust_missing'])} 行", "中：分层使用，不同分析口径不同", "保留两套数据集：交易级/用户级"),
    ("R5 特殊StockCode标注", "POST/M/DOT/BANK CHARGES 等为运费/人工/调整项", "见特殊码", "低：可按需纳入或剔除", "打标签而非删除，按分析目的选择"),
]
clean_rows = "".join([f"<tr><td class='mono'>{r[0]}</td><td>{r[1]}</td><td>{r[2]}</td><td>{r[3]}</td><td class='muted'>{r[4]}</td></tr>" for r in clean_rules])

seg_rows = ""
seg_desc = {
    "冠军客户": "近期高频高额，最有价值", "忠诚客户": "稳定复购，需维系",
    "新客户": "近期首购，需培育", "高潜力客户": "近期高额，可提频",
    "流失预警": "曾高频但近期沉默", "重要挽回": "高价值但久未购",
    "已流失/沉睡": "长期未购", "一般客户": "各项中等",
}
for r in S["rfm_segments"]:
    seg_rows += f"""<tr><td><b>{r['Segment']}</b><div class='muted'>{seg_desc.get(r['Segment'],'')}</div></td>
    <td>{num(r['人数'])}</td><td>{r['人数占比']}%</td><td>{r['平均R']:.0f}天</td>
    <td>{r['平均F']:.1f}</td><td>{money(r['平均M'])}</td><td><b>{r['贡献占比']}%</b></td></tr>"""

# KMeans 验证表
km_rows = ""
for r in S["kmeans"]["profile"]:
    km_rows += f"""<tr><td>Cluster {r['Cluster']}</td><td>{num(r['人数'])}</td><td>{r['人数占比']:.1f}%</td>
    <td>{r['平均R']:.0f}天</td><td>{r['平均F']:.1f}</td><td>{money(r['平均M'])}</td><td><b>{r['贡献占比']:.1f}%</b></td></tr>"""

anom_rows = ""
anom_hyp = {"高峰": "促销/大客户批量采购/季节性(圣诞备货)", "骤降": "周末/节假日休市/数据采集缺口"}
for r in S["anomalies"][:10]:
    anom_rows += f"""<tr><td>{r['date']}</td><td><span class='badge {'up' if r['typ']=='高峰' else 'down'}'>{r['typ']}</span></td>
    <td>{money(r['gmv'])}</td><td>期望 {money(r['expected'])}</td><td>z={r['z']}</td><td class='muted'>{anom_hyp[r['typ']]}</td></tr>"""

mo_rows = ""
for i, m in enumerate(S["monthly"]):
    rep = S["monthly_repurchase"][i]
    mo_rows += f"""<tr><td>{m['YM']}</td><td>{money(m['GMV'])}</td><td>{num(m['Orders'])}</td>
    <td>{num(m['Buyers'])}</td><td>{money(m['AOV'])}</td><td>{rep}%</td><td>{m['CancelRate']:.1f}%</td></tr>"""

# 数据绑定洞察
cc = S["country_cancel"]; ovs = S["overseas"]; conc = S["concentration"]; mb = S["missing_bias"]
m1 = S["m1_insight"]
# 预测
ch = S["churn"]; cl = S["clv"]

recs = [
    ("1. 激活「重要挽回」与「流失预警」客群",
     f"对高价值但久未购买的客群发起个性化召回。RFM 显示「{conc['top_segment']}」等头部客群以少数人数贡献 {conc['top2_contrib']}% GMV，维系头部是首要任务。",
     "召回率、被召回客户90天GMV、ROI",
     "A/B：随机拆分实验组(收券)vs对照组(不收)，对比90天复购率与GMV，样本量按当前分群人数保证统计功效",
     "过度补贴侵蚀利润；需设券门槛与有效期，监控毛利率"),
    ("2. 提升新客首购→复购转化(Cohort M1留存)",
     f"首购后次月留存通常最大跌幅。本数据最低 M1 留存出现在 {m1['low_cohort']} cohort（仅 {m1['low_m1']}%），最高为 {m1['high_cohort']}（{m1['high_m1']}%）。针对低留存批次在首购后14-30天触发二单激励。",
     "M1留存率、90天人均LTV、二单转化率",
     "对新客cohort按注册周随机分组,实验组享二单权益,对比留存曲线与累计LTV",
     "激励可能吸引羊毛党;结合RFM过滤异常账户"),
    (f"3. 降低高取消率市场（{cc['top_country']}）的退款",
     f"数据显示 {cc['top_country']} 的订单取消/退款率高达 {cc['top_cancel_rate']}%（英国为 {cc['uk_cancel_rate']}%），显著高于本土。针对性改进该市场的商品描述、物流与库存。",
     "取消/退款率、退款金额占GMV比",
     "对高取消SKU/市场改进详情页与发货流程,前后对比取消率(中断时间序列分析)",
     "口径需区分主动取消与缺货;避免误伤正常退换"),
    ("4. 拓展高客单价海外市场",
     f"英国占比过高,收入集中风险大。海外市场(剔除UK)GMV 达 {money(ovs['overseas'])}，其中 {ovs['best_aov_country']} 客单价最高(£{ovs['best_aov']})，是增长洼地，做本地化获客。",
     "海外GMV占比、海外新客数、海外客单价",
     "选1-2个市场做投放增量实验,对比获客成本(CAC)与回本周期(LTV/CAC)",
     "跨境物流成本与退货率上升;先小步测试单一市场"),
    ("5. 用预测模型前置识别流失客户",
     f"逻辑回归流失预测模型 AUC={ch['auc']}（测试集）。为避免循环论证，特征中已排除定义变量 Recency，仅用 Frequency/Monetary 两类事前行为预测流失，更贴近真实场景。可将模型部署为周级评分，对高分客户自动触发维系。",
     "模型捕获的流失客户数、维系后留存提升、节省的GMV",
     "将模型输出接入运营系统做holdout验证,对比干预组与对照组的实际流失率",
     "标签定义(180天)需结合业务校准;避免对误判客户过度打扰"),
]

rec_cards = ""
for r in recs:
    rec_cards += f"""<div class='rec'>
      <div class='rec-h'>{r[0]}</div>
      <div class='rec-b'>{r[1]}</div>
      <div class='rec-meta'>
        <div><span class='tag green'>预期收益指标</span> {r[2]}</div>
        <div><span class='tag blue'>验证实验设计</span> {r[3]}</div>
        <div><span class='tag amber'>风险点</span> {r[4]}</div>
      </div></div>"""

period = f"{S['time_min'][:10]} ~ {S['time_max'][:10]}"
kpis = f"""
<div class='kpi'><div class='kpi-v'>{money(S['gmv_total'])}</div><div class='kpi-l'>总 GMV (剔除取消单)</div></div>
<div class='kpi'><div class='kpi-v'>{num(S['n_orders'])}</div><div class='kpi-l'>有效订单数</div></div>
<div class='kpi'><div class='kpi-v'>{num(S['n_customers'])}</div><div class='kpi-l'>活跃购买用户</div></div>
<div class='kpi'><div class='kpi-v'>{money(S['aov'])}</div><div class='kpi-l'>客单价 (AOV)</div></div>
<div class='kpi'><div class='kpi-v'>{S['overall_repurchase']}%</div><div class='kpi-l'>整体复购率</div></div>
<div class='kpi'><div class='kpi-v'>{S['n_countries']}</div><div class='kpi-l'>覆盖国家/地区</div></div>
"""

HTML = f"""<!DOCTYPE html><html lang='zh-CN'><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width,initial-scale=1'>
<title>电商业务健康度 + 用户价值分析报告 · UCI Online Retail</title>
<script src='{PLOTLY_CDN}'></script>
<style>
:root{{--bg:#f8fafc;--card:#fff;--ink:#0f172a;--muted:#64748b;--line:#e2e8f0;--pri:#2563eb;}}
*{{box-sizing:border-box;}}
body{{margin:0;background:var(--bg);color:var(--ink);font-family:Inter,'Segoe UI','Microsoft YaHei',sans-serif;line-height:1.6;}}
.wrap{{max-width:1160px;margin:0 auto;padding:0 20px 80px;}}
header{{background:linear-gradient(135deg,#1e3a8a,#2563eb 55%,#0ea5e9);color:#fff;padding:54px 20px 60px;}}
header .inner{{max-width:1160px;margin:0 auto;}}
.tagline{{font-size:13px;letter-spacing:2px;opacity:.85;text-transform:uppercase;}}
h1{{font-size:32px;margin:8px 0 6px;font-weight:800;}}
.sub{{opacity:.9;font-size:15px;}}
.kpigrid{{display:grid;grid-template-columns:repeat(6,1fr);gap:14px;margin-top:28px;}}
.kpi{{background:rgba(255,255,255,.14);backdrop-filter:blur(6px);border:1px solid rgba(255,255,255,.2);border-radius:12px;padding:16px 14px;}}
.kpi-v{{font-size:24px;font-weight:800;}}
.kpi-l{{font-size:12px;opacity:.9;margin-top:4px;}}
section{{background:var(--card);border:1px solid var(--line);border-radius:16px;padding:28px 30px;margin-top:26px;box-shadow:0 1px 3px rgba(15,23,42,.04);}}
.sec-tag{{display:inline-block;font-size:12px;font-weight:700;color:var(--pri);background:#eff6ff;padding:4px 12px;border-radius:20px;letter-spacing:1px;}}
h2{{font-size:23px;margin:12px 0 4px;font-weight:800;}}
h3{{font-size:16px;margin:26px 0 10px;font-weight:700;color:#1e293b;border-left:4px solid var(--pri);padding-left:10px;}}
p{{color:#334155;}}
.muted{{color:var(--muted);font-size:12.5px;}}
.mono{{font-family:ui-monospace,Consolas,monospace;font-size:12.5px;color:#0f172a;}}
table{{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px;}}
th{{background:#f1f5f9;text-align:left;padding:9px 11px;font-weight:700;color:#334155;border-bottom:2px solid var(--line);font-size:12px;}}
td{{padding:8px 11px;border-bottom:1px solid #f1f5f9;vertical-align:top;}}
tr:hover td{{background:#fafcff;}}
.fig{{margin:14px 0 6px;border:1px solid var(--line);border-radius:12px;padding:8px;background:#fff;}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px;}}
.minis{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:16px 0;}}
.mini{{background:#f8fafc;border:1px solid var(--line);border-radius:10px;padding:14px;}}
.mini-v{{font-size:22px;font-weight:800;display:block;}}
.mini-l{{font-size:12px;color:var(--muted);margin-top:4px;display:block;}}
.red{{color:#dc2626;}}.amber{{color:#d97706;}}.green{{color:#16a34a;}}.blue{{color:#2563eb;}}
.chip{{display:inline-block;background:#f1f5f9;border:1px solid var(--line);border-radius:8px;padding:3px 9px;margin:3px 4px 0 0;font-size:12px;font-family:monospace;}}
.badge{{padding:2px 9px;border-radius:20px;font-size:12px;font-weight:700;}}
.badge.up{{background:#fee2e2;color:#dc2626;}} .badge.down{{background:#dcfce7;color:#16a34a;}}
.rec{{border:1px solid var(--line);border-left:5px solid var(--pri);border-radius:12px;padding:18px 20px;margin:14px 0;background:#fff;}}
.rec-h{{font-size:17px;font-weight:800;color:#1e293b;}}
.rec-b{{color:#334155;margin:8px 0 12px;}}
.rec-meta>div{{margin:6px 0;font-size:13px;color:#475569;}}
.tag{{display:inline-block;font-size:11px;font-weight:700;padding:2px 9px;border-radius:6px;margin-right:8px;}}
.tag.green{{background:#dcfce7;color:#15803d;}}.tag.blue{{background:#dbeafe;color:#1d4ed8;}}.tag.amber{{background:#fef3c7;color:#b45309;}}
.callout{{background:#eff6ff;border:1px solid #bfdbfe;border-radius:12px;padding:16px 20px;margin:16px 0;font-size:14px;}}
.toc{{display:flex;flex-wrap:wrap;gap:10px;margin-top:16px;}}
.toc a{{font-size:13px;color:var(--pri);text-decoration:none;background:#eff6ff;padding:6px 14px;border-radius:20px;border:1px solid #dbeafe;}}
.toc a:hover{{background:#dbeafe;}}
ul{{color:#334155;font-size:14px;}} li{{margin:5px 0;}}
.foot{{text-align:center;color:var(--muted);font-size:12px;margin-top:40px;}}
.note{{background:#fffbeb;border:1px solid #fde68a;border-radius:12px;padding:14px 18px;margin:14px 0;font-size:13px;color:#92400e;}}
@media(max-width:900px){{.kpigrid{{grid-template-columns:repeat(3,1fr);}}.grid2{{grid-template-columns:1fr;}}.minis{{grid-template-columns:1fr;}}}}
</style></head><body>
<header><div class='inner'>
<div class='tagline'>E-COMMERCE HEALTH & CUSTOMER VALUE ANALYSIS</div>
<h1>电商业务健康度 + 用户价值 分析报告</h1>
<div class='sub'>数据集：UCI Online Retail（英国跨境电商逐行订单明细）&nbsp;·&nbsp;时间范围：{period}&nbsp;·&nbsp;原始记录 {num(S['raw_rows'])} 行</div>
<div class='kpigrid'>{kpis}</div>
</div></header>
<div class='wrap'>

<section>
<span class='sec-tag'>EXECUTIVE SUMMARY</span>
<h2>核心结论摘要</h2>
<div class='callout'>
在 {period} 期间，该电商实现有效 GMV <b>{money(S['gmv_total'])}</b>，来自 <b>{num(S['n_customers'])}</b> 名可识别客户的 <b>{num(S['n_orders'])}</b> 笔订单，客单价 <b>{money(S['aov'])}</b>，整体复购率 <b>{S['overall_repurchase']}%</b>。
</div>
<ul>
<li><b>业务高度依赖英国本土市场</b>：英国贡献绝大部分 GMV，海外市场（荷兰、爱尔兰、德国等）虽单量少但客单价高，是增长洼地。</li>
<li><b>收入高度集中于少数客群</b>：RFM 显示头部 {conc['top2_contrib']}% 的 GMV 来自少数分群（{conc['top_segment']} 独占 {conc['top_segment_contrib']}%），符合帕累托特征。</li>
<li><b>数据质量存在系统性问题</b>：约 {a['cust_missing_pct']}% 订单缺失 CustomerID，{a['cancel_pct']}% 为取消单，需分层清洗后再计算各口径指标。</li>
<li><b>季节性显著</b>：去季节化后的异常检测显示，GMV 在年末（圣诞备货季）出现明显高峰；而大量「周末单量低」属于正常规律，已在检测中剔除。</li>
<li><b>新客留存快速衰减</b>：Cohort 分析显示首购后次月留存最大跌幅（最低见于 {m1['low_cohort']} cohort，仅 {m1['low_m1']}%）。</li>
<li><b>可预测</b>：随机森林流失预测模型 AUC 达 {ch['auc']}，证明客户生命周期状态可由 R/F/M 有效建模，可前置干预。</li>
</ul>
<div class='toc'>
<a href='#s1'>① 数据字典</a><a href='#s2'>② 质量审计与清洗</a><a href='#s3'>③ 核心指标看板</a>
<a href='#s4'>④ RFM 分群</a><a href='#s5'>⑤ Cohort LTV</a><a href='#s6'>⑥ 异常检测</a>
<a href='#s7'>⑦ 预测模型</a><a href='#s8'>⑧ 结论与行动</a>
</div>
</section>

<section id='s1'>
<span class='sec-tag'>01 · DATA DICTIONARY</span>
<h2>数据字典与业务含义推断</h2>
<p><b>数据粒度</b>：一行 = 一张发票中的一个商品明细（Invoice × StockCode）。<b>潜在主键</b>：无单列主键，业务主键约为 (InvoiceNo, StockCode) 组合；订单级主键为 InvoiceNo。<b>时间字段</b>：InvoiceDate（分钟级）。<b>金额字段</b>：UnitPrice（单价£），行金额 = Quantity × UnitPrice。<b>国家字段</b>：Country（客户所属国家/地区）。</p>
<table><thead><tr><th>字段</th><th>业务含义</th><th>类型</th><th>唯一值</th><th>缺失率</th><th>说明</th><th>不确定点</th></tr></thead>
<tbody>{dict_rows}</tbody></table>
<div class='muted' style='margin-top:12px'>⚠️ 不确定点说明：时区未在数据中标注（推断为英国本地时间）；UnitPrice 是否含税未知；字母类 StockCode（如 POST/M/DOT/BANK CHARGES）为运费/人工/调整项而非实物商品；负数 Quantity 既可能是退货也可能是库存冲销。</div>
</section>

<section id='s2'>
<span class='sec-tag'>02 · DATA QUALITY AUDIT</span>
<h2>数据质量审计</h2>
<div class='minis'>{audit_cards}</div>
<h3>Quantity / UnitPrice 极端值分布</h3>
<table><thead><tr><th>字段</th><th>最小</th><th>P1</th><th>中位</th><th>P99</th><th>最大</th><th>均值</th></tr></thead><tbody>{ext_rows}</tbody></table>
<p class='muted' style='margin-top:10px'>Quantity 与 UnitPrice 均存在极端正负值（批量订单、库存冲销、异常高价手工条目），中位数与均值差异大，建议用分位截尾展示分布。</p>
<h3>非商品类特殊 StockCode（Top）</h3>
<div>{special_rows}</div>
<h3>缺失 CustomerID 的偏差讨论</h3>
<div class='callout'>
用户级分析（RFM/Cohort）剔除了 {num(mb['nos_orders'])} 笔无 CustomerID 的「游客」订单。对比发现：有ID订单客单价 £{mb['has_aov']}，无ID订单客单价 £{mb['nos_aov']}（{'更高' if mb['nos_aov']>mb['has_aov'] else '更低'}）；
取消率分别为 {mb['has_cancel_share']}% vs {mb['nos_cancel_share']}%。<b>启示</b>：游客订单结构可能不同于注册用户，RFM/Cohort 结论仅代表「可识别客户」群体，外推至全量需谨慎。
</div>
<h3>清洗规则清单（原因 / 影响面 / 可回滚策略）</h3>
<table><thead><tr><th>规则</th><th>原因</th><th>影响面(记录)</th><th>业务影响</th><th>可回滚策略</th></tr></thead><tbody>{clean_rows}</tbody></table>
<div class='callout' style='margin-top:16px'>
<b>清洗结果</b>：原始 {num(S['raw_rows'])} 行 → 去重后剔除缺失客户 {num(S['drop_cust_missing'])} 行 → 分离取消单 {num(S['cancel_valid_rows'])} 行 → 最终<b>有效销售 {num(S['sales_rows'])} 行</b>。所有规则均以「打标签/条件过滤」实现，保留原始 DataFrame 副本，可完整回滚。
</div>
</section>

<section id='s3'>
<span class='sec-tag'>03 · KPI DASHBOARD</span>
<h2>核心指标看板（按月）</h2>
<div class='fig'>{fig('gmv_trend')}</div>
<div class='grid2'>
<div class='fig'>{fig('buyer_aov')}</div>
<div class='fig'>{fig('repurchase_cancel')}</div>
</div>
<h3>月度指标明细</h3>
<table><thead><tr><th>月份</th><th>GMV</th><th>订单数</th><th>活跃买家</th><th>客单价</th><th>当月复购率</th><th>取消率</th></tr></thead><tbody>{mo_rows}</tbody></table>
<h3>Top 国家 / 地区</h3>
<div class='grid2'><div class='fig'>{fig('top_country')}</div><div class='fig'>{fig('top_country_overseas')}</div></div>
<h3>Top 商品与订单结构</h3>
<div class='fig'>{fig('top_product')}</div>
<div class='grid2'><div class='fig'>{fig('order_dist')}</div><div class='fig'>{fig('heatmap_time')}</div></div>
</section>

<section id='s4'>
<span class='sec-tag'>04 · RFM SEGMENTATION</span>
<h2>用户分群 (RFM)</h2>
<p><b>参数选择依据</b>：以数据末日 +1 天（{S['snapshot']}）为快照日计算 Recency；Frequency 用去重发票数（而非行数，避免大订单虚高）；Monetary 用有效销售额。R/F/M 各按<b>五分位(qcut=5)</b>打分；Frequency 因长尾严重先做 rank 再分箱避免边界重叠。分群规则基于 R、F、M 分档组合映射为 8 个业务标签。</p>
<div class='grid2'><div class='fig'>{fig('rfm_segments')}</div><div class='fig'>{fig('rfm_bubble')}</div></div>
<table><thead><tr><th>客户分群</th><th>人数</th><th>人数占比</th><th>平均Recency</th><th>平均Frequency</th><th>平均消费额</th><th>GMV贡献占比</th></tr></thead><tbody>{seg_rows}</tbody></table>
<div class='muted' style='margin-top:10px'>中位数参考：Recency {S['rfm_overall']['recency_median']} 天，Frequency {S['rfm_overall']['freq_median']} 单，Monetary {money(S['rfm_overall']['monetary_median'])}。</div>
<h3>K-Means 聚类交叉验证</h3>
<p>为验证规则分群的合理性，对标准化后的 R/F/M 做 K-Means(k=5) 聚类，<b>轮廓系数 = {S['kmeans']['silhouette']}</b>。聚类画像与规则分群在「高价值小群体 vs 低价值大群体」的结构上高度一致，说明分群边界稳健。</p>
<div class='fig'>{fig('kmeans_segments')}</div>
<table><thead><tr><th>Cluster</th><th>人数</th><th>人数占比</th><th>平均Recency</th><th>平均Frequency</th><th>平均消费额</th><th>GMV贡献占比</th></tr></thead><tbody>{km_rows}</tbody></table>
</section>

<section id='s5'>
<span class='sec-tag'>05 · COHORT LTV</span>
<h2>简化版 LTV（Cohort 分析）</h2>
<p>按客户<b>首购月份</b>划分 Cohort，追踪其在后续各月的留存与累计人均贡献。左图为留存率（首购当月=100%），右图为累计人均收入 LTV（£/人）。</p>
<div class='grid2'><div class='fig'>{fig('cohort_retention')}</div><div class='fig'>{fig('cohort_ltv')}</div></div>
<div class='note'><b>关于「真 LTV」的说明</b>：上图「累计人均收入」是 LTV 的代理指标，<b>未含毛利率与折现</b>。更严谨的 LTV 应：① 用贡献毛利率（本分析假设 {int(__import__('src.config', fromlist=['MARGIN_ASSUMPTION']).MARGIN_ASSUMPTION*100)}%）折算收入；② 按资金时间价值折现未来月份（月折现率 {int(__import__('src.config', fromlist=['MONTHLY_DISCOUNT']).MONTHLY_DISCOUNT*100)}%）。下图为<b>折现后 LTV</b> 视角，可见远期月份贡献被合理压低。</div>
<div class='fig'>{fig('cohort_ltv_disc')}</div>
<p class='muted'>解读：首购后次月（M1）留存通常出现最大跌幅（最低见于 {m1['low_cohort']} cohort，仅 {m1['low_m1']}%），是流失防控与二单激励的关键窗口；累计 LTV 曲线的斜率随月份放缓，头部 cohort 的人均 LTV 明显高于后期批次。</p>
</section>

<section id='s6'>
<span class='sec-tag'>06 · ANOMALY DETECTION</span>
<h2>异常检测（去季节化的 GMV 波动）</h2>
<p><b>方法</b>：先以「全局均值 × 星期因子 × 月份因子」建模<b>季节性期望</b>，对残差做 28 日滚动中位数 + 稳健 z-score（|z|≥2.5）标记异常。这样可避免把「周末单量低」这类规律误判为异常。对照：未去季节性的朴素方法会标记 <b>{S['anomaly_naive_count']}</b> 个点，去季节化后仅 <b>{S['anomaly_seasonal_count']}</b> 个真正异常。</p>
<div class='fig'>{fig('anomaly')}</div>
<h3>异常日期与原因假设</h3>
<table><thead><tr><th>日期</th><th>类型</th><th>当日GMV</th><th>季节性期望</th><th>偏离度</th><th>可能原因假设</th></tr></thead><tbody>{anom_rows}</tbody></table>
<div class='muted' style='margin-top:10px'><b>验证方法</b>：① 高峰点 → 关联当日大额订单/大客户 InvoiceNo 与商品，核对是否批量采购或促销；② 骤降点 → 核对是否周末/英国公共假期或数据采集缺口（对比相邻周同一星期）；③ 结合营销日历与库存记录交叉验证。</div>
</section>

<section id='s7'>
<span class='sec-tag'>07 · PREDICTIVE MODELING</span>
<h2>预测性分析（加分项）</h2>
<p>在描述性分析之外，构建了两个可复用预测模型，评估指标如下。</p>
<div class='grid2'><div class='fig'>{fig('predict_metrics')}</div><div class='fig'>{fig('feature_importance')}</div></div>
<h3>流失预测（分类）</h3>
<p>定义流失：快照日前 {__import__('src.config', fromlist=['CHURN_RECENCY_DAYS']).CHURN_RECENCY_DAYS} 天无交易（占样本 {ch['churn_rate']}%）。逻辑回归在 30% 测试集上 <b>AUC={ch['auc']}</b>、准确率 {ch['accuracy']}。<b>方法学注意</b>：标签由 Recency 定义，故特征中已排除 Recency 以避免循环论证/数据泄漏，仅用 Frequency（{ch['importance']['Frequency']}）、Monetary（{ch['importance']['Monetary']}）两类事前行为预测流失——验证「购买频次/消费额越低的客户越易流失」这一可干预信号。</p>
<h3>CLV 预测（回归）</h3>
<p>以 Frequency / Recency 回归预测 Monetary（CLV 代理），测试集 <b>R²={cl['r2']}</b>。Frequency 是收入的最强预测因子，说明提升购买频次比单纯拉新更能放大客户价值。</p>
<div class='callout'>模型价值：可将流失评分部署为<b>周级运营触发器</b>，对高分客户自动派发维系权益，把「事后分析」变为「事前干预」。</div>
</section>

<section id='s8'>
<span class='sec-tag'>08 · CONCLUSIONS & ACTIONS</span>
<h2>结论与可执行建议</h2>
<p>基于以上分析，提出 5 条可落地建议，每条含<b>预期收益指标</b>、<b>验证实验设计</b>与<b>风险点</b>。建议均绑定本项目的具体数据发现：</p>
{rec_cards}
</section>

<div class='foot'>本报告由自动化分析流程生成 · 数据源：UCI Machine Learning Repository - Online Retail · 交互图表基于 Plotly.js v3.7.0（与 plotly.py 6.9.0 匹配）</div>
</div></body></html>"""

with open(os.path.join(OUT, "report.html"), "w", encoding="utf-8") as f:
    f.write(HTML)
print("报告已生成: outputs/report.html  大小", round(len(HTML)/1024, 1), "KB")
