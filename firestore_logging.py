# -*- coding: utf-8 -*-
"""
firestore_logging.py
使用 Google Forms API 處理數據紀錄。
"""
import requests
import json
import time 
from datetime import datetime

# 1. Google 表單的提交 URL (Action URL from 'Embed HTML' share option)
FORM_URL = "https://docs.google.com/forms/u/0/d/e/1FAIpQLSf_Ui1Ygi-YWXKlHteOS0PNWfLkK4lKGdWw9N-jR2yH1SpG_Q/formResponse" 

# 2. 欄位名稱 (Google Forms 的內部 ID
FIELD_IDS = {
    "ALERT_TYPE": "entry.372793363",
    "SAFETY_SCORE": "entry.63614352",
    "TIMESTAMP": "entry.924932555",
}
def initialize_firebase():
    # 虛擬初始化，檢查 URL 是否已配置
    if "YOUR_GOOGLE_FORM_SUBMIT_URL" in FORM_URL:
        print("[SHEETS ERROR] 請先在 firestore_logging.py 中填寫 FORM_URL 和 FIELD_IDS！")
        return False
    print("[SHEETS] Google Sheets API (Forms) 服務已準備就緒。")
    return True

def log_alert_to_firestore(alert_type, score, details=""):
    # 使用 Google Forms POST 請求將資料寫入
    
    if not initialize_firebase():
        return

    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 建立 POST 數據
        form_data = {
            FIELD_IDS["ALERT_TYPE"]: f"{alert_type} ({details})",
            FIELD_IDS["SAFETY_SCORE"]: str(score),
            FIELD_IDS["TIMESTAMP"]: current_time,
            "entry.9999999999": "Rider_A001" # 假設有一個額外欄位用於 rider ID
        }
        
        # 發送 POST 請求
        response = requests.post(FORM_URL, data=form_data)
        response.raise_for_status() # 檢查是否有 HTTP 錯誤
        
        print(f"[SHEETS] {alert_type} 警報已記錄 (HTTP Status: {response.status_code})。")

    except requests.exceptions.RequestException as e:
        print(f"[SHEETS ERROR] 寫入 Google Sheets 失敗: {e}")
        print("請檢查網路連線、FORM_URL 或 FIELD_IDS 是否正確。")
        
    return
