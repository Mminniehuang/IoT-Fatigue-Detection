# IoT-Fatigue-Detection 物聯網實務應用期末專案-安全帽疲勞偵測系統
### 系級：資管三B   學號：112403037   姓名：黃姵慈

![成果照片](https://hackmd.io/_uploads/rJMk1MYda.jpg)

## 目錄
1. [簡介](#簡介)
2. [作品圖片及影片](#作品圖片及影片)
3. [Step1: 使用設備](#step1-使用設備)
4. [Step2: 環境準備](#step2-環境準備)
5. [Step3: 核心原理與模型](#step3-核心原理與模型)
6. [Step4: 本地警報設置](#step4-本地警報設置)
7. [Step5: 網站建置與數據流](#step5-網站建置與數據流)
8. [Step6: 語音預測與輸出](#step6-語音預測與輸出)
9. [Step7: 整合函式與運行](#step7-整合函式與運行)
10. [可以改善的地方](#可以改善的地方)
11. [參考資料](#參考資料)

---

## 簡介
### 專案概述

本專案旨在解決外送員或高時長機車騎士在工作期間因疲勞導致的安全問題。利用 RPi4 的邊緣計算能力，建立一套非侵入式的頭戴式監測系統。

- 核心功能： 實時偵測微睡眠 (EAR) 和哈欠頻率 (MAR)。
- 決策邏輯： 計算 Safety Score，低於閾值即觸發本地蜂鳴器警報。
- 聯網功能： 將警報事件和 Safety Score 紀錄到雲端，進行數據分析及預測性語音提醒。

### 系統架構

本專案採用雙環境隔離、雙進程並行的架構，以確保 RPi4 在運行 Dlib 核心 AI 的穩定性和 Web 服務時的兼容性。

- 進程 A (AI Core): 運行在 Base OS 環境，負責高強度的 CV 運算和硬體 I/O (Pi Camera, Dlib, GPIO Buzzer)。
- 進程 B (Web Server): 運行在 web_env 虛擬環境，負責低衝突的網路服務 (Flask, Sheets API)。
- 數據交換： 兩個進程之間通過 Google Sheets (資料庫) 進行間接交流。

---

## 作品圖片及影片

---

## Step1: 使用設備

|元件  |說明|
|-----|----|
|Raspberry Pi 4 Model B|邊緣計算核心|
|Pi Camera Module V2 NOIR (標準 FOV)|影像輸入|
|有源蜂鳴器 (Active Buzzer)|本地警報輸出|
|有線耳機|語音輸出|
|安全帽|主體||
|麵包板|0||
|電阻|0||
|公母杜邦線|2條||

---

## Step2: 環境準備
- Raspberry Pi Buster 作業系統
- Python 3.7
- Base OS：運行 DLIB 核心所必需的環境
- web_env：為解決 Flask/Pandas/typing 的兼容性衝突，建立隔離環境

### 基礎依賴安裝 (Base OS)
#### 1. 安裝 opencv   參考[https://hackmd.io/HV6hQ2PHSiWlrRsfxC10SA](https://hackmd.io/HV6hQ2PHSiWlrRsfxC10SA)
安裝CMack  
```bash
cd ~/
wget https://github.com/Kitware/CMake/releases/download/v3.14.4/cmake-3.14.4.tar.gz
tar xvzf cmake-3.14.4.tar.gz
cd ~/cmake-3.14.4
./bootstrap
make -j4
sudo make install
```
安裝OpenCV
```bash
cd ~/
sudo apt install git libgtk2.0-dev pkg-config libavcodec-dev libavformat-dev libswscale-dev libatlas-base-dev python3-scipy
git clone --depth 1 --branch 4.5.2-openvino https://github.com/opencv/opencv.git
cd opencv && mkdir build && cd build
cmake –DCMAKE_BUILD_TYPE=Release –DCMAKE_INSTALL_PREFIX=/usr/local ..
make -j4
sudo make install
```
#### 2. 安裝 dlib 庫 (高耗時步驟)
```bash
pip3 install dlib
```
#### 3. 下載 DLIB 68 點權重，並且解壓縮
```bash
wget [http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2](http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2)
bzip2 -dk shape_predictor_68_face_landmarks.dat.bz2
```
#### 4. TTS 音頻播放器
```bash
pip3 install TTS(?
sudo apt install mpg321
```
### 建立 Web 環境 (web_env)
#### 1. 建立並啟動虛擬環境
```bash
python3 -m venv web_env
source web_env/bin/activate
```
#### 2. 安裝 Web 服務依賴項
```bash
# 鎖定兼容版本，解決 Python 3.7 衝突
pip3 install Werkzeug==2.0.3 Flask==2.0.3 Flask-SocketIO==5.0.1
pip3 install requests # 數據寫入 Google Forms/CSV
```
---

## Step3: 核心原理與模型
### 疲勞指標
根據實測結果設定指標臨界值
- EAR (眼睛縱橫比)： Critical $\rightarrow$ $\text{EAR} \le 0.22$
- MAR (哈欠頻率)： Warning $\rightarrow$ $\text{MAR} \ge 0.14$
### Safety Score 設計
- 閉眼持續 $\ge 1.5$ 秒 (扣 50 分，15 秒後加回)
- 哈欠頻率 1 分鐘內累積 $\ge 3$ 次以上 (扣 15 分)，這裡設計動態滾動窗口

---

## Step4: 本地警報設置
### 蜂鳴器接線
蜂鳴器正極 (+) 接 RPi GPIO 26；負極 (-) 接 RPi GND
![蜂鳴器接線]()
### 核心警報邏輯
```bash
if self.current_score < 40:
  self.buzz_critical(BUZZER)
elif self.current_score < 70:
  self.buzz_warning(BUZZER)
```

---

## Step5: 網站建置與數據流
網站用於顯示 Safety Score 和歷史圖表，並作為 **JSON 檔案輸出端**。

### 數據紀錄 (`firestore_logging.py`)
該模組負責將警報數據 **POST** 到 Google Forms，實現雲端持久化。

### 網站主程式 (`web_server.py`)
Web 服務在 `web_env` 中運行，每 10 秒讀取 Google Sheets CSV。
http://googleusercontent.com/immersive_entry_chip/2

### HTML 模板 (`templates/index.html`)
網站前端顯示所有數據，並使用 **Chart.js** 繪製歷史趨勢圖。

http://googleusercontent.com/immersive_entry_chip/3
---

## Step6: 語音預測與輸出
通過隔離的背景線程實現，以避免阻塞主 CV 迴圈。

### 預測原理 (前一天同一小時)
- 分析： `web_server.py` 定期分析 Google Sheets 數據，檢查 **「前一天同一小時」 內是否有警報紀錄。
- 輸出： 將分析結果（提醒文本）寫入本地 **`risk_analysis.json` 檔案。

### 7.2 語音提醒線程 (`fatigue_detection_system.py` 內部)

AI 核心程式啟動一個線程，每 30 秒讀取 JSON 檔案。


http://googleusercontent.com/immersive_entry_chip/4
---

## Step7: 整合函式與運行
最終運行步驟 (雙進程並行)
1.  啟動 Web Server (數據分析/JSON 輸出)：
    `source web_env/bin/activate`
    `python3 web_server.py`
2.  啟動 AI Core (偵測/語音/本地顯示)：
    `python3 fatigue_detection_system.py`
    
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
