from fractions import Fraction
import piexif
from PIL import Image
import cv2
import pandas as pd


def to_deg(value, loc):
    """緯度、経度を10進法→60進法(度分秒)に変換"""
    loc_value = loc[0] if value < 0 else loc[1] if value > 0 else ""
    abs_value = abs(value)
    deg = int(abs_value)
    t1 = (abs_value - deg) * 60
    minute = int(t1)
    second = round((t1 - minute) * 60, 5)
    return (deg, minute, second, loc_value)


def change_to_rational(number):
    """有理数に変換"""
    f = Fraction(str(number))
    return (f.numerator, f.denominator)


def attach_geotag(file_name, out_file, lat, lng, alt):
    """画像にジオタグを追加"""
    lat_deg = to_deg(lat, ["S", "N"])
    lng_deg = to_deg(lng, ["W", "E"])

    # 度分秒を有理数に変換
    exiv_lat = tuple(map(change_to_rational, lat_deg[:3]))
    exiv_lng = tuple(map(change_to_rational, lng_deg[:3]))
    exiv_alt = change_to_rational(alt)

    gps_ifd = {
        piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
        piexif.GPSIFD.GPSLatitudeRef: lat_deg[3],
        piexif.GPSIFD.GPSLatitude: exiv_lat,
        piexif.GPSIFD.GPSLongitudeRef: lng_deg[3],
        piexif.GPSIFD.GPSLongitude: exiv_lng,
        piexif.GPSIFD.GPSAltitudeRef: 0,  # 0は海抜高度を示します
        piexif.GPSIFD.GPSAltitude: exiv_alt,
    }

    exif_dict = {"GPS": gps_ifd}
    exif_bytes = piexif.dump(exif_dict)

    # ジオタグ付きの画像を作成
    create_picture_geotag(file_name, out_file, exif_bytes)


def create_picture_geotag(file_name, out_file, exif_bytes):
    """ジオタグを貼り付けた画像を作成"""
    im = Image.open(file_name)
    im.save(out_file, quality=95, exif=exif_bytes)


def add_geotags_to_images(input_movie, metadata_path, output_folder, project_dir, basename, delta_frame, ext):
    # メタデータの読み込み
    df_metadata = pd.read_csv(metadata_path)

    # 動画のフレーム数を取得
    cap = cv2.VideoCapture(input_movie)
    all_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    digit = len(str(all_frames))
    print(digit)

    # 各フレームにジオタグを付加
    pickup_frame_arr = []
    i = 0
    while i <= all_frames:
        pickup_frame_arr.append(i)
        i = i + delta_frame

    pickup_frame_arr = list(range(0, all_frames, delta_frame))

    for frame in pickup_frame_arr:
        if frame < all_frames:
            lat = df_metadata.iloc[frame, 1]
            lon = df_metadata.iloc[frame, 2]
            alt = df_metadata.iloc[frame, 3]  # 高度の列番号を確認してください
            base_path = project_dir + "/images/" + basename
            image_path = base_path + "_" + str(frame).zfill(digit) + "." + ext
            in_file = image_path
            out_file = output_folder + "geo_" + str(frame).zfill(digit)+".jpg"
            attach_geotag(in_file, out_file, lat, lon, alt)


# テスト用のコード
if __name__ == '__main__':
    input_movie = "F:/05.2024年度/02.授業科目/F2_Pracitice/gopro_to_gps/school_corridor.MP4"
    metadata_path = "project6/ex_school_corridor.csv"
    output_folder = "project6/geo_jpg/"
    project_dir = "project6"
    basename = 'video_img'
    delta_frame = 10
    ext = "png"

    add_geotags_to_images(input_movie, metadata_path,
                          output_folder, project_dir, basename, delta_frame, ext)
