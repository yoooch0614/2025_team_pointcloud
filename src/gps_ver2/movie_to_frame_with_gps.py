import cv2
import numpy as np
import os
import pandas as pd

# ==== 設定 ====
video_path = os.path.expanduser('~/デスクトップ/pointcloud_ws/movies/GS010692.mov')
csv_path = os.path.expanduser('~/デスクトップ/pointcloud_ws/src/gps_ver2/output/GS010692_telemetry.csv')
output_dir = os.path.expanduser('~/デスクトップ/pointcloud_ws/src/gps_ver2/output/frames_with_gps')
frame_interval = 15  # 何フレームごとに1枚抽出するか

# ==== 出力ディレクトリの作成 ====
os.makedirs(output_dir, exist_ok=True)

# ==== CSVのGPSデータ読み込み ====
df = pd.read_csv(csv_path)

# ==== 動画読み込み ====
cap = cv2.VideoCapture(video_path)
frame_id = 0
saved_id = 0

if not cap.isOpened():
    print(f"動画ファイルが開けませんでした: {video_path}")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    if frame_id % frame_interval == 0:
        # 対応するGPSデータの行を取得
        if saved_id < len(df):
            gps_row = df.iloc[saved_id]
            lat = gps_row.get('latitude', None)
            lon = gps_row.get('longitude', None)
            alt = gps_row.get('altitude', None)

            # GPS情報を画像上に描画
            if lat is not None and lon is not None:
                text = f"Lat: {lat:.6f}, Lon: {lon:.6f}, Alt: {alt:.2f}m"
                cv2.putText(frame, text, (20, 50), cv2.FONT_HERSHEY_SIMPLEX,
                            1.0, (0, 255, 0), 2, cv2.LINE_AA)

        # フレームを保存
        filename = os.path.join(output_dir, f'frame_{saved_id:05d}.jpg')
        cv2.imwrite(filename, frame)
        saved_id += 1

    frame_id += 1

cap.release()
print("すべてのフレーム変換とGPS描画が完了しました！")
