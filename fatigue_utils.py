# -*- coding: utf-8 -*-
"""
fatigue_utils.py
包含 EAR/MAR 幾何計算、地標點提取，以及 Safety Score 的 FatigueState 邏輯。
"""
import numpy as np
from scipy.spatial import distance as dist
from imutils import face_utils
import time
import threading
from math import degrees, atan2, sqrt

# 引入 Firestore 紀錄模組
try:
    from firestore_logging import log_alert_to_firestore
except ImportError:
    # 設置一個空的函式，如果檔案不存在，程式碼仍然可以運行，但不會紀錄
    def log_alert_to_firestore(*args, **kwargs):
        print("[LOGGING] 警告：firestore_logging 模組未載入，紀錄功能被跳過。")
        
# --- DLIB 68 點地標索引定義 ---
LEFT_EYE_START, LEFT_EYE_END = 42, 48 # 左眼 6 點
RIGHT_EYE_START, RIGHT_EYE_END = 36, 42 # 右眼 6 點
MOUTH_START, MOUTH_END = 48, 68 # 嘴巴 20 點

# --- 1. 地標轉換與提取 ---

def landmarks_to_np(shape):
    """將 Dlib shape 結構轉換為 NumPy 數組"""
    coords = np.zeros((68, 2), dtype="int")
    for i in range(0, 68):
        coords[i] = (shape.part(i).x, shape.part(i).y)
    return coords


def extract_key_points(landmarks):
    """從 68 點中提取 EAR 和 MAR 所需的關鍵子集"""
    left_eye_points = landmarks[LEFT_EYE_START:LEFT_EYE_END]
    right_eye_points = landmarks[RIGHT_EYE_START:RIGHT_EYE_END]
    mouth_points = landmarks[MOUTH_START:MOUTH_END]
    
    return left_eye_points, right_eye_points, mouth_points


# --- 2. 核心幾何計算 ---

def calculate_ear(eye):
    """計算眼睛縱橫比 (EAR)"""
    A = dist.euclidean(eye[1], eye[5])
    B = dist.euclidean(eye[2], eye[4])
    C = dist.euclidean(eye[0], eye[3])
    ear = (A + B) / (2.0 * C)
    
    # Debug 輸出
    if ear <= 0.22 :
        print(f"\n[DEBUG EAR] EAR: {ear:.4f}\n")
    return ear


def calculate_mar(mouth):
    """計算嘴巴縱橫比 (MAR)"""
    A = dist.euclidean(mouth[13], mouth[19]) 
    B = dist.euclidean(mouth[14], mouth[18])
    C = dist.euclidean(mouth[15], mouth[17])
    D = dist.euclidean(mouth[0], mouth[6]) # 水平距離

    mar = (A + B + C) / (3.0 * D)
    
    # Debug 輸出
    if mar >= 0.15 :
        print(f"\n[DEBUG MAR]  MAR: {mar:.4f}\n")
    return mar


# --- 3. Safety Score 邏輯核心 ---

