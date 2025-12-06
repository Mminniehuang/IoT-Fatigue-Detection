# -*- coding: utf-8 -*-
"""
專案: 外送員疲勞偵測系統
檔案: fatigue_detection_system.py
目的: 整合 DLIB 核心邏輯、Safety Score 判斷、蜂鳴器警報，以及 TTS 語音提醒。
      **已修正：加入「每小時鎖定」機制，防止語音提醒重複播放。**
"""
import numpy as np
import cv2
import dlib
import time
import picamera
import picamera.array
import threading
from gpiozero import Buzzer
from imutils import face_utils
import json
import os
from datetime import datetime

# 從外部檔案匯入所有工具和常數
try:
    from fatigue_utils import (
        landmarks_to_np, 
        extract_key_points, 
        calculate_ear, 
        calculate_mar,
        FatigueState 
    )
    from tts_service import speak_text # 引入語音播放服務
except ImportError as e:
    print(f"錯誤: 無法匯入必要的模組。請確認 fatigue_utils.py/tts_service.py 存在。錯誤: {e}")
    exit()

# --- 1. 系統配置與硬體定義 ---
RESOLUTION = (640, 480)
FRAME_RATE = 30
FONT = cv2.FONT_HERSHEY_SIMPLEX
DLIB_MODEL_PATH = "shape_predictor_68_face_landmarks.dat" 
BUZZER_PIN = 26 

# --- 語音提醒設定 ---
RISK_ANALYSIS_FILE = 'risk_analysis.json' # Web Server 寫入的檔案
REMINDER_CHECK_INTERVAL = 30 # 每 30 秒檢查一次是否有預測提醒

# 初始化 Buzzer
try:
    BUZZER = Buzzer(BUZZER_PIN)
except Exception as e:
    class DummyBuzzer:
        def off(self): pass
        def is_active(self): return False
        def on(self): pass
    BUZZER = DummyBuzzer()


# --- 2. 語音提醒線程 ---
def start_reminder_thread():
    """在背景執行，定期讀取 JSON 檔案並檢查是否有提醒文本"""
    
    # 追蹤上次播放語音的內容和時間
    last_spoken_reminder = "" 
    last_reminded_hour = -1 # 追蹤上次播放的小時數
    
    def check_and_speak_reminder():
        nonlocal last_spoken_reminder, last_reminded_hour
        
        while True:
            current_time = time.time()
            current_hour = datetime.now().hour # 獲取當前小時
            
            try:
                if not os.path.exists(RISK_ANALYSIS_FILE):
                    time.sleep(REMINDER_CHECK_INTERVAL)
                    continue

                with open(RISK_ANALYSIS_FILE, 'r', encoding='utf-8') as f:
                    risk_data = json.load(f)
                
                reminder_text = risk_data.get('reminder')
                
                # 3. 判斷是否達到提醒閾值，且不在冷卻期內
                if reminder_text and current_hour != last_reminded_hour:
                    
                    # 只有在新的小時 AND 文本內容發生變化時才播放
                        
                    speak_text(f"預測提醒。{reminder_text}")
                    last_spoken_reminder = reminder_text 
                    last_reminded_hour = current_hour # 鎖定當前小時
                        
            except Exception as e:
                # 如果 Web Server 尚未啟動或 JSON 格式錯誤，則跳過
                print(f"\n[TTS ERROR] 語音提醒線程錯誤: {e}")
            
            # 每隔 REMINDER_CHECK_INTERVAL 秒檢查一次
            time.sleep(REMINDER_CHECK_INTERVAL)
            
    thread = threading.Thread(target=check_and_speak_reminder, daemon=True)
    thread.start()


# --- 3. DLIB & OpenCV 初始化 ---

