# -*- coding: utf-8 -*-
"""
專案: 外送員疲勞偵測系統
檔案: tts_service.py
目的: 處理語音提醒的生成與播放 (gTTS 和 mpg321)。
"""
from gtts import gTTS
import os
import subprocess
import threading
import time

tts_lock = threading.Lock() 

def speak_text(text):
    # 將文本轉換為語音並透過 RPi 的音頻輸出播放。
    if tts_lock.acquire(blocking=False): 
        mp3_filename = "temp_alert.mp3"
        try:
            # 1. gTTS: 生成 MP3 檔案
            tts = gTTS(text=text, lang='zh-tw')
            tts.save(mp3_filename)
            
            print(f"\n[TTS] 正在播放語音提醒: {text}")
            
            # 2. mpg321: 播放 MP3
            # -q: 安靜模式
            subprocess.Popen(["mpg321", "-q", mp3_filename])
            
        except subprocess.CalledProcessError:
            print(f"[TTS ERROR] 語音播放失敗：mpg321 指令執行錯誤。")
        except Exception as e:
            print(f"[TTS ERROR] 語音播放失敗：{e}")
        finally:
            threading.Thread(target=lambda: (time.sleep(5), os.remove(mp3_filename), tts_lock.release()), daemon=True).start()
    else:
        # 正在播放中，跳過此次提醒
        pass