# 1. 環境設定
1. 環境設定が出来ているか確認<br>
    ```bash
    #ワークスペースに移動
    cd pointcloud_ws/include

    #Node.jsのバージョンを確認 > v18.19.0
    ./nodejs18/bin/node --version 

    #npmのバージョンを確認 > 10.2.3
    PATH="$(pwd)/nodejs18/bin:$PATH" ./nodejs18/bin/npm --version

    #pythonのバージョンを確認 > Python 3.13.3
    ./python313/bin/python3 --version


    ```

    バージョンを確認できたらok <br>

    <details><summary>ffmpegのヴァージョン</summary>
    <br>

    ```bash
    #確認ｓ
    ./ffmpeg/ffmpeg -version
    # 実行権限の確認
    chmod +x ffmpeg/ffmpeg
    chmod +x ffmpeg/ffprobe
    ```

    再度確認してください<br>
    
    </details>

2.　ファイル構成<br>
    pointcloud_ws/ # ワークスペースルート <br>
    ├── include/ # 外部ツール・ライブラリ <br>
    │ ├── python313/ # Python 3.13.3 <br>
    │ │ └── bin/<br>
    │ │ └── python3 # Python実行ファイル <br>
    │ ├── nodejs18/ # Node.js 18 <br>
    │ │ └── bin/ <br>
    │ │ └── node # Node.js実行ファイル <br>
    │ ├── ffmpeg/ # FFmpeg（静的ビルド） <br>
    │ │ ├── ffmpeg # FFmpeg実行ファイル <br>
    │ │ └── ffprobe # FFprobe実行ファイル <br>
    │ ├── package.json # Node.js依存関係設定 <br>
    │ └── node_modules/ # Node.jsパッケージ <br>
    │   ├── gpmf-extract/ # GoProテレメトリ抽出 <br>
    │   └── gopro-telemetry/ # GoProテレメトリ処理 <br>
    ├── movies/ # 動画ファイル置き場 <br>
    │ └── GS010678.360 # 入力動画ファイル <br>
    └── src/ <br>
    └── gps_ver2/ # メインスクリプトディレクトリ <br>
        ├── output/ # 出力ファイル <br>
        │ └── GS010678_telemetry.csv # 最終出力CSV <br>
        └── gopro_360_to_csv.js # 統合ツール（これを使用）<br>
