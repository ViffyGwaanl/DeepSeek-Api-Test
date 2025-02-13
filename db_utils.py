#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek Api Test
Version: 0.2.0
Author: Gwaanl

数据库相关的初始化与读写函数
"""

import sqlite3

DB_PATH = "results.db"

def init_db():
    """初始化数据库，创建测试结果表（保留所有记录）"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        CREATE TABLE IF NOT EXISTS test_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_start_time TEXT,
            test_end_time TEXT,
            round1_html TEXT,
            round2_html TEXT,
            round3_html TEXT,
            summary_html TEXT
        )
        """)
        conn.commit()

def save_test_result(start_time, end_time, round1_html, round2_html, round3_html, summary_html):
    """保存测试结果到数据库（不删除旧记录）。"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        INSERT INTO test_results 
        (test_start_time, test_end_time, round1_html, round2_html, round3_html, summary_html)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (start_time, end_time, round1_html, round2_html, round3_html, summary_html))
        conn.commit()

def load_latest_test_result():
    """读取最新的一条测试记录"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        SELECT id, test_start_time, test_end_time, round1_html, round2_html, round3_html, summary_html
        FROM test_results ORDER BY id DESC LIMIT 1
        """)
        row = c.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "test_start_time": row[1],
        "test_end_time": row[2],
        "round1_html": row[3],
        "round2_html": row[4],
        "round3_html": row[5],
        "summary_html": row[6],
    }

def load_all_test_results():
    """读取所有测试记录（按 id 倒序）"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        SELECT id, test_start_time, test_end_time FROM test_results ORDER BY id DESC
        """)
        rows = c.fetchall()
    return rows

def load_test_result_by_id(record_id):
    """根据记录ID读取一条测试记录"""
    with sqlite3.connect(DB_PATH) as conn:
        c = conn.cursor()
        c.execute("""
        SELECT id, test_start_time, test_end_time, round1_html, round2_html, round3_html, summary_html
        FROM test_results WHERE id = ?
        """, (record_id,))
        row = c.fetchone()
    return row
