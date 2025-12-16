# -*- coding: utf-8 -*-
"""
web_server.py
運行 Flask 網站，從 Google Sheets CSV 鏈接讀取疲勞數據並計算。
"""
from flask import Flask, render_template, jsonify
import requests
import threading
import time
from datetime import datetime, timedelta
import csv
from io import StringIO
import re 
import locale 
from collections import defaultdict 
import json
import os

# 設置中文環境
try:
    locale.setlocale(locale.LC_TIME, 'zh_TW.UTF-8')
except locale.Error:
    try:
        locale.setlocale(locale.LC_TIME, 'zh_TW')
    except locale.Error:
        pass


# --- 配置參數 ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_super_secret_key'

# --- Google Sheets CSV 連結 ---
SHEETS_CSV_URL = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vQyh4KJgf5pxwQ2yTO_AujdmnZVARozHXUjYZ5xVXtWn4xmhh9DyK4VNUmOz0JiEQNlPnOliaMYTzwu/pub?gid=2066603959&single=true&output=csv' # <<<<< 必須替換！
DATA_CACHE_FILENAME = 'risk_analysis.json' # 本地 JSON 檔案名

# 數據快取與鎖定 (用於多線程安全)
data_cache = {}
data_lock = threading.Lock()

# --- 數據分析函式 ---
def analyze_fatigue_risk(records):
    """
    分析前一天的數據，判斷當前小時是否有疲勞慣性。
    返回: 語音提醒文本 (str)
    """
    
    now = datetime.now()
    yesterday = now - timedelta(days=1)
    
    # 專注於前一天同一小時的紀錄
    target_hour = now.hour
    
    alert_count_yesterday = 0
    total_yawn_count = 0
    total_sleep_count = 0
    
    for rec in records:
        if rec['Alert Type'] != 'SAFE':
            timestamp_str = rec['Timestamp']
            
            try:
                # 必須解析為 datetime 物件
                dt_object = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                
                # 檢查是否是昨天的數據 且 小時數匹配
                if dt_object.date() == yesterday.date() and dt_object.hour == target_hour:
                    alert_count_yesterday += 1
                    
                    if 'YAWN' in rec['Alert Type']:
                         total_yawn_count += 1
                    if 'SLEEP' in rec['Alert Type']:
                         total_sleep_count += 1
            except ValueError:
                continue

    if alert_count_yesterday > 0:
        details = f"在昨天的 {target_hour}:00 時段，偵測到 {total_sleep_count} 次閉眼和 {total_yawn_count} 次哈欠。"
        return f"警告，根據歷史紀錄，你當前時段為高風險時段。{details}"
    else:
        return "狀態良好，繼續保持。"


def fetch_and_process_data():
    """從 Google Sheets CSV 讀取數據並計算安全分數和排行榜"""
    global data_cache
    
    try:
        response = requests.get(SHEETS_CSV_URL)
        response.raise_for_status() 
        
        csv_data = StringIO(response.text)
        reader = csv.reader(csv_data)
        
        headers = next(reader)
        records = list(reader)
        
        if not records:
            print("【數據錯誤】CSV 數據為空。")
            return

        # --- 數據清洗與篩選 (讀取過去 48 小時數據以覆蓋前一天) ---
        processed_records = []
        latest_score = 100
        total_alerts = 0
        
        time_48_hours_ago = datetime.now() - timedelta(hours=48)
        
        for row in records:
            if len(row) < 4 or not row[3].strip(): continue 
            
            timestamp_str = row[3].strip() 
            alert_full = row[1].strip()
            score_raw = row[2].strip()
            
            # --- 時間解析修正 ---
            record_time_str = timestamp_str
            
            try:
                record_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                record_time_str = record_time.strftime('%Y-%m-%d %H:%M:%S')
            except ValueError:
                record_time_str = timestamp_str 
            
            # 篩選掉超過 48 小時的數據 (只分析最近兩天)
            if record_time < time_48_hours_ago:
                 continue
            
            alert_type_main = alert_full.split('(')[0].strip()
            
            try:
                score = int(score_raw)
            except ValueError:
                score = 100 
                
            processed_records.append({
                'Timestamp': record_time_str,
                'Alert Type': str(alert_type_main or 'SAFE'),
                'Safety Score': score,
                'Rider_ID': 'Rider_A380' 
            })
            
            latest_score = score
            if alert_type_main != 'SAFE':
                 total_alerts += 1
        
        if not processed_records:
            print("【數據錯誤】無有效紀錄。")
            return
            
        # --- 4. 風險分析與 JSON 寫入 ---
        
        reminder_text = analyze_fatigue_risk(processed_records)
        
        risk_data_to_save = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'reminder': reminder_text,
        }
        
        # 確保 JSON 檔案寫入成功
        try:
            with open(DATA_CACHE_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(risk_data_to_save, f, ensure_ascii=False, indent=4)
            print(f"【數據更新】成功讀取 {len(processed_records)} 筆紀錄，並寫入 {DATA_CACHE_FILENAME}。")
        except Exception as e:
            print(f"【致命錯誤】JSON 檔案寫入失敗: {e}")
        
        # --- 6. 更新網站快取 ---
        safety_level = 'critical' if latest_score < 40 else ('warning' if latest_score < 70 else 'safe')
        rider_stats = [{
            'Rider_ID': 'Rider_A380',
            'latest_score': latest_score,
            'total_alerts': total_alerts,
            'safety_level': safety_level
        }]
        recent_data = processed_records
            
        with data_lock:
            data_cache['rider_stats'] = rider_stats
            data_cache['recent_logs'] = recent_data
            data_cache['last_update'] = datetime.now().strftime("%H:%M:%S")
            data_cache['reminder'] = reminder_text 

    except Exception as e:
        print(f"【數據錯誤】處理試算表時發生錯誤: {e}")


# --- 定期更新數據的背景線程 ---
def start_data_refresh_thread():
    """每 10 秒刷新一次數據"""
    fetch_and_process_data() # 立即執行第一次
    def refresh_data():
        while True:
            time.sleep(10) # 每 10 秒刷新一次
            fetch_and_process_data()
            
    thread = threading.Thread(target=refresh_data)
    thread.daemon = True
    thread.start()


# --- Flask 路由 ---

@app.route('/')
def index():
    if not data_cache or not data_cache.get('rider_stats'):
        return render_template('loading.html') 
        
    return render_template('index.html', 
                           rider_stats=data_cache['rider_stats'],
                           recent_logs=data_cache['recent_logs'],
                           last_update=data_cache.get('last_update', '--'),
                           reminder=data_cache.get('reminder', '正在分析歷史數據...')
                           )

@app.route('/api/status', methods=['GET'])
def api_status():
    with data_lock:
        return jsonify(data_cache)


# --- 啟動 Flask ---
if __name__ == '__main__':
    start_data_refresh_thread()
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
