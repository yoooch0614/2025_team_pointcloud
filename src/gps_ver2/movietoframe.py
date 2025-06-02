import cv2
import numpy as np
import os

# ==== 設定 ====
video_path = os.path.expanduser('~/デスクトップ/pointcloud_ws/movies/GS010692.mov')
output_dir = os.path.expanduser('~/デスクトップ/pointcloud_ws/src/gps_ver2/output/frames')

frame_interval = 15              # 何フレームごとに1枚抽出するか（例：30なら1秒ごと）

# 出力ディレクトリを作成（存在しなければ）
os.makedirs(output_dir, exist_ok=True)

# ==== メイン処理 ====
cap = cv2.VideoCapture(video_path)
frame_id = 0
saved_id = 0

if not cap.isOpened():
    print(f"動画ファイルが開けませんでした: {video_path}")
    exit()

while True:
    ret, frame = cap.read()
    print(f"{ret}")
    print(f"{frame}")
    if not ret:
        break

    # フレーム間引き
    if frame_id % frame_interval == 0:
        # フレームを保存
        filename = os.path.join(output_dir, f'frame_{saved_id:05d}.jpg')
        cv2.imwrite(filename, frame)
        saved_id += 1
      

    frame_id += 1

cap.release()
print("すべての変換が完了しました！")
