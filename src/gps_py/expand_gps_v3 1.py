import cv2
import datetime
import numpy as np
import pandas as pd
from gps_linear_interpolation import interpolate_gps_data

def expand_gps(input_movie, csvpath, output_file, frame_rate=30):
    # 動画のフレーム数を取得
    cap = cv2.VideoCapture(input_movie)
    allframe = cap.get(cv2.CAP_PROP_FRAME_COUNT)
    
    if not cap.isOpened():
        print(f"Error: Unable to open video file {input_movie}")
        return

    # GPSデータの開始時刻を取得
    input_df = pd.read_csv(csvpath)
    start_time = input_df.loc[0, 'Time']
    # 文字列をdatetimeオブジェクトに変換
    formatted_start_time = datetime.datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S.%f")

    # フレームごとの時刻配列を作成
    num_elements = int(allframe)
    datetime_time_array = np.array([formatted_start_time + datetime.timedelta(seconds=i/frame_rate) for i in range(num_elements)])

    # GPSデータを補間して配列に格納
    ex_latarr = []
    ex_lonarr = []
    ex_elearr = []

    for j in range(num_elements):
        target_time = pd.to_datetime(datetime_time_array[j]).timestamp()
        interp_lat, interp_lon, interp_elev = interpolate_gps_data(input_df, target_time)
        ex_latarr.append(float(interp_lat))
        ex_lonarr.append(float(interp_lon))
        ex_elearr.append(float(interp_elev))

    # データ構造化
    data = {
        'Time': datetime_time_array,
        'Latitude': ex_latarr,
        'Longitude': ex_lonarr,
        'Elevation': ex_elearr
    }

    # DataFrameの作成
    output_df = pd.DataFrame(data)

    # 秒数を小数点3桁まで表示
    output_df['Time'] = output_df['Time'].apply(lambda x: x.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3])

    # 列のフォーマット
    output_df['Latitude'] = output_df['Latitude'].map('{:.7f}'.format)
    output_df['Longitude'] = output_df['Longitude'].map('{:.7f}'.format)
    output_df['Elevation'] = output_df['Elevation'].round(3)

    # CSVファイルに保存
    output_df.to_csv(output_file, index=False, float_format='%.3f')

# テスト用のコード
if __name__ == '__main__':
    input_movie = "C:/Users/h-shi/OneDrive/デスクトップ/100GOPRO/GS010553.360"
    csvpath = "project2/0425_road_bike.csv"
    output_file = "project2/ex_0425_road_bike.csv"

    expand_gps(input_movie, csvpath, output_file)
