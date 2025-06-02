# movie_to_plane-gui.pyについて

**目的**：Matashapeを用いて点群を生成するための画像を動画から取得する<br>
**内容**：360度動画(.mov)を任意のyaw角度ごとに分割した画像ファイルに変換する

## 基本的な使い方
1. **movie_to_plane.py**を実行するとGUIが立ち上がる
2. **Input 360度 Video**にmov形式の動画を選択してください
3. **Output Directory**に出力ファイルを選択してください
4. 必要であればオプションを変更する
5. **Start Processing**ボタンをクリックすると変換が始まる

## オプションの説明
### Frames Settings:
* **Extract every N frames**<br>何フレームごとに動画から写真を切り取るか設定できる
* **Output Format**<br>出力される拡張子を設定できる
* **Organize by Yaw Angle**<br>分割する角度ごとにフォルダーを作成するか、一つのフォルダーに全ての写真を出力するか設定できる
* **Save individual views**<br>指定したyawごとに分割した写真を保存したい場合は必ずチェックを入れてください<br>チェックを外すと、分割する前の動画から抽出しただけの写真が保存される

### Projection Settings:
* **Start Processing**ボタンをクリックすると変換が始まる
* **Field of View (FOV) [degrees]**<br>パノラマ画像から切り出す画像の視野角(水平方向の角度)を設定できる
* **Output Width [px]**<br>出力画像の幅のピクセル数を設定できる
* **Output Height [px]**<br>出力画像の縦のピクセル数を設定できる
* **Pitch Angle [degrees]**<br>カメラの垂直方向の角度を設定できる(90:まっすぐ, 90より小さい:下向き, 90より大きい:上向き)
* **Yaw Angles [degrees]**<br>パノラマ写真から切り出すカメラの水平方向の視点を設定できる(0,60,120,180,240,300の場合6分割できる)
* **Worker Threads**<br>使用するCPUのスレッドの数を設定できる※実際のCPUのスレッドの数を超えないように調節される

### Profile Management
* **Profile Name**<br>上の設定を名前を付けて保存できる
* **Select Profile**<br>選択した設定データを読み込み、削除できる

---

### note
<details><summary>MarkDown形式の記述方法</summary>

[MarkDown形式の記述方法](https://qiita.com/oreo/items/82183bfbaac69971917f)<br>
[折りたたみ表現](https://qiita.com/matagawa/items/31e26e9cd53c3e61ae07)
</details>
