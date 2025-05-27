import os
import time
import threading
import subprocess
import re
import shutil  # 用於移動文件
import pymysql # 用於連接 MySQL 資料庫

# 設定標準輸出編碼為 UTF-8
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 設定影片資料夾路徑
video_folder = '影片/videos/'  # 假設影片匯入至此資料夾
processed_video_folder = '影片/processed_videos/'  # 儲存處理後影片的資料夾
stop_flag = False  # 控制自動偵測是否停止

# 確保永久儲存資料夾存在
if not os.path.exists(processed_video_folder):
    os.makedirs(processed_video_folder)

# 連接資料庫
def connect_db():
    return pymysql.connect(host='localhost', user='root', password='', database='betta_fish')

# 儲存影片資訊到資料庫
def save_video_to_db(video1_path, video2_path):
    conn = connect_db()
    cursor = conn.cursor()
    sql = "INSERT INTO video_records (top_view_video, side_view_video, created_at) VALUES (%s, %s, NOW())"
    cursor.execute(sql, (video1_path, video2_path))

    conn.commit()
    cursor.close()
    conn.close()
    print(f"已將影片 {video1_path}, {video2_path} 儲存至資料庫")

# 自動偵測影片並執行步驟的函數
def auto_detect():
    global stop_flag
    while not stop_flag:
        print("自動偵測影片資料夾中...<br>")

        # 偵測是否有新影片匯入
        video_files = [f for f in os.listdir(video_folder) if f.endswith(('.mp4', '.avi', '.mov'))]
        
        # 過濾出俯視和平視的影片
        top_view_video = None
        side_view_video = None
        
        for video_file in video_files:
            if "-2" in video_file:
                top_view_video = video_file
            elif "-1" in video_file:
                side_view_video = video_file

        if top_view_video and side_view_video:
            video1_path = os.path.join(video_folder, top_view_video)  # 俯視
            video2_path = os.path.join(video_folder, side_view_video)  # 平視

            print(f"處理俯視影片: {video1_path}<br>")
            print(f"處理平視影片: {video2_path}<br>")

            # 1. 修改 3-2d_tracking.py 影片路徑，並執行生成 2D 軌跡數據
            with open('三維軌跡/3-2d_tracking.py', 'r', encoding='utf-8') as file:
                code = file.read()

            # 使用正則表達式動態替換當下的 video1_path 和 video2_path 值
            new_code = re.sub(r'video1_path\s*=\s*".*?"', f'video1_path = "{video1_path}"', code)
            new_code = re.sub(r'video2_path\s*=\s*".*?"', f'video2_path = "{video2_path}"', new_code)

            with open('三維軌跡/3-2d_tracking.py', 'w', encoding='utf-8') as file:
                file.write(new_code)

            print("修改影片路徑，並開始執行 2D 軌跡數據生成...")
            subprocess.run(['python', '三維軌跡/3-2d_tracking.py'])  # 執行 3-2d_tracking.py

            # 2. 執行 4-3d_tracking.py 生成 3D 軌跡數據
            print("開始執行 3D 軌跡數據生成...")
            subprocess.run(['python', '三維軌跡/4-3d_tracking.py'])  # 執行 4-3d_tracking.py

            # 3. 執行 trajectory_plot.py 生成 HTML 並匯入資料庫
            print("開始生成 3D 軌跡圖並匯入資料庫...")
            subprocess.run(['python', '網頁/trajectory_plot.py'])  # 執行 trajectory_plot.py

            # 將影片移動到永久儲存的資料夾
            new_video1_path = os.path.join(processed_video_folder, top_view_video)
            new_video2_path = os.path.join(processed_video_folder, side_view_video)
            shutil.move(video1_path, new_video1_path)
            shutil.move(video2_path, new_video2_path)

            print(f"已將影片移動至 {new_video1_path}, {new_video2_path}")

            # 儲存移動後的影片資訊到資料庫
            save_video_to_db(new_video1_path, new_video2_path)

        else:
            print("沒有找到俯視或平視影片，稍後再次檢查...")

        # 每 30 秒重新檢測一次資料夾
        time.sleep(30)

# 監聽用戶輸入來控制停止偵測
def stop_by_user_input():
    global stop_flag
    input("輸入任意鍵來停止自動偵測: ")
    stop_flag = True

# 啟動自動偵測與用戶輸入監聽
t1 = threading.Thread(target=auto_detect)
t2 = threading.Thread(target=stop_by_user_input)

t1.start()
t2.start()

t1.join()
t2.join()

print("<br>自動偵測已停止。")
