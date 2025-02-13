#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Api Test
Version: 0.2.0
Author: Gwaanl
"""

import os
import threading
import logging
import datetime
import webbrowser  # 用于自动打开浏览器

from flask import Flask, request, jsonify
from flask_apscheduler import APScheduler

# ======= 导入我们拆分后的其他模块 =======
from config import Config
from db_utils import init_db, load_latest_test_result, load_all_test_results, load_test_result_by_id
from test_runner import background_test_runner, scheduled_job, test_progress
from test_runner import custom_prompt, set_custom_prompt
from utils import logger  # 使用同一个 logger 避免多次配置
from utils import export_tables_to_image

# ======= Flask 应用初始化 =======
app = Flask(__name__)
app.config.from_object(Config())

# 隐藏Flask默认请求日志
logging.getLogger('werkzeug').setLevel(logging.ERROR)

# APScheduler 初始化
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()


# ========== 路由区域 ==========
@app.route("/start_test")
def start_test_route():
    """手动启动测试的接口，支持自定义超时"""
    timeout = int(request.args.get("timeout", 300))  # 默认 5 分钟
    logger.info(f"开始一轮测试（后台线程），超时时间: {timeout}秒")

    global test_progress
    with test_progress["lock"]:
        if test_progress["status"] == "running":
            return "已有测试正在进行，请稍候再试。"
        test_progress["status"] = "running"
        test_progress["current_round"] = 0
        test_progress["total_rounds"] = 3
        test_progress["finished_models"] = []
        test_progress["unfinished_models"] = []

    thread = threading.Thread(target=background_test_runner, args=(timeout,))
    thread.start()

    return "测试已后台启动！"


@app.route("/update_prompt")
def update_prompt_route():
    """更新自定义提示词"""
    prompt = request.args.get("prompt", "")
    if prompt:
        set_custom_prompt(prompt)
        logger.info(f"更新提示词为: {prompt}")
    return "提示词已更新！"


@app.route("/test_progress")
def test_progress_route():
    """查看当前测试进度"""
    global test_progress
    with test_progress["lock"]:
        return jsonify({
            "status": test_progress["status"],
            "current_round": test_progress["current_round"],
            "total_rounds": test_progress["total_rounds"],
            "finished_models": test_progress["finished_models"],
            "unfinished_models": test_progress["unfinished_models"],
        })


@app.route("/")
def index_page():
    """首页：展示最新一条测试结果"""
    global custom_prompt
    row = load_latest_test_result()

    # 通用的基础样式
    base_styles = """
    <style>
    body {
        font-family: "Helvetica Neue", Arial, sans-serif;
        margin: 20px;
        color: #333;
    }
    h1, h2, h3 {
        font-weight: 600;
    }
    input[type="number"], input[type="text"] {
        font-size: 14px;
        padding: 4px;
        margin-right: 10px;
        border: 1px solid #ccc;
        border-radius: 4px;
    }
    button {
        background-color: #5cb85c;
        color: white;
        border: none;
        padding: 6px 12px;
        margin-right: 10px;
        font-size: 14px;
        border-radius: 4px;
        cursor: pointer;
    }
    button:hover {
        background-color: #4cae4c;
    }
    .toggle-buttons button {
        background-color: #0275d8;
    }
    .toggle-buttons button:hover {
        background-color: #025aa5;
    }
    /* 默认隐藏以下几列 */
    .col-response, .col-content, .col-reasoning, .col-time {
        display: none;
    }
    .progress-container {
        width: 100%;
        background-color: #f1f1f1;
        border-radius: 5px;
        overflow: hidden;
        margin-top: 10px;
        max-width: 400px;
    }
    .progress-bar {
        height: 24px;
        background-color: #337ab7;
        text-align: center;
        color: #fff;
        line-height: 24px;
        width: 0%;
        transition: width 0.4s ease;
    }
    table {
        border: 1px solid #ccc;
        border-collapse: collapse;
        margin: 16px 0;
        width: 100%;
    }
    th, td {
        border: 1px solid #ccc;
        padding: 8px;
        text-align: center;
    }
    th {
        background-color: #f7f7f7;
        font-weight: bold;
    }
    a {
        color: #337ab7;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    .flex-row {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        margin-top: 20px;
    }
    .flex-row > div {
        margin-right: 20px;
        margin-bottom: 10px;
    }
    </style>
    """

    progress_section = """
    <div id="progress-info" style="margin-top: 20px;">
        <strong style="font-size:16px;">测试进度</strong>
        <div class="progress-container">
            <div id="progress-bar" class="progress-bar">0%</div>
        </div>
        <div id="progress-text" style="margin-top: 8px; color: #555;">无测试进行</div>
    </div>
    """

    # 如果没有任何测试记录
    if row is None:
        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="utf-8">
            <title>DeepSeek 测试结果</title>
            {base_styles}
        </head>
        <body>
            <h1>DeepSeek 测试结果</h1>
            <p>暂无测试结果，请等待定时任务或手动发起测试。</p>

            <div class="flex-row">
                <div>
                    <label for="timeout">超时时间 (秒):</label>
                    <input type="number" id="timeout" value="300" min="30" max="600">
                </div>
                <div>
                    <label for="prompt">自定义提示词：</label>
                    <input type="text" id="prompt" value="{custom_prompt}">
                </div>
                <div>
                    <button onclick="triggerTest()">立即执行一轮测试</button>
                    <button onclick="setPrompt()">更新提示词</button>
                </div>
            </div>

            {progress_section}

            <hr/>
            <p><a href="/history">查看历史记录</a></p>

            <script>
            function triggerTest() {{
                const timeout = document.getElementById("timeout").value;
                fetch(`/start_test?timeout=${{timeout}}`)
                  .then(response => response.text())
                  .then(msg => {{ alert(msg); }});
            }}

            function setPrompt() {{
                const prompt = document.getElementById("prompt").value;
                fetch(`/update_prompt?prompt=${{prompt}}`)
                  .then(response => response.text())
                  .then(msg => {{
                      alert(msg);
                  }});
            }}

            setInterval(() => {{
                fetch("/test_progress").then(res => res.json()).then(data => {{
                    const progressBar = document.getElementById("progress-bar");
                    const progressText = document.getElementById("progress-text");
                    if (!progressBar || !progressText) return;

                    if (data.status === "idle") {{
                        progressBar.style.width = "0%";
                        progressBar.textContent = "0%";
                        progressText.textContent = "无测试进行";
                    }} else if (data.status === "running") {{
                        const totalModels = data.finished_models.length + data.unfinished_models.length;
                        const finished = data.finished_models.length;
                        let percent = 0;
                        if (totalModels > 0) {{
                            percent = Math.round((finished / totalModels) * 100);
                        }}
                        progressBar.style.width = percent + "%";
                        progressBar.textContent = percent + "%";

                        progressText.innerHTML = `
                            当前第 ${{data.current_round}} / ${{data.total_rounds}} 轮 <br/>
                            已完成模型: ${{data.finished_models.join(", ")}} <br/>
                            未完成模型: ${{data.unfinished_models.join(", ")}}
                        `;
                    }} else if (data.status === "finished") {{
                        progressBar.style.width = "100%";
                        progressBar.textContent = "100%";
                        progressText.textContent = "全部轮次测试完成";
                        setTimeout(() => window.location.reload(), 2000);
                    }}
                }});
            }}, 2000);
            </script>
        </body>
        </html>
        """

    # 有最新测试记录的情况
    test_id = row["id"]
    test_start_time = row["test_start_time"]
    test_end_time = row["test_end_time"]
    r1 = row["round1_html"]
    r2 = row["round2_html"]
    r3 = row["round3_html"]
    smry = row["summary_html"]

    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>DeepSeek 测试结果</title>
    {base_styles}
