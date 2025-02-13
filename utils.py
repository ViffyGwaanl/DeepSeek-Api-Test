#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Api Test
Version: 0.2.0
Author: Gwaanl

一些常用的辅助函数，如日志配置、导出图片、生成带样式的HTML表格等
"""

import os
import logging
import json
import pandas as pd
import imgkit

# ========== 日志配置 ==========
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

file_handler = logging.FileHandler("test.log", mode="a", encoding="utf-8")
file_handler.setLevel(logging.DEBUG)
file_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(filename)s:%(lineno)d - %(message)s"
)
file_handler.setFormatter(file_formatter)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] - %(message)s")
console_handler.setFormatter(console_formatter)

logger.handlers = []
logger.addHandler(file_handler)
logger.addHandler(console_handler)

os.environ['no_proxy'] = '*'

def detect_outliers_iqr(df, group_col='model_key', target_col='tokens_per_second'):
    """使用 IQR 方法检测并标记离群值"""
    df = df.copy()
    df['is_outlier'] = False
    df[target_col] = pd.to_numeric(df[target_col], errors='coerce')
    df.loc[df[target_col].isna(), 'is_outlier'] = True
    for model, group_data in df.groupby(group_col):
        valid_mask = (~group_data[target_col].isna()) & (~group_data['is_outlier'])
        valid_data = group_data[valid_mask][target_col]
        if len(valid_data) == 0:
            continue
        Q1 = valid_data.quantile(0.25)
        Q3 = valid_data.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        outlier_index = group_data[
            (group_data[target_col] < lower_bound) |
            (group_data[target_col] > upper_bound)
        ].index
        df.loc[outlier_index, 'is_outlier'] = True
    return df

def make_styled_table_html(df, highlight_tps=True, is_summary=False, hide_response_cols=False):
    """
    生成带有自定义CSS的HTML表格。
    - hide_response_cols=True 时，会隐藏 "Response JSON"、"Content" 和 "Reasoning Content" 列。
    """
    import pandas as pd
    import json

    df = df.copy()

    # 如果包含 raw_response 列，尝试解析并拆分 "Content" 与 "Reasoning Content"
    if 'raw_response' in df.columns:
        def extract_fields(x):
            try:
                data = json.loads(x) if isinstance(x, str) else {}
                if "choices" in data and isinstance(data["choices"], list) and len(data["choices"]) > 0:
                    message = data["choices"][0].get("message", {})
                    content = message.get("content", "")
                    reasoning = message.get("reasoning_content", "")
                else:
                    content, reasoning = "", ""
            except Exception:
                content, reasoning = "", ""
            return pd.Series({'Content': content, 'Reasoning Content': reasoning})
        extracted = df['raw_response'].apply(extract_fields)
        df = pd.concat([df, extracted], axis=1)

    # 移除不需要展示的 test_round 列
    df = df.drop(columns=['test_round'], errors='ignore')

    # 重命名列
    df_renamed = df.rename(columns={
        'model_name': 'Model Name',
        'completion_tokens': 'Completion Tokens',
        'time_taken': 'Time Taken (s)',
        'tokens_per_second': 'Tokens/s (Token/s)',
        'input_timestamp': 'Input Time',
        'output_timestamp': 'Output Time',
        'raw_response': 'Response JSON'
    })

    # 如果需要隐藏响应相关列，则直接从 DataFrame 中剔除它们
    if hide_response_cols:
        df_renamed = df_renamed.drop(columns=["Response JSON", "Content", "Reasoning Content"], errors='ignore')

    # 调整列的顺序
    if not is_summary:
        desired_order = [
            'Model Name',
            'Tokens/s (Token/s)',
            'Completion Tokens',
            'Time Taken (s)',
            'Input Time',
            'Output Time',
            'Response JSON',
            'Content',
            'Reasoning Content'
        ]
        existing_cols = [col for col in desired_order if col in df_renamed.columns]
        df_renamed = df_renamed[existing_cols]
    else:
        desired_order_summary = [
            "Model Name",
            "Avg Tokens/s (Token/s)",
            "Avg Completion Tokens",
            "Avg Time Taken (s)",
            "Outlier Count"
        ]
        existing_cols = [col for col in desired_order_summary if col in df_renamed.columns]
        remaining_cols = [c for c in df_renamed.columns if c not in existing_cols]
        df_renamed = df_renamed[existing_cols + remaining_cols]

    # 将部分列转换为数值类型，方便格式化显示
    numeric_cols = [
        'Completion Tokens', 'Time Taken (s)', 'Tokens/s (Token/s)',
        'Avg Completion Tokens', 'Avg Time Taken (s)', 'Avg Tokens/s (Token/s)'
    ]
    for col in numeric_cols:
        if col in df_renamed.columns:
            df_renamed[col] = pd.to_numeric(df_renamed[col], errors='coerce')

    # 定义每一列对应的 CSS 类（可选）
    classes = pd.DataFrame("", index=df_renamed.index, columns=df_renamed.columns)
    if "Response JSON" in classes.columns:
        classes["Response JSON"] = "col-response"
    if "Content" in classes.columns:
        classes["Content"] = "col-content"
    if "Reasoning Content" in classes.columns:
        classes["Reasoning Content"] = "col-reasoning"
    if "Input Time" in classes.columns:
        classes["Input Time"] = "col-time"
    if "Output Time" in classes.columns:
        classes["Output Time"] = "col-time"

    # 生成样式化的 HTML 表格
    styled = df_renamed.style \
        .set_td_classes(classes) \
        .set_properties(**{'border': '1px solid #ccc', 'padding': '8px'}) \
        .set_table_styles([
            {'selector': 'th', 'props': [('background-color', '#f7f7f7'),
                                         ('font-weight', 'bold'),
                                         ('padding', '10px')]},
            {'selector': 'table', 'props': [('border-collapse', 'collapse'),
                                             ('width', '100%'),
                                             ('margin', '16px 0')]}
        ]) \
        .format({
            'Completion Tokens': "{:.0f}",
            'Time Taken (s)': "{:.2f}",
            'Tokens/s (Token/s)': "{:.2f}",
            'Avg Completion Tokens': "{:.0f}",
            'Avg Time Taken (s)': "{:.2f}",
            'Avg Tokens/s (Token/s)': "{:.2f}"
        }, na_rep='Error')

    if highlight_tps and ('Tokens/s (Token/s)' in df_renamed.columns):
        styled = styled.background_gradient(cmap='Blues', subset=['Tokens/s (Token/s)']) \
            .highlight_max(subset=['Tokens/s (Token/s)'], color='lightgreen', axis=0, props='font-weight:bold;')

    if is_summary and ('Avg Tokens/s (Token/s)' in df_renamed.columns):
        styled = styled.background_gradient(cmap='Blues', subset=['Avg Tokens/s (Token/s)']) \
            .highlight_max(subset=['Avg Tokens/s (Token/s)'], color='lightgreen', axis=0, props='font-weight:bold;')

    return styled.to_html()


def export_tables_to_image(df_rounds, df_summary):
    """
    将 4 个表格合并为一张长图片并保存到 output 文件夹中。
    在导出的图片里，不显示 Response JSON / Content / Reasoning Content。
    """
    os.makedirs('output', exist_ok=True)
    import datetime
    filename = os.path.join('output', f"test_results_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.png")

    round_htmls_for_export = []
    for i, df_r in enumerate(df_rounds, start=1):
        html_r = make_styled_table_html(df_r, highlight_tps=True, is_summary=False, hide_response_cols=True)
        round_htmls_for_export.append(f"<h2>Round {i}</h2>{html_r}")

    summary_html_for_export = make_styled_table_html(df_summary, highlight_tps=False, is_summary=True, hide_response_cols=True)

    combined_html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <title>Exported Tables</title>
        <style>
            body {{
                font-family: "Helvetica Neue", Arial, sans-serif;
                margin: 20px;
                color: #333;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 20px;
            }}
            th, td {{
                border: 1px solid #ccc;
                padding: 8px;
                text-align: center;
            }}
            th {{
                background-color: #f7f7f7;
            }}
        </style>
    </head>
    <body>
        {''.join(round_htmls_for_export)}
        <h2>Summary</h2>
        {summary_html_for_export}
    </body>
    </html>
    """

    options = {
        'encoding': 'UTF-8',
        'width': '1200'
    }
    imgkit.from_string(combined_html, filename, options=options)
    logger.info(f"已导出4个表为一张图片: {filename}")
