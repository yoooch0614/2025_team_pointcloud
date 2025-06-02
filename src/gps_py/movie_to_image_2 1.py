import cv2
import os


def save_all_resize_frames(video_path, output_dir, basename, ext, deltaframe, resize_rate=0.25):
    # 動画ファイルを開く
    cap = cv2.VideoCapture(video_path)

    # 動画ファイルが開けない場合は終了
    if not cap.isOpened():
        print("Error: Unable to open video file.")
        return

    # 出力ディレクトリが存在しない場合は作成
    os.makedirs(output_dir, exist_ok=True)

    # ベースパスの設定
    base_path = os.path.join(output_dir, basename)

    # 全フレーム数の取得
    all_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    digit = len(str(all_frames))
    print("Total frames:", all_frames)

    # フレームの読み込みと処理
    n = 0
    while True:
        ret, frame = cap.read()

        # フレームが取得できない場合は終了
        if not ret:
            break

        # フレーム間隔ごとに処理
        if n % deltaframe == 0:
            print("Processing frame", n)
            # リサイズ
            resized_frame = cv2.resize(
                frame, dsize=None, fx=resize_rate, fy=resize_rate)
            # 画像を保存
            cv2.imwrite('{}_{}.{}'.format(base_path, str(
                n).zfill(digit), ext), resized_frame)

        n += 1

    # 動画ファイルを解放
    cap.release()


if __name__ == '__main__':
    # 使用例
    input_movie = "../school_corridor.MP4"
    output_dir = "project2/test_images"
    basename = 'video_img'
    ext = "jpg"
    deltaframe = 10
    resize_rate = 0.25

    save_all_resize_frames(input_movie, output_dir,
                           basename, ext, deltaframe, resize_rate)