</head>
<body>
    <h1>DeepSeek 测试结果 (记录ID: {test_id})</h1>
    <p>测试时间: {test_start_time} ~ {test_end_time}</p>

    <div class="flex-row">
        <div>
            <label for="timeout">超时时间 (秒):</label>
            <input type="number" id="timeout" value="300" min="30" max="600">
        </div>
        <div>
            <label for="prompt">自定义提示词：</label>
            <input type="text" id="prompt" value="{custom_prompt}">
        </div>
        <div>
            <button onclick="triggerTest()">立即执行一轮测试</button>
            <button onclick="setPrompt()">更新提示词</button>
        </div>
    </div>

    {progress_section}

    <div class="toggle-buttons" style="margin-top:20px;">
        <button onclick="toggleColumn('col-response')">Toggle Response JSON</button>
        <button onclick="toggleColumn('col-content')">Toggle Content</button>
        <button onclick="toggleColumn('col-reasoning')">Toggle Reasoning</button>
        <button onclick="toggleColumn('col-time')">Toggle Time</button>
    </div>

    <h2>Round 1 测试结果</h2>
    {r1}
    <h2>Round 2 测试结果</h2>
    {r2}
    <h2>Round 3 测试结果</h2>
    {r3}
    <h2>最终汇总 (剔除离群和出错后)</h2>
    {smry}

    <hr/>
    <p><a href="/history">查看历史记录</a></p>

