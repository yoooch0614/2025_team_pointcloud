import re
import pandas as pd
from datetime import datetime

def process_gps_data(input_file, output_file):
    latarr = []
    longarr = []
    elearr = []
    timearr = []

    def remove_str(input_str, keyword):
        time_index = input_str.find(keyword)
        if time_index != -1:
            string_starting_with_time = input_str[time_index:]
            return str(string_starting_with_time)
        else:
            print(keyword + "が見つかりませんでした。")
            return None

    def get_gps(input_str):
        # 正規表現パターンを定義
        pattern = r'lat="([\d\.]+)" lon="([\d\.]+)"'

        # 文字列からlatとlonの値を抽出
        match = re.search(pattern, input_str)

        if match:
            lat = float(match.group(1))
            lon = float(match.group(2))
            latarr.append(lat)
            longarr.append(lon)
        else:
            print("latとlonが見つかりませんでした。")

    def get_ele(input_str):
        # 正規表現パターンを定義
        pattern = r"\d+(?:\.\d+)?"

        # 文字列から数字を抽出
        match = re.search(pattern, input_str)

        if match:
            extracted_number = float(match.group())
            elearr.append(extracted_number)
        else:
            print("数字が見つかりませんでした。")
            elearr.append(0)

    def get_time(input_str):
        # 文字列から日付と時刻を解析
        datetime_obj = datetime.strptime(
            input_str, "<time>%Y-%m-%dT%H:%M:%S.%fZ</time>\n")
        timearr.append(datetime_obj)

    with open(input_file) as f:
        for line in f:
            if ("<trkpt" in line):
                input_str = remove_str(line, "<trkpt")
                get_gps(input_str)
            elif ("<ele>" in line):
                input_str = remove_str(line, "<ele>")
                get_ele(input_str)
            elif ("<time>" in line):
                input_str = remove_str(line, "<time>")
                get_time(input_str)

    # データ構造化
    data = {
        'Time': timearr,
        'Latitude': latarr,
        'Longitude': longarr,
        'Elevation': elearr
    }

    # データフレームの作成
    df = pd.DataFrame(data)

    # 'Latitude' と 'Longitude' 列を小数点以下7桁にフォーマット
    df['Latitude'] = df['Latitude'].map('{:.7f}'.format)
    df['Longitude'] = df['Longitude'].map('{:.7f}'.format)

    # 'Elevation' 列を小数点以下3桁で保存
    df['Elevation'] = df['Elevation'].round(3)

    # CSVファイルに保存
    df.to_csv(output_file, index=False, float_format='%.3f')

if __name__ == '__main__':
    input_file = "project2/0425_road_bike.txt"
    output_file = "project2/0425_road_bike.csv"
    process_gps_data(input_file, output_file)