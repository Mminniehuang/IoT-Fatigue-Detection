# IoT-Fatigue-Detection
### 系級：資管三B   學號：112403037   姓名：黃姵慈

![成果照片]()

## 目錄
- [專案簡介](#專案簡介)
- [作品圖片及影片](#作品圖片及影片)
- [元件清單](#元件清單)
- [製作流程與邏輯](#製作流程與邏輯)
- [環境設定](#環境設定)
- [STEP1-實作臉部偵測與分數機制](#step1-實作臉部偵測與分數機制)
- [STEP2-本地警報設置](#step2-本地警報設置)
- [STEP3-建立雲端資料庫](#step3-建立雲端資料庫)
- [STEP4-建立網站](#step4-建立網站)
- [STEP5-語音預測與輸出](#step5-語音預測與輸出)
- [STEP6-運行專案系統](#step6-運行專案系統)
- [可以改善的地方](#可以改善的地方)
- [參考資料](#參考資料)





---

## 專案簡介

基於 RPi4 的穿戴式機車騎士疲勞監測與安全數據系統，針對高時長機車騎士或外送員所設計。

### 解決的痛點
- 行業特性與高壓： 外送員常面臨長時間、高強度的騎行任務，導致生理疲勞累積，容易引發交通安全事故。
- 現有技術限制： 過去的疲勞監測系統 (DMS) 多基於汽車設計，其鏡頭固定距離與角度不適用於機車安全帽內極近距離、大角度俯視角的挑戰。
- 穿戴式困境： 現有穿戴式疲勞監測專案使用紅外線感測器進行閉眼偵測，但可能因遮蔽單眼而帶來危險性，實用性有待研究。
  
### 解決方案
本專案利用 RPi4 的邊緣計算能力結合鏡頭，建立一套非侵入式的疲勞監測系統。

- 核心功能： 透過鏡頭實時偵測微睡眠 (EAR) 和哈欠頻率 (MAR)。
- 決策邏輯： 計算 Safety Score，低於閾值即觸發本地蜂鳴器警報。
- 聯網功能： 將警報事件和 Safety Score 紀錄到雲端，進行數據分析及預測性語音提醒。





---

## 作品圖片及影片
### 成品
![成果照片]()
### Demo 影片
[![video_thumbnail](URL)](YouTube URL)





---

## 元件清單
![元件]()

|元件  |說明|
|-----|----|
|Raspberry Pi 4|邊緣計算核心|
|Pi Camera Module V2 NOIR (標準 FOV)|影像輸入|
|有源蜂鳴器 (Active Buzzer)|本地警報輸出|
|有線耳機|語音輸出|
|安全帽|主體||
|麵包板|1個||
|電阻|1個||
|公母杜邦線|2條||





---

## 製作流程與邏輯
### 系統架構
本專案採用雙環境隔離、雙進程並行的架構，以確保 RPi4 在運行 Dlib 核心 AI 的穩定性和 Web 服務時的兼容性。

- 進程 A (AI Core) : 運行在 Base OS 環境，負責高強度的 CV 運算和硬體 I/O (Pi Camera, Dlib, GPIO Buzzer)
- 進程 B (Web Server) : 運行在 web_env 虛擬環境，負責低衝突的網路服務 (Flask, Sheets API)
- 數據交換： 兩個進程之間通過 Google Sheets (資料庫) 進行間接交流。

![架構圖]()

### 電路圖
![電路圖]()




---

## 環境設定
### 1. Raspberry Pi Buster 作業系統
### 2. Python 3.7

### 3. Base OS：運行 DLIB 核心所必需的環境
#### 安裝 opencv
用於讀取 Pi Camera 影像 (cv2.imshow, cv2.waitKey)、在影像上繪製地標點與 FPS 數值
參考：[https://hackmd.io/HV6hQ2PHSiWlrRsfxC10SA](https://hackmd.io/HV6hQ2PHSiWlrRsfxC10SA)
>安裝CMack  
>```bash
>cd ~/
>wget https://github.com/Kitware/CMake/releases/download/v3.14.4/cmake-3.14.4.tar.gz
>tar xvzf cmake-3.14.4.tar.gz
>cd ~/cmake-3.14.4
>./bootstrap
>make -j4
>sudo make install
>```
>安裝OpenCV
>```bash
>cd ~/
>sudo apt install git libgtk2.0-dev pkg-config libavcodec-dev libavformat-dev >libswscale-dev libatlas-base-dev python3-scipy
>git clone --depth 1 --branch 4.5.2-openvino https://github.com/opencv/opencv.git
>cd opencv && mkdir build && cd build
>cmake –DCMAKE_BUILD_TYPE=Release –DCMAKE_INSTALL_PREFIX=/usr/local ..
>make -j4
>sudo make install
>```

#### 安裝 dlib 庫
用於臉部地標偵測，dlib 提供 68 個地標座標
>安裝編譯依賴項
>```bash
>sudo apt update
>sudo apt install -y build-essential cmake pkg-config libx11-dev libopenblas-dev liblapack-dev libjpeg-dev libpng-dev libtiff-dev libavcodec-dev libavformat-dev libswscale-dev libv4l-dev python3-dev python3-numpy python3-scipy python3-pip
>```
>安裝 dlib 庫 (最耗時的步驟)
>```bash
>pip3 install dlib
>```
>下載 DLIB 68 點權重檔案並解壓縮
>```bash
># 放在專案根目錄
>cd ~/IoT_112403037
>wget [http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2](http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2)
>bzip2 -dk shape_predictor_68_face_landmarks.dat.bz2
>```

#### 安裝 TTS 及播放器
用於語音合成 (將文本轉換為 MP3)、音頻播放
>安裝 gTTS (Text-to-Speech 庫)
>```bash
>pip3 install gTTS
>```
>安裝 mpg321 (Linux 命令行 MP3 播放器)
>```bash
>sudo apt install mpg321
>```

### 4. web_env：為解決 Flask/Pandas/typing 的兼容性衝突，建立隔離的 Web 環境
#### 建立虛擬環境
>安裝虛擬環境工具
>```bash
>sudo apt install python3-venv
>```
>建立虛擬環境
>```bash
>python3 -m venv web_env
>```
>啟動虛擬環境
>```bash
>source web_env/bin/activate
># 成功後會出現：(web_env) user@raspberrypi:~$
>```
#### 安裝 Web 服務依賴項
>```bash
># 安裝兼容版本，解決 Python 3.7 衝突
>pip3 install Werkzeug==2.0.3 Flask==2.0.3 Flask-SocketIO==5.0.1
>pip3 install requests # 數據寫入 Google Forms/CSV
>```




---

## STEP1-實作臉部偵測與分數機制
1. 相機設置
![架構圖]()

2. 提取關鍵點
>```bash
># --- DLIB 68 點地標索引定義 ---
>LEFT_EYE_START, LEFT_EYE_END = 42, 48 # 左眼 6 點
>RIGHT_EYE_START, RIGHT_EYE_END = 36, 42 # 右眼 6 點
>MOUTH_START, MOUTH_END = 48, 68 # 嘴巴 20 點
>def extract_key_points(landmarks):
>    """從 68 點中提取 EAR 和 MAR 所需的關鍵子集"""
>    left_eye_points = landmarks[LEFT_EYE_START:LEFT_EYE_END]
>    right_eye_points = landmarks[RIGHT_EYE_START:RIGHT_EYE_END]
>    mouth_points = landmarks[MOUTH_START:MOUTH_END]    
>    return left_eye_points, right_eye_points, mouth_points
>```
>```bash
># 提取關鍵點
>left_eye, right_eye, mouth = extract_key_points(landmarks)
>```
3. 計算核心指標
>EAR、MAR 計算公式定義
>參考：
>```bash
># 計算眼睛縱橫比 (EAR)
>def calculate_ear(eye):
>    A = dist.euclidean(eye[1], eye[5])
>    B = dist.euclidean(eye[2], eye[4])
>    C = dist.euclidean(eye[0], eye[3])
>    ear = (A + B) / (2.0 * C)
># 計算嘴巴縱橫比 (MAR)
>def calculate_mar(mouth):
>    A = dist.euclidean(mouth[13], mouth[19]) 
>    B = dist.euclidean(mouth[14], mouth[18])
>    C = dist.euclidean(mouth[15], mouth[17])
>    D = dist.euclidean(mouth[0], mouth[6]) # 水平距離
>    mar = (A + B + C) / (3.0 * D)   
>```
>計算核心指標
>```bash
>left_ear = calculate_ear(left_eye) 
>right_ear = calculate_ear(right_eye)
>EAR_AVG = (left_ear + right_ear) / 2.0
>MAR = calculate_mar(mouth)
>```
4. CV2 視窗，顯示狀態資訊
>```bash
>score_color = (0, 255, 0) 
>if score < 70: score_color = (0, 255, 255) # 後續根據實測結果修正
>if score < 40: score_color = (0, 0, 255) # 後續根據實測結果修正
>cv2.putText(image, f"FPS: {global_fps:.1f}", (10, 30), FONT, 0.7, (255, 255, 255), 2)
>cv2.putText(image, f"Score: {score:.0f}", (10, 210), FONT, 0.7, score_color, 2)
>cv2.putText(image, f"EAR: {EAR_AVG:.3f}", (10, 240), FONT, 0.7, score_color, 2)
>cv2.putText(image, f"MAR: {MAR:.3f}", (10, 270), FONT, 0.7, score_color, 2)
>cv2.imshow("EAR/MAR Core Monitoring", image)
>```

5. Safety Score 設計
   
>根據實測結果設定指標臨界值：(最大值-最小值)/2
>```bash
>EAR (眼睛縱橫比)： Critical $\rightarrow$ $\text{EAR} \le 0.22$
>MAR (哈欠頻率)： Warning $\rightarrow$ $\text{MAR} \ge 0.14$
>```
>分數機制設定：
>```bash
>閉眼持續 $\ge 1.5$ 秒：扣 50 分 (15 秒後加回)
>哈欠頻率 1 分鐘內累積 $\ge 3$ 次以上：扣 15 分，這裡設計動態滾動窗口
>```






---

## STEP2-本地警報設置
1. 蜂鳴器接線
蜂鳴器正極 (+) 接 RPi GPIO 26；負極 (-) 接 RPi GND
![蜂鳴器接線]()
2. 核心警報邏輯
```bash
if self.current_score < 40:
  self.buzz_critical(BUZZER)
elif self.current_score < 70:
  self.buzz_warning(BUZZER)
```





---

## STEP3-建立雲端資料庫
1. 建立 Google Sheets
- 創建一個新的 Google 表單
- 建立以下三個「簡答」問題：Alert Type、Safety Score、Timestamp
- 獲取 POST URL 及 欄位 ID ：點擊表單右上角的「傳送」 (Send) $\rightarrow$ 點擊 < > 嵌入 HTML 圖標 $\rightarrow$ 在程式碼中找到完整 URL 以及每個問題的 name 屬性)
  
$\rightarrow$ 將 FORM_URL 和 欄位 ID 貼入 firestore_logging.py
>```bash
># 1. Google 表單的提交 URL (Action URL from 'Embed HTML' share option)
> FORM_URL = "https://docs.google.com/forms/u/0/d/e/1FAIpQLSf_Ui1Ygi-YWXKlHteOS0PNWfLkK4lKGdWw9N-jR2yH1SpG_Q/formResponse" 
># 2. 欄位名稱 (Google Forms 的內部 ID
>FIELD_IDS = {
>    "ALERT_TYPE": "entry.372793363",
>    "SAFETY_SCORE": "entry.63614352",
>    "TIMESTAMP": "entry.924932555",
>}
>```

3. 數據紀錄 (`firestore_logging.py`)
將警報數據 POST 到 Google Forms，實現雲端持久化
>```bash
>def log_alert_to_firestore(alert_type, score, details=""):
>    # 使用 Google Forms POST 請求將資料寫入   
>    if not initialize_firebase():
>        return
>    try:
>        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")       
>        # 建立 POST 數據
>        form_data = {
>            FIELD_IDS["ALERT_TYPE"]: f"{alert_type} ({details})",
>            FIELD_IDS["SAFETY_SCORE"]: str(score),
>            FIELD_IDS["TIMESTAMP"]: current_time,
>            "entry.9999999999": "Rider_A001" # 假設有一個額外欄位用於 rider ID
>        }       
>        # 發送 POST 請求
>        response = requests.post(FORM_URL, data=form_data)
>        response.raise_for_status() # 檢查是否有 HTTP 錯誤       
>        print(f"[SHEETS] {alert_type} 警報已記錄 (HTTP Status: {response.status_code})。")
>    except requests.exceptions.RequestException as e:
>        print(f"[SHEETS ERROR] 寫入 Google Sheets 失敗: {e}")
>        print("請檢查網路連線、FORM_URL 或 FIELD_IDS 是否正確。")        
>    return
>```


4. 數據匯出
獲取 Google Sheets 的 CSV 匯出連結
- 打開 Google Sheets (表單回應的試算表)
- 導航： 點擊 「檔案 (File)」 $\rightarrow$ 「分享 (Share)」 $\rightarrow$ 「發佈到網路 (Publish to the web)」
- 發佈： 選擇 「連結 (Link)」 選項卡
- 將下拉選單中 「整個文件 (Entire Document)」 更改為 「表單回應工作表」
- 將格式從 「網頁」 更改為 「逗號分隔值 (.csv)」
- 點擊 「發佈 (Publish)」，複製生成的 CSV 連結

$\rightarrow$ 這個連結將用於網站 `web_server.py` 中，供網站讀取數據。



---

## STEP4-建立網站
網站用於顯示 Safety Score 和歷史圖表，並作為 JSON 檔案輸出端 (詳見STEP5)。

1. 創建 Web 伺服器 (`web_server.py`)
Web 服務需在 `web_env` 中運行，每 10 秒讀取 Google Sheets CSV 進行數據更新
>```bash
># 從 Google Sheets CSV 讀取數據
>def fetch_and_process_data():
>    try:
>        # 1. 透過 requests 庫獲取 Google Sheets 共享連結的 CSV 數據
>        response = requests.get(SHEETS_CSV_URL)
>        response.raise_for_status() # 檢查是否成功獲取 (HTTP 200)
>        # 2. 將文本數據轉換為 CSV 讀取器物件
>        csv_data = StringIO(response.text)
>        reader = csv.reader(csv_data)
>        headers = next(reader)
>        records = list(reader)
>        ...
>    except Exception as e:
>        print(f"【數據錯誤】處理試算表時發生錯誤: {e}") 
>```

2. 套用 HTML 模板 (`templates/index.html`)
網站前端顯示所有數據，並使用 Chart.js 繪製歷史趨勢圖





---

## STEP5-語音預測與輸出
實現預測性疲勞提醒。透過分析過去的騎行數據，主動給予騎士休息建議，而非僅在發生當下警報。

預測邏輯：依據「前一天同一小時內」是否有警報紀錄，判斷騎士在當前時間區間的高風險疲勞傾向

0. 如果要啟用語音功能，RPi4 必須正確配置音頻輸出至喇叭或耳機：
>確認音頻輸出裝置
>```bash
>sudo raspi-config
>導航至：System Options $\rightarrow$ Audio $\rightarrow$ 選擇：3.5mm Jack (Headphones) $\rightarrow$ OK
>```
>播放系統內建音效檔案進行確認
>```bash
>aplay /usr/share/sounds/alsa/Front_Center.wav
>```

1. 數據來源
>`web_server.py`會定期分析「前一天同一小時內」的數據
>```bash
>def analyze_fatigue_risk(records):
>    now = datetime.now()
>    yesterday = now - timedelta(days=1)
>    # 檢查於前一天同一小時的紀錄
>    ...
>    if alert_count_yesterday > 0:
>        details = f"在昨天的 {target_hour}:00 時段，偵測到 {total_sleep_count} 次閉眼和 >{total_yawn_count} 次哈欠。"
>        return f"警告，根據歷史紀錄，你當前時段為高風險時段。{details}"
>    else:
>        return "狀態良好，繼續保持。"
>```
2. 本地數據快取與 JSON 寫入
>將分析結果（提醒文本）寫入本地 `risk_analysis.json` 檔案
>```bash
># 風險分析與 JSON 寫入
>reminder_text = analyze_fatigue_risk(processed_records)
>risk_data_to_save = {
>    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
>    'reminder': reminder_text,
>}
># 確保 JSON 檔案寫入成功
>try:
>    with open(DATA_CACHE_FILENAME, 'w', encoding='utf-8') as f:
>        json.dump(risk_data_to_save, f, ensure_ascii=False, indent=4)
>    print(f"【數據更新】成功讀取 {len(processed_records)} 筆紀錄，並寫入 {DATA_CACHE_FILENAME}。")
>except Exception as e:
>    print(f"【致命錯誤】JSON 檔案寫入失敗: {e}")
>```
3. 語音提醒線程
>`fatigue_detection_system.py`會啟動一個獨立的語音提醒線程，每 1 分鐘讀取`risk_analysis.json` 檔案，檢查是否有提醒文本
>```bash
>RISK_ANALYSIS_FILE = 'risk_analysis.json'
>def start_reminder_thread():
>    last_reminded_hour = -1 # 追蹤上次播放的小時數
>    def check_and_speak_reminder():
>        nonlocal last_spoken_reminder, last_reminded_hour
>        while True:
>            current_hour = datetime.now().hour # 獲取當前小時
>            try:
>                # 1. 讀取本地 JSON 檔案
>                if not os.path.exists(RISK_ANALYSIS_FILE):
>                    time.sleep(REMINDER_CHECK_INTERVAL); continue
>                with open(RISK_ANALYSIS_FILE, 'r', encoding='utf-8') as f:
>                    risk_data = json.load(f)
>                reminder_text = risk_data.get('reminder')
>                # 2. 核心邏輯：有提醒文本 AND 當前小時尚未播放過
>                if reminder_text and current_hour != last_reminded_hour:
>                    speak_text(f"預測提醒。{reminder_text}")
>                    last_reminded_hour = current_hour # 鎖定當前小時          
>            except Exception as e:
>                print(f"\n[TTS ERROR] 語音提醒線程錯誤: {e}")
>            time.sleep(REMINDER_CHECK_INTERVAL)
>    # 啟動線程：以 daemon=True 確保背景執行   
>    thread = threading.Thread(target=check_and_speak_reminder, daemon=True)
>    thread.start()
>```
4. 語音文本轉語音
>`tts_service.py` 負責將文本轉為 MP3 並播放語音
>```bash
>def speak_text(text):
>    if tts_lock.acquire(blocking=False):
>        mp3_filename = "temp_alert.mp3"
>        try:
>            # 1. gTTS: 生成 MP3 檔案
>            tts = gTTS(text=text, lang='zh-tw')
>            tts.save(mp3_filename)
>            print(f"\n[TTS] 正在播放語音提醒: {text}")
>            # 2. mpg321: 播放 MP3
>            subprocess.Popen(["mpg321", "-q", mp3_filename])
>        except Exception as e:
>            print(f"[TTS ERROR] 語音播放失敗：{e}")
>        finally:
>            threading.Thread(target=lambda: (time.sleep(5), os.remove(mp3_filename), tts_lock.release()), daemon=True).start()
>```




---

## STEP6-運行專案系統
在 RPi4 開啟兩個終端機

1.  啟動 Web Server (數據分析/JSON 輸出)：
```bash
source web_env/bin/activate` # 開啟虛擬環境
python3 web_server.py`
# 點開網址進入網頁
```
2.  啟動 AI Core (疲勞偵測/本地顯示與警報/語音輸出)：
```bash
python3 fatigue_detection_system.py
```




    
---

## 可以改善的地方
1. 性能提升：DLIB 運行在 CPU 上速度較慢 ($\sim 5 \text{ FPS}$)。未來可嘗試使用 OpenCV DNN 模塊載入優化後的 Dlib 權重，或使用 NCS2 加速一個兼容的 CNN 地標模型。
2. 數據魯棒性：增加人臉追踪器 (Tracker) 來穩定 Dlib 邊界框，減少地標跳動。
3. 語音輸出：語音提醒的內容可以根據疲勞的嚴重程度和哈欠次數進行動態調整。




---

## 參考資料

1.  **Soukupová, T., & Čech, J. (2016).** *Real-Time Eye Blink Detection using Facial Landmarks.* (EAR 核心公式的基礎).
2.  **Rosebrock, A.** *Eye Blink Detection with OpenCV, Python, and dlib.* (DLIB 68 點實作與 EAR 閾值應用).
3.  **Google Developers.** *gTTS Library Documentation* (TTS 語音合成服務).
4.  **Google Cloud Platform.** *Google Sheets API V4 Documentation* (數據讀取和寫入的底層原理).
5.  **Kildall, Scott.** *Raspberry Pi GPIO Pinout Guide* (GPIO 和電子元件接線基礎)。