<script>
function triggerTest() {{
    const timeout = document.getElementById("timeout").value;
    fetch(`/start_test?timeout=${{timeout}}`)
      .then(response => response.text())
      .then(msg => {{ alert(msg); }});
}}

function setPrompt() {{
    const prompt = document.getElementById("prompt").value;
    fetch(`/update_prompt?prompt=${{prompt}}`).then(response => response.text()).then(msg => {{
        alert(msg);
    }});
}}

function toggleColumn(colClass) {{
    const elements = document.getElementsByClassName(colClass);
    for (let i = 0; i < elements.length; i++) {{
        const currentDisplay = window.getComputedStyle(elements[i]).getPropertyValue("display");
        elements[i].style.display = (currentDisplay === "none") ? "table-cell" : "none";
    }}
}}

document.addEventListener("DOMContentLoaded", function() {{
    const headers = document.querySelectorAll("th");
    headers.forEach(function(th) {{
        const text = th.textContent.trim();
        if (text === "Response JSON") {{
            th.classList.add("col-response");
        }} else if (text === "Content") {{
            th.classList.add("col-content");
        }} else if (text === "Reasoning Content") {{
            th.classList.add("col-reasoning");
        }} else if (text === "Input Time") {{
            th.classList.add("col-time");
        }} else if (text === "Output Time") {{
            th.classList.add("col-time");
        }}
    }});
}});

setInterval(() => {{
    fetch("/test_progress").then(res => res.json()).then(data => {{
        const progressBar = document.getElementById("progress-bar");
        const progressText = document.getElementById("progress-text");
        if (!progressBar || !progressText) return;

        if (data.status === "idle") {{
            progressBar.style.width = "0%";
            progressBar.textContent = "0%";
            progressText.textContent = "无测试进行";
        }} else if (data.status === "running") {{
            const totalModels = data.finished_models.length + data.unfinished_models.length;
            const finished = data.finished_models.length;
            let percent = 0;
            if (totalModels > 0) {{
                percent = Math.round((finished / totalModels) * 100);
            }}
            progressBar.style.width = percent + "%";
            progressBar.textContent = percent + "%";

            progressText.innerHTML = `
                当前第 ${{data.current_round}} / ${{data.total_rounds}} 轮 <br/>
                已完成模型: ${{data.finished_models.join(", ")}} <br/>
                未完成模型: ${{data.unfinished_models.join(", ")}}
            `;
        }} else if (data.status === "finished") {{
            progressBar.style.width = "100%";
            progressBar.textContent = "100%";
            progressText.textContent = "全部轮次测试完成";
            setTimeout(() => window.location.reload(), 2000);
        }}
    }});
}}, 2000);
</script>
</body>
</html>
"""
    return html


@app.route("/history")
def history_page():
    """展示所有历史记录的列表"""
    rows = load_all_test_results()
    base_styles = """
    <style>
    body {
        font-family: "Helvetica Neue", Arial, sans-serif;
        margin: 20px;
        color: #333;
    }
    table {
        border: 1px solid #ccc;
        border-collapse: collapse;
        margin: 16px 0;
        width: 100%;
    }
    th, td {
        border: 1px solid #ccc;
        padding: 8px;
        text-align: center;
    }
    th {
        background-color: #f7f7f7;
        font-weight: bold;
    }
    a {
        color: #337ab7;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    button {
        background-color: #5cb85c;
        color: white;
        border: none;
        padding: 6px 12px;
        margin-right: 10px;
        font-size: 14px;
        border-radius: 4px;
        cursor: pointer;
    }
    button:hover {
        background-color: #4cae4c;
    }
    </style>
    """

    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>测试历史记录</title>
    {base_styles}
</head>
<body>
    <h1>测试历史记录</h1>
    <table>
        <tr>
            <th>ID</th>
            <th>测试开始时间</th>
            <th>测试结束时间</th>
            <th>详情</th>
        </tr>
    """
    for row in rows:
        record_id, start_time, end_time = row
        html += f"""
        <tr>
            <td>{record_id}</td>
            <td>{start_time}</td>
            <td>{end_time}</td>
            <td><a href="/result/{record_id}">查看详情</a></td>
        </tr>
        """
    html += """
    </table>
    <p><a href="/">返回最新测试结果</a></p>
</body>
</html>
    """
    return html


@app.route("/result/<int:record_id>")
def result_detail(record_id):
    """展示某一条特定记录的详情"""
    row = load_test_result_by_id(record_id)
    if row is None:
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>记录 {record_id} 未找到</title>
</head>
<body style="font-family:Arial;margin:20px;">
    <h1>记录 {record_id} 未找到</h1>
    <p><a href="/history">返回历史记录</a></p>
</body>
</html>
"""
    _id, test_start_time, test_end_time, r1, r2, r3, smry = row
    base_styles = """
    <style>
    body {
        font-family: "Helvetica Neue", Arial, sans-serif;
        margin: 20px;
        color: #333;
    }
    h1, h2, h3 {
        font-weight: 600;
    }
    .col-response, .col-content, .col-reasoning, .col-time {
        display: none;
    }
    table {
        border: 1px solid #ccc;
        border-collapse: collapse;
        margin: 16px 0;
        width: 100%;
    }
    th, td {
        border: 1px solid #ccc;
        padding: 8px;
        text-align: center;
    }
    th {
        background-color: #f7f7f7;
        font-weight: bold;
    }
    button {
        background-color: #0275d8;
        color: #fff;
        border: none;
        padding: 6px 12px;
        margin-right: 10px;
        font-size: 14px;
        border-radius: 4px;
        cursor: pointer;
    }
    button:hover {
        background-color: #025aa5;
    }
    a {
        color: #337ab7;
        text-decoration: none;
    }
    a:hover {
        text-decoration: underline;
    }
    </style>
    """
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="utf-8">
    <title>测试详情 - 记录 {record_id}</title>
    {base_styles}
</head>
<body>
    <h1>测试详情 - 记录 {record_id}</h1>
    <p>测试开始时间: {test_start_time}</p>
    <p>测试结束时间: {test_end_time}</p>

    <div class="toggle-buttons" style="margin-top:20px;">
        <button onclick="toggleColumn('col-response')">Toggle Response JSON</button>
        <button onclick="toggleColumn('col-content')">Toggle Content</button>
        <button onclick="toggleColumn('col-reasoning')">Toggle Reasoning</button>
        <button onclick="toggleColumn('col-time')">Toggle Time</button>
    </div>

    <h2>Round 1 测试结果</h2>
    {r1}
    <h2>Round 2 测试结果</h2>
    {r2}
    <h2>Round 3 测试结果</h2>
    {r3}
    <h2>最终汇总 (剔除离群和出错后)</h2>
    {smry}
    <hr>
    <p><a href="/history">返回历史记录</a></p>
    <p><a href="/">返回最新测试结果</a></p>
<script>
function toggleColumn(colClass) {{
    const elements = document.getElementsByClassName(colClass);
    for (let i = 0; i < elements.length; i++) {{
        const currentDisplay = window.getComputedStyle(elements[i]).getPropertyValue("display");
        elements[i].style.display = (currentDisplay === "none") ? "table-cell" : "none";
    }}
}}

document.addEventListener("DOMContentLoaded", function() {{
    const headers = document.querySelectorAll("th");
    headers.forEach(function(th) {{
        const text = th.textContent.trim();
        if (text === "Response JSON") {{
            th.classList.add("col-response");
        }} else if (text === "Content") {{
            th.classList.add("col-content");
        }} else if (text === "Reasoning Content") {{
            th.classList.add("col-reasoning");
        }} else if (text === "Input Time") {{
            th.classList.add("col-time");
        }} else if (text === "Output Time") {{
            th.classList.add("col-time");
        }}
    }});
}});
</script>
</body>
</html>
"""
    return html


if __name__ == "__main__":
    init_db()
    # 可按需决定是否启动时先跑一次测试
    # scheduled_job()

    # 启动Flask并自动打开默认浏览器
    webbrowser.open("http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False)

# DeepSeek Api Test 由 Gwaanl 构建，源代码遵循 MIT 协议
