#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
.360動画をフレームごとに分割して写真を作成するプログラム
GoPro .360動画対応
"""

import cv2
import os
import sys
from pathlib import Path

def split_360_to_frames(video_path, output_dir, basename="frame", ext="jpg", frame_interval=1, resize_rate=1.0):
    """
    .360動画をフレームごとに分割して画像として保存
    
    Args:
        video_path (str): 入力動画ファイルのパス
        output_dir (str): 出力ディレクトリ
        basename (str): 出力ファイルのベース名
        ext (str): 出力画像の拡張子 (jpg, png)
        frame_interval (int): フレーム間隔（1=全フレーム、10=10フレームごと）
        resize_rate (float): リサイズ率（1.0=元サイズ、0.5=半分）
    """
    
    print(f"🎬 Processing 360 video: {video_path}")
    print(f"📁 Output directory: {output_dir}")
    
    # 動画ファイルを開く
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"❌ Error: Cannot open video file: {video_path}")
        return False
    
    # 出力ディレクトリを作成
    os.makedirs(output_dir, exist_ok=True)
    
    # 動画の基本情報を取得
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    duration = total_frames / fps if fps > 0 else 0
    
    print(f"📊 Video Info:")
    print(f"   📐 Resolution: {width}x{height}")
    print(f"   🎯 Total frames: {total_frames}")
    print(f"   ⏱️  FPS: {fps:.2f}")
    print(f"   ⏰ Duration: {duration:.2f} seconds")
    print(f"   📋 Frame interval: every {frame_interval} frames")
    print(f"   🔍 Resize rate: {resize_rate}")
    
    # ファイル名の桁数を決定
    max_frame_num = total_frames // frame_interval
    digit_count = len(str(max_frame_num))
    
    print(f"\n🚀 Starting frame extraction...")
    
    frame_count = 0
    saved_count = 0
    
    while True:
        ret, frame = cap.read()
        
        if not ret:
            break
        
        # 指定したフレーム間隔でのみ処理
        if frame_count % frame_interval == 0:
            # リサイズ処理
            if resize_rate != 1.0:
                new_width = int(width * resize_rate)
                new_height = int(height * resize_rate)
                frame = cv2.resize(frame, (new_width, new_height))
            
            # ファイル名を生成
            frame_filename = f"{basename}_{str(frame_count).zfill(digit_count)}.{ext}"
            frame_path = os.path.join(output_dir, frame_filename)
            
            # 画像を保存
            success = cv2.imwrite(frame_path, frame)
            
            if success:
                saved_count += 1
                if saved_count % 100 == 0:  # 100枚ごとに進捗表示
                    progress = (frame_count / total_frames) * 100
                    print(f"   📸 Saved {saved_count} frames... ({progress:.1f}%)")
            else:
                print(f"   ⚠️  Failed to save: {frame_filename}")
        
        frame_count += 1
    
    # 動画ファイルを解放
    cap.release()
    
    print(f"\n✅ Frame extraction completed!")
    print(f"📸 Total frames saved: {saved_count}")
    print(f"📁 Output directory: {output_dir}")
    
    return True

def main():
    """メイン実行関数"""
    
    # 設定項目
    VIDEO_NAME = "GS010678.360"  # 動画ファイル名
    FRAME_INTERVAL = 30          # フレーム間隔（30フレームごと = 約1秒間隔）
    RESIZE_RATE = 0.5           # リサイズ率（0.5 = 半分のサイズ）
    BASENAME = "frame"          # 出力ファイルのベース名
    EXT = "jpg"                 # 出力画像の拡張子
    
    # パス設定
    script_dir = Path(__file__).parent
    workspace_root = script_dir.parent.parent
    movies_dir = workspace_root / "movies"
    output_dir = script_dir / "output" / "frames"
    
    video_path = movies_dir / VIDEO_NAME
    
    print("🎬 GoPro .360 Video Frame Extractor")
    print("=" * 50)
    
    # 動画ファイルの存在確認
    if not video_path.exists():
        print(f"❌ Video file not found: {video_path}")
        print(f"   📁 Expected location: {movies_dir}")
        print(f"   📋 Available files:")
        if movies_dir.exists():
            for file in movies_dir.iterdir():
                if file.is_file():
                    print(f"      • {file.name}")
        return False
    
    # フレーム分割実行
    success = split_360_to_frames(
        str(video_path),
        str(output_dir),
        basename=BASENAME,
        ext=EXT,
        frame_interval=FRAME_INTERVAL,
        resize_rate=RESIZE_RATE
    )
    
    if success:
        print(f"\n💡 Usage examples:")
        print(f"   📸 View frames: Open {output_dir}")
        print(f"   🔄 Change settings: Edit VIDEO_NAME, FRAME_INTERVAL, RESIZE_RATE in script")
        print(f"   📊 Analyze: python3 analyze_frames.py")
    
    return success

if __name__ == "__main__":
    main()