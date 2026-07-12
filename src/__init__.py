# -*- coding: utf-8 -*-
"""UCI Online Retail 电商业务健康度 + 用户价值分析 · 模块化分析包

数据：UCI Machine Learning Repository - Online Retail（英国跨境电商逐行订单明细）
本包将「加载清洗 → 指标 → RFM → Cohort → 异常 → 洞察 → 预测 → 可视化」拆分为独立模块，
由 main.py 编排。所有图表输出为 plotly HTML 片段（outputs/figs）与静态 PNG（outputs/images）。
"""

__version__ = "2.0.0"
