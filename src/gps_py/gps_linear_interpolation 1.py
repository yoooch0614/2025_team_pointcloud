import pandas as pd
from scipy.interpolate import interp1d
import datetime


def convert_to_unix_time(dt):
    return dt.timestamp()


def interpolate_gps_data(input_df, target_time):
    df = input_df
    if (df["Time"].dtype == "object"):
        # time列をdatetime型として読み込む
        df['Time'] = pd.to_datetime(df['Time'])

    if (df["Time"].dtype == "datetime64[ns]"):
        # time列をUnix時間に変換
        df['Time'] = df['Time'].apply(convert_to_unix_time)

    # 線形補完用の関数を作成
    interp_func_lat = interp1d(
        df["Time"], df["Latitude"], kind="linear", fill_value="extrapolate")
    interp_func_lon = interp1d(
        df["Time"], df["Longitude"], kind="linear", fill_value="extrapolate")
    interp_func_elev = interp1d(
        df["Time"], df["Elevation"], kind="linear", fill_value="extrapolate")

    # 線形補完された値を取得
    interp_lat = interp_func_lat(target_time)
    interp_lon = interp_func_lon(target_time)
    interp_elev = interp_func_elev(target_time)

    return interp_lat, interp_lon, interp_elev


if __name__ == '__main__':
    csvpath = "gps_GX010553_3.csv"
    input_df = pd.read_csv(csvpath)

    # テスト用の時刻
    target_time = pd.to_datetime("2024-04-22 06:37:45.5").timestamp()

    # 関数を呼び出して線形補完された値を取得
    interp_lat, interp_lon, interp_elev = interpolate_gps_data(
        input_df, target_time)

    print(f"時刻 {datetime.datetime.fromtimestamp(target_time)}:")
    print(f"Latitude: {interp_lat:.6f}")
    print(f"Longitude: {interp_lon:.6f}")
    print(f"Elevation: {interp_elev:.3f}")