class FatigueState:
    """用於追蹤跨幀累積數據的狀態類別"""
    def __init__(self):
        # 實測校準閾值
        self.FRAME_RATE = 30.0 
        self.CLOSED_EAR_THRESHOLD = 0.22  # EAR 閉眼判斷實測閾值 
        self.YAWN_MAR_THRESHOLD = 0.15    # 哈欠判斷實測閾值 
        
        # 時序參數 
        self.MICRO_SLEEP_SEC = 1.5 
        self.PENALTY_RESET_SEC = 15.0 # 15 秒後分數加回
        self.YAWN_CONSEC_SEC = 1  # 哈欠持續 1 秒才算有效
        self.YAWN_WINDOW_SEC = 60.0 # 滾動窗口 60 秒
        self.YAWN_CRITICAL_COUNT = 2 # 1 分鐘內超過 2 次哈欠

        # 實時計數器
        self.closed_counter = 0
        self.current_score = 100
        self.last_alert_time = 0 
        
        # 懲罰旗標，確保單一事件只扣分一次
        self.ear_penalty_applied = False
        self.yawn_freq_penalty_applied = False
        
        # MAR 相關追蹤
        self.yawn_frame_counter = 0 # 單次哈欠持續幀數
        self.is_yawning = False     # 哈欠正在發生中
        
        # 滾動窗口追蹤 (用於 MAR 累積)
        self.yawn_timestamps = [] # 儲存每次有效哈欠發生的時間戳記 (time.time())
        self.last_alert_level = 0 
        self.last_yawn_output_count = 0 # 追蹤上一次輸出的哈欠計數

    def buzz_warning(self, BUZZER):
        """模擬 Warning 警報模式 (輕微、慢速蜂鳴)"""
        if self.last_alert_level < 1:
            self.last_alert_level = 1
            threading.Thread(target=lambda: (BUZZER.on(), time.sleep(0.3), BUZZER.off(), time.sleep(0.8), BUZZER.on(), time.sleep(0.3), BUZZER.off(), time.sleep(1.0), self.__reset_alert_level(1))).start()

    def buzz_critical(self, BUZZER):
        """模擬 Critical 警報模式 (快速、連續強烈蜂鳴)"""
        if self.last_alert_level < 2:
            self.last_alert_level = 2
            threading.Thread(target=lambda: (
                BUZZER.on(), time.sleep(0.1), BUZZER.off(), time.sleep(0.1),
                BUZZER.on(), time.sleep(0.1), BUZZER.off(), time.sleep(0.1),
                BUZZER.on(), time.sleep(0.1), BUZZER.off(), time.sleep(2.0), self.__reset_alert_level(2)
            )).start()
            
    def __reset_alert_level(self, level_completed):
        if self.last_alert_level == level_completed:
            self.last_alert_level = 0
            
    def update_score_and_alert(self, ear, mar, current_time, current_fps, BUZZER):
        micro_sleep_frames = int(self.MICRO_SLEEP_SEC * current_fps)
        micro_sleep_frames = max(1, micro_sleep_frames) 
        
        is_alert = False
        score_deduction = 0
        old_yawn_count = len(self.yawn_timestamps)

        # --- 1. 分數加回邏輯 (15 秒後加回分數) ---
        if self.current_score < 100 and (current_time - self.last_alert_time) >= self.PENALTY_RESET_SEC and self.ear_penalty_applied == True:
            self.current_score += 50
            self.ear_penalty_applied = False
            print("\n[RESET]  15秒已過，Safety Score 加回 50 。\n", end="")
        
        # --- A. EAR (眼睛) 判斷與扣分 ---
        is_eye_closed = ear < self.CLOSED_EAR_THRESHOLD
        
        if is_eye_closed:
            self.closed_counter += 1
        else:
            self.closed_counter = 0
        
        # 臨界警報：微睡眠 (> 1.5s 持續閉眼)
        if self.closed_counter >= micro_sleep_frames:
            if not self.ear_penalty_applied:
                self.current_score -= 50 # 扣除 50 點
                self.last_alert_time = current_time 
                self.ear_penalty_applied = True 
                is_alert = True
                # 數據記錄寫入 Sheets
                log_alert_to_firestore("CRITICAL_SLEEP", self.current_score, f"EAR:{ear:.3f} 閉眼持續超過 {self.MICRO_SLEEP_SEC} 秒")
                print(f"\n[ALERT-CRIT]  微睡眠確認 (持續 {self.closed_counter} 幀). 扣分: 50\n", end="")

        # --- B. MAR (哈欠) 判斷與累積 ---
        is_yawning_frame = mar > self.YAWN_MAR_THRESHOLD
        
        if is_yawning_frame:
            self.yawn_frame_counter += 1
            
            # 判斷是否為一個"有效"的哈欠 (持續 0.7 秒)
            if self.yawn_frame_counter >= int(self.YAWN_CONSEC_SEC * current_fps) and not self.is_yawning:
                self.yawn_timestamps.append(current_time) # 記錄哈欠時間
                self.is_yawning = True # 標記為正在哈欠中，避免重複計數
                print(f"\n[YAWN-VALID]  偵測到一次有效哈欠。\n", end="")
        elif not is_yawning_frame:
            self.yawn_frame_counter = 0
            self.is_yawning = False

        # 滾動窗口管理 (移除過期的哈欠時間戳)
        self.yawn_timestamps = [t for t in self.yawn_timestamps if current_time - t < self.YAWN_WINDOW_SEC]
        
        current_yawn_count = len(self.yawn_timestamps)
        
        # 2. 中度警報：哈欠頻率判斷 (> 2 次 / 60 秒)
        if current_yawn_count > self.YAWN_CRITICAL_COUNT:
            if not self.yawn_freq_penalty_applied:
                self.current_score -= 15 # 扣除 15 點
                self.yawn_freq_penalty_applied = True
                is_alert = True
                # 數據記錄寫入 Sheets
                log_alert_to_firestore("WARNING_YAWN_FREQUENCY", self.current_score, f"一分鐘內哈欠 {current_yawn_count} 次")
                print(f"\n[ALERT-WARN]  哈欠頻率過高 ({current_yawn_count} 次/分鐘). 扣分: 15\n", end="")
        elif current_yawn_count <= self.YAWN_CRITICAL_COUNT:
            if self.yawn_freq_penalty_applied:
                self.current_score += 15 # 分數加回 15 點
                self.yawn_freq_penalty_applied = False
                # 確保只在哈欠累積恢復正常時才輸出
                print(f"\n[RESET-WARN]  哈欠頻率恢復正常 ({current_yawn_count} 次). 分數加回 15 點。\n", end="")
        
        # --- C. 最終輸出 ---
        self.current_score = max(0, self.current_score)

        # 只有當 EAR Frame 正在累積 OR Yawn Count 發生變化 OR 發生警報/重置時才輸出
        should_print_status = self.closed_counter > 0 or current_yawn_count != self.last_yawn_output_count

        if should_print_status:
            print(f"\r[STATUS] EAR Frame: {self.closed_counter}/{micro_sleep_frames} | Yawn Count: {current_yawn_count} | Score: {self.current_score}                          ", end="")
            # 必須更新 last_yawn_output_count
            self.last_yawn_output_count = current_yawn_count

        if is_alert:
            if self.current_score < 40:
                self.buzz_critical(BUZZER)
            elif self.current_score < 70:
                self.buzz_warning(BUZZER)
        
        return self.current_score
