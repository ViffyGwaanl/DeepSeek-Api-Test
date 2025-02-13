#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Api Test
Version: 0.2.0
Author: Gwaanl

测试核心逻辑，包括多轮测试、APS周期任务、后台线程执行等
"""

import time
import json
import datetime
import threading

import requests
import pandas as pd

from db_utils import save_test_result
from utils import logger, detect_outliers_iqr, make_styled_table_html, export_tables_to_image
from models_config import MODELS_CONFIG, MODELS_TO_TEST

# 全局提示词，可以通过接口更新
custom_prompt = f'请用当前时间 {datetime.datetime.now().isoformat()} ，写一首打油诗。'

def set_custom_prompt(prompt: str):
    global custom_prompt
    custom_prompt = prompt


# 全局进度记录
test_progress = {
    "status": "idle",
    "current_round": 0,
    "total_rounds": 3,
    "finished_models": [],
    "unfinished_models": [],
    "lock": threading.Lock()
}

def test_model(model_key, results, round_number, timeout=300, unfinished=None):
    """对单个模型执行测试"""
    config = MODELS_CONFIG[model_key]
    display_name = config["display_name"]
    url = config["url"]
    api_key = config["api_key"]
    model_for_payload = config.get("payload_model", model_key)

    logger.info(f"[Round {round_number}] Start testing: {model_key} ({display_name})")

    input_timestamp_str = datetime.datetime.now().isoformat()
    start_time = time.time()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": model_for_payload,
        "messages": [
            {
                "role": "user",
                "content": custom_prompt
            }
        ],
        "stream": False,
        "response_format": {"type": "text"}
    }

    def timeout_handler():
        logger.info(f"[Round {round_number}] {display_name} timed out.")
        with test_progress["lock"]:
            if unfinished is not None and model_key in unfinished:
                unfinished.remove(model_key)
                if display_name in test_progress["unfinished_models"]:
                    test_progress["unfinished_models"].remove(display_name)
                if display_name not in test_progress["finished_models"]:
                    test_progress["finished_models"].append(display_name)
        results.append({
            "test_round": round_number,
            "model_key": model_key,
            "model_name": display_name,
            "completion_tokens": "Timeout",
            "time_taken": timeout,
            "tokens_per_second": "Error",
            "raw_response": "Request Timed Out",
            "input_timestamp": input_timestamp_str,
            "output_timestamp": datetime.datetime.now().isoformat()
        })
        logger.info(f"[Round {round_number}] Finished: {model_key} ({display_name}) - Timed Out")

    timeout_timer = threading.Timer(timeout, timeout_handler)
    timeout_timer.start()

    completion_tokens = None
    tokens_per_second = None
    raw_response_text = None
    output_timestamp_str = None

    try:
        response = requests.post(url, json=payload, headers=headers, proxies={}, timeout=timeout)
        response.raise_for_status()
        response_json = response.json()
        completion_tokens = response_json.get('usage', {}).get('completion_tokens', 0)
        raw_response_text = response.text
        output_timestamp_str = datetime.datetime.now().isoformat()

        logger.info(f"[Round {round_number}] {display_name} response OK, completion_tokens={completion_tokens}")
    except Exception as e:
        logger.exception(f"[Round {round_number}] {display_name} request error: {e}")
        completion_tokens = None
        raw_response_text = f"{type(e).__name__}: {str(e)}"
        output_timestamp_str = datetime.datetime.now().isoformat()

    end_time = time.time()
    time_taken_val = end_time - start_time

    if isinstance(completion_tokens, int) and time_taken_val > 0 and completion_tokens > 0:
        tokens_per_second = completion_tokens / time_taken_val

    result = {
        "test_round": round_number,
        "model_key": model_key,
        "model_name": display_name,
        "completion_tokens": completion_tokens if completion_tokens is not None else "Error",
        "time_taken": time_taken_val,
        "tokens_per_second": tokens_per_second if tokens_per_second is not None else "Error",
        "raw_response": raw_response_text,
        "input_timestamp": input_timestamp_str,
        "output_timestamp": output_timestamp_str
    }

    with test_progress["lock"]:
        results.append(result)
        if unfinished is not None and model_key in unfinished:
            unfinished.remove(model_key)
        if display_name in test_progress["unfinished_models"]:
            test_progress["unfinished_models"].remove(display_name)
        if display_name not in test_progress["finished_models"]:
            test_progress["finished_models"].append(display_name)

    timeout_timer.cancel()

def run_single_test(model_keys, round_number, timeout=300):
    """执行单轮测试"""
    logger.info(f"======== Start Round {round_number} ========")
    threads = []
    results = []

    with test_progress["lock"]:
        test_progress["current_round"] = round_number
        test_progress["finished_models"] = []
        test_progress["unfinished_models"] = [MODELS_CONFIG[k]["display_name"] for k in model_keys]
        test_progress["status"] = "running"

    unfinished = set(model_keys)
    for key in model_keys:
        thread = threading.Thread(target=test_model, args=(key, results, round_number, timeout, unfinished))
        threads.append(thread)
        thread.start()
        logger.info(f"[Round {round_number}] Started {key}. Unfinished models: {', '.join(unfinished)}")
        time.sleep(0.5)  # 避免所有请求同时发出

    for thread in threads:
        thread.join()

    logger.info(f"======== End Round {round_number} ========")
    return results

def run_all_tests_and_generate_html(timeout=300):
    """
    依次执行三轮测试，并生成每轮的 HTML 表格，以及最终汇总表格的 HTML。
    同时返回每一轮的 DataFrame，方便后续导出时再次生成不含Response/Reasoning的表。
    """
    all_results = []
    total_rounds = 3
    round_html_list = []
    df_rounds = []

    for round_num in range(1, total_rounds + 1):
        round_results = run_single_test(MODELS_TO_TEST, round_num, timeout)
        import pandas as pd
        df_round = pd.DataFrame(round_results)
        df_rounds.append(df_round)
        round_html = make_styled_table_html(df_round, highlight_tps=True, is_summary=False, hide_response_cols=False)
        round_html_list.append(round_html)
        all_results.extend(round_results)

    df_all = pd.DataFrame(all_results)
    df_all['completion_tokens'] = pd.to_numeric(df_all['completion_tokens'], errors='coerce')
    df_all['time_taken'] = pd.to_numeric(df_all['time_taken'], errors='coerce')
    df_all['tokens_per_second'] = pd.to_numeric(df_all['tokens_per_second'], errors='coerce')

    df_all = detect_outliers_iqr(df_all, 'model_key', 'tokens_per_second')
    outlier_count_series = df_all.groupby('model_key')['is_outlier'].sum()

    df_filtered = df_all[~df_all['is_outlier']]
    agg_dict = {'completion_tokens': 'mean', 'time_taken': 'mean', 'tokens_per_second': 'mean'}
    df_summary = df_filtered.groupby(['model_key', 'model_name'], as_index=False).agg(agg_dict)
    df_summary['outlier_count'] = df_summary['model_key'].map(outlier_count_series)

    df_summary_renamed = df_summary.rename(columns={
        'model_key': 'Model Key',
        'model_name': 'Model Name',
        'completion_tokens': 'Avg Completion Tokens',
        'time_taken': 'Avg Time Taken (s)',
        'tokens_per_second': 'Avg Tokens/s (Token/s)',
        'outlier_count': 'Outlier Count'
    })
    df_summary_renamed = df_summary_renamed.sort_values(by='Avg Tokens/s (Token/s)', ascending=False)

    # 生成最终汇总表（web展示时保留所有列）
    summary_html = make_styled_table_html(df_summary_renamed, highlight_tps=False, is_summary=True, hide_response_cols=False)

    return df_rounds, df_summary_renamed, round_html_list, summary_html

def background_test_runner(timeout=300):
    """
    后台线程执行完整的三轮测试并保存结果到数据库。
    测试结束后自动导出4张表到一张图片 (不包含Response JSON等列)。
    """
    global test_progress
    from utils import logger
    import datetime

    try:
        logger.info("=== 后台测试线程：开始执行测试 ===")
        with test_progress["lock"]:
            test_progress["status"] = "running"
        start_ts = datetime.datetime.now().isoformat()

        df_rounds, df_summary, round_html_list, summary_html = run_all_tests_and_generate_html(timeout=timeout)

        end_ts = datetime.datetime.now().isoformat()
        logger.info("=== 后台测试线程：测试完成，开始保存数据库 ===")

        with test_progress["lock"]:
            test_progress["status"] = "finished"
            test_progress["unfinished_models"] = []
            test_progress["finished_models"] = []
            test_progress["current_round"] = test_progress["total_rounds"]

        # 保存到数据库（web展示用）
        save_test_result(
            start_ts,
            end_ts,
            round_html_list[0],
            round_html_list[1],
            round_html_list[2],
            summary_html
        )

        # 导出不包含Response/Content/Reasoning的图片
        export_tables_to_image(df_rounds, df_summary)

        logger.info("=== 后台测试线程：数据库保存完毕，并已导出图片 ===")
    except Exception as e:
        logger.exception(f"后台测试线程异常: {e}")
    finally:
        with test_progress["lock"]:
            test_progress["status"] = "idle"
            test_progress["current_round"] = 0
            test_progress["unfinished_models"] = []
            test_progress["finished_models"] = []

def scheduled_job():
    """
    定时任务（例如每小时执行一次）。
    需在 APScheduler 中配置: @scheduler.task('interval', id='hourly_job', hours=1)
    """
    logger.info("=== APScheduler: Starting scheduled test job (hourly). ===")
    import threading
    thread = threading.Thread(target=background_test_runner, args=(300,))
    thread.start()
