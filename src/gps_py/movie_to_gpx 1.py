import subprocess

# 1. ここで共通の ffmpeg パスを定義
ffmpeg = r'D:\\ffmpeg-7.1.1-essentials_build\\ffmpeg-7.1.1-essentials_build\\bin\\ffmpeg.exe'

def run_ffmpeg(mp4path, out_bin_path):
    command = [
        ffmpeg,
        '-y',
        '-i', mp4path,
        '-codec', 'copy',
        '-map', '0:3',
        '-f', 'rawvideo',
        out_bin_path
    ]

    try:
        # subprocess.runを使用してコマンドを実行
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("run_ffmepg")
        print("Command executed successfully.")
        print("Output:\n", result.stdout.decode())
        print("Error (if any):\n", result.stderr.decode())
    except subprocess.CalledProcessError as e:
        print("ERROR: run_ffmepg")
        print("An error occurred while executing the command.")
        print("Error message:\n", e.stderr.decode())


def run_ffmpeg_remove_audio(input_path, output_path):
    command = [
        ffmpeg,
        '-i', input_path,
        '-vcodec', 'copy',
        '-an',
        output_path
    ]

    try:
        # subprocess.runを使用してコマンドを実行
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("run_ffmpeg_remove_audio")
        print("Command executed successfully.")
        print("Output:\n", result.stdout.decode())
        print("Error (if any):\n", result.stderr.decode())
    except subprocess.CalledProcessError as e:
        print("An error occurred while executing the command.")
        print("Error message:\n", e.stderr.decode())


def run_gopro2gpx(in_bin_path, out_gpx_path):
    #######################################
    # 変更ポイント
    command = [
        r"C:\Users\user\go\bin\gopro2gpx.exe",
        '-i', in_bin_path,
        '-o', out_gpx_path
    ]
    #######################################

    try:
        # subprocess.runを使用してコマンドを実行
        result = subprocess.run(command, check=True,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("run_gopro2gpx")
        print("Command executed successfully.")
        print("Output:\n", result.stdout.decode())
        print("Error (if any):\n", result.stderr.decode())
    except subprocess.CalledProcessError as e:
        print("ERROR: run_gopro2gpx")
        print("An error occurred while executing the command.")
        print("Error message:\n", e.stderr.decode())


if __name__ == '__main__':
    mp4path = "../school_corridor.MP4"
    no_aud_mp4 = "example_noaud.mp4"
    out_bin_path = "ex.bin"
    in_bin_path = out_bin_path
    out_gpx_path = "output.gpx"
    run_ffmpeg_remove_audio(mp4path, no_aud_mp4)
    # run_ffmpeg(mp4path, out_bin_path)
    # run_gopro2gpx(in_bin_path, out_gpx_path)
