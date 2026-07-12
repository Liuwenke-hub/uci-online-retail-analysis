# E-Commerce Business Health & Customer Value Analysis

> 基于 **UCI Online Retail** 数据集（英国跨境电商逐行订单明细，541,909 行，2010-12 ~ 2011-12）的完整数据分析项目，覆盖**数据质量审计 → 核心指标看板 → RFM 分群 → Cohort LTV → 异常检测 → 预测建模**的全流程。

本项目为**匿名**的数据分析作品集示例，不含任何个人身份信息。数据集来自公开学术仓库，仅用于方法演示。

---

## 分析框架

| 模块 | 内容 | 关键产出 |
|---|---|---|
| ① 数据字典 | 字段业务含义、粒度、主键、时间/金额/国家字段、不确定点标注 | 8 字段推断表 |
| ② 质量审计 + 清洗 | 缺失率/异常值/取消单/重复；5 条**可回滚**清洗规则 | 清洗规则清单 |
| ③ 核心指标看板 | 月度 GMV / 订单 / 客单价 / 活跃买家 / 复购率 / 取消率 | 月度交互图表看板 |
| ④ RFM 分群 | 五分位打分 + 8 业务标签 + **K-Means 聚类交叉验证** | 分群贡献帕累托 |
| ⑤ Cohort LTV | 按首购月留存 + 累计人均 LTV（含**折现/毛利率**假设） | 留存/LTV 热力图 |
| ⑥ 异常检测 | **去季节化**后的稳健 z-score（剔除周末规律误报） | 异常日期+原因假设 |
| ⑦ 预测建模 | 流失预测（逻辑回归 · R/F 特征, AUC=0.80）+ CLV 预测（线性回归 · R/F, R²=0.42） | 评估指标+特征重要性 |
| ⑧ 结论与行动 | 5 条可落地建议（预期收益 / A-B 实验 / 风险点） | 行动清单 |

---

## 核心结论（摘要）

- **业务高度依赖英国本土**：海外市场经济单量少但客单价高，是增长洼地。
- **收入极度集中**：头部少数客群贡献绝大部分 GMV（帕累托特征）。
- **数据质量有系统性问题**：约 25% 订单缺失 CustomerID，1.7% 为取消单。
- **季节性显著**：去季节化后年末（圣诞备货）出现明确 GMV 高峰。
- **新客留存衰减快**：首购次月（M1）留存跌幅最大，是二单激励关键窗口。
- **可预测**：逻辑回归流失模型 AUC=0.80，可由 Frequency / Monetary 前置识别流失客户（Recency 因定义流失标签已剔除，避免数据泄漏）。

---

## 关键图表

> 以下为静态截图；完整交互图表见 `outputs/report.html`（需浏览器打开，依赖 Plotly.js CDN）。

**月度 GMV 与订单趋势**
![月度GMV与订单趋势](outputs/images/gmv_trend.png)

**RFM 分群：人数占比 vs GMV 贡献占比**
![RFM分群](outputs/images/rfm_segments.png)

**RFM 分群气泡图**
![RFM气泡图](outputs/images/rfm_bubble.png)

**下单时段热力图（星期 × 小时）**
![时段热力图](outputs/images/heatmap_time.png)

**Cohort 留存率热力图**
![Cohort留存](outputs/images/cohort_retention.png)

**Cohort 累计人均 LTV 热力图**
![Cohort LTV](outputs/images/cohort_ltv.png)

**异常检测（去季节化）**
![异常检测](outputs/images/anomaly.png)

**预测模型评估指标**
![预测模型](outputs/images/predict_metrics.png)

---

## 技术栈

- **Python 3.13**：pandas · numpy · plotly 6.9 · matplotlib
- **可视化**：Plotly（交互式 HTML 报告）+ matplotlib（README 静态截图，纯 Python 生成）
- **方法论**：RFM 五分位打分、**K-Means 聚类验证（纯 numpy 实现）**、Cohort 留存/LTV、去季节化异常检测、**逻辑回归流失预测 + 线性回归 CLV 预测（均纯 numpy 实现，零外部 ML 依赖）**

## 项目结构

```
.
├── main.py                 # 分析流程编排入口
├── build_report.py         # 组装单文件 HTML 报告
├── requirements.txt
├── src/
│   ├── config.py           # 路径与业务假设常量
│   ├── io_clean.py         # 加载 / 编码修复 / 清洗 / 审计
│   ├── metrics.py          # 月度指标 / 分布 / 缺失偏差
│   ├── rfm.py              # RFM 打分 + K-Means 验证
│   ├── cohort.py           # Cohort 留存 + LTV（折现/毛利）
│   ├── anomaly.py          # 去季节化异常检测
│   ├── insights.py         # 数据绑定洞察（最高取消率国家等）
│   ├── predict.py          # 流失 / CLV 预测模型
│   └── viz.py              # Plotly 图表构建与导出
└── outputs/
    ├── report.html         # 最终交互报告
    ├── stats.json          # 结构化统计结果
    ├── figs/               # 图表 HTML 片段
    └── images/             # README 静态截图
```

## 如何复现（Runbook）

> 环境：Python 3.13 · 依赖见 `requirements.txt` · 数据就绪时全流程约 1 分钟

```bash
# 0. （可选）建虚拟环境
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate

# 1. 装依赖
pip install -r requirements.txt

# 2. 取数据：下载 UCI Online Retail，解压后另存为 OnlineRetail.csv 放项目根目录
#    地址 https://archive.ics.uci.edu/static/public/352/online+retail.zip
#    注意：脚本用 latin-1 读取（含 £ 符号），请勿改编码

# 3. 跑分析 → 生成 outputs/stats.json + outputs/figs/*.html
python main.py

# 4. 出报告 → 生成 outputs/report.html（交互式，17 图）
python build_report.py

# 5. 出截图（可选，README 用）→ 生成 outputs/images/*.png
python export_png.py
```

**预期产物**：`outputs/report.html`（主交付物，浏览器打开，依赖 Plotly.js CDN）。

> ⚠️ 数据文件 `OnlineRetail.csv`（约 45MB）已被 `.gitignore` 忽略，不进版本库；`outputs/figs/` 为中间产物同样忽略，可由代码复现。

### 部署到 GitHub（首次提交命令清单）

```bash
# 提交前先配置身份（未设置会提交失败）
git config user.name  "你的GitHub用户名"
git config user.email "你的GitHub邮箱"

git init
git add .
git commit -m "feat: UCI Online Retail 业务健康度与用户价值分析"
git branch -M main
git remote add origin <你的仓库URL>   # 例: https://github.com/Liuwenke-hub/data-analysis-projects.git
git push -u origin main
```

> 仓库已匿名（无作者署名），`.gitignore` 已排除数据与中间产物，首推体积约 0.5MB，适合直接作为作品集仓库。

## 方法学说明与局限

- **LTV 为简化口径**：累计人均收入未含毛利率与折现；报告内已给出折现后 LTV 视图，毛利率（30%）与月折现率（1%）为显式假设，可按业务调整（见 `src/config.py`）。
- **流失标签定义**：快照日前 180 天无交易，需结合业务校准。
- **缺失 CustomerID 偏差**：用户级分析仅覆盖「可识别客户」，对全量外推需谨慎（报告中已做偏差讨论）。
- **异常检测**：去季节化方法基于历史星期/月份因子，对结构性突变（如新市场开拓）可能不敏感。

---

*数据源：UCI Machine Learning Repository – Online Retail。本项目仅供数据分析方法演示。*