def initialize_dlib():
    """初始化 Dlib 偵測器和預測器"""
    global detector, predictor
    detector = dlib.get_frontal_face_detector()
    try:
        predictor = dlib.shape_predictor(DLIB_MODEL_PATH)
    except Exception as e:
        print(f"錯誤: 無法載入 DLIB 權重檔案。請確認 {DLIB_MODEL_PATH} 位於專案根目錄。錯誤: {e}")
        exit()

# --- 4. 系統主迴圈 ---
def main_pipeline():
    initialize_dlib()
    
    # --- 啟動語音提醒線程 ---
    start_reminder_thread()

    state = FatigueState() # 狀態追蹤器
    
    global_fps = 1.0 # 滾動平均 FPS
    last_frame_time = time.time()
    FPS_SMOOTHING_FACTOR = 0.8 # 平滑係數
    
    # 初始化 PiCamera
    try:
        with picamera.PiCamera() as camera:
            camera.resolution = RESOLUTION
            camera.rotation = 180 
            camera.framerate = FRAME_RATE
            
            with picamera.array.PiRGBArray(camera, size=RESOLUTION) as output:
                
                print("\n--- EAR/MAR 疲勞監測系統啟動 ---")
                
                for frame_raw in camera.capture_continuous(output, format="bgr", use_video_port=True):
                    
                    current_time = time.time()
                    
                    # --- 動態 FPS 計算 ---
                    frame_duration = current_time - last_frame_time
                    last_frame_time = current_time
                    current_fps = 1.0 / frame_duration
                    global_fps = (global_fps * FPS_SMOOTHING_FACTOR) + (current_fps * (1 - FPS_SMOOTHING_FACTOR))
                    
                    image = frame_raw.array
                    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                    rects = detector(gray, 0)
                    
                    EAR_AVG = 0.0
                    MAR = 0.0
                    score = state.current_score
                    
                    if len(rects) > 0:
                        rect = rects[0] 
                        shape = predictor(gray, rect)
                        landmarks = landmarks_to_np(shape)
                        
                        # 提取關鍵點
                        left_eye, right_eye, mouth = extract_key_points(landmarks)
                        
                        # 5. 計算核心指標
                        left_ear = calculate_ear(left_eye) 
                        right_ear = calculate_ear(right_eye)
                        EAR_AVG = (left_ear + right_ear) / 2.0
                        MAR = calculate_mar(mouth)
                        
                        # 7. 決策與警報 - **傳遞實際 FPS**
                        score = state.update_score_and_alert(EAR_AVG, MAR, current_time, global_fps, BUZZER)
                        
                        # 繪製所有 68 個地標點 (輔助驗證)
                        for (x, y) in landmarks:
                            cv2.circle(image, (x, y), 1, (0, 0, 255), -1)


                    # 8. 顯示狀態資訊 (CV2 視窗)
                    
                    score_color = (0, 255, 0) 
                    if score < 70: score_color = (0, 255, 255)
                    if score < 40: score_color = (0, 0, 255)
                    
                    cv2.putText(image, f"FPS: {global_fps:.1f}", (10, 30), FONT, 0.7, (255, 255, 255), 2)
                    cv2.putText(image, f"Score: {score:.0f}", (10, 210), FONT, 0.7, score_color, 2)
                    cv2.putText(image, f"EAR: {EAR_AVG:.3f}", (10, 240), FONT, 0.7, score_color, 2)
                    cv2.putText(image, f"MAR: {MAR:.3f}", (10, 270), FONT, 0.7, score_color, 2)

                    cv2.imshow("EAR/MAR Core Monitoring", image)

                    output.truncate(0)
                    if cv2.waitKey(1) & 0xFF == ord('q'):
                        break

        cv2.destroyAllWindows()
    except Exception as e:
        print(f"主程序發生致命錯誤: {e}")
        
if __name__ == '__main__':
    try:
        start_reminder_thread()
        main_pipeline()
    except KeyboardInterrupt:
        print("\n使用者中斷程式。")
    finally:
        if 'BUZZER' in globals() and BUZZER.is_active:
            BUZZER.off()
        print("資源已釋放。")