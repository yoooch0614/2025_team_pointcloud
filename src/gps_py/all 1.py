from movie_to_gpx import run_ffmpeg, run_ffmpeg_remove_audio, run_gopro2gpx
from movie_to_image_2 import save_all_resize_frames
from gpx_to_txt_2 import convert_gpx_to_txt
from pickup_5 import process_gps_data
from expand_gps_v3 import expand_gps
from geotag_v4 import add_geotags_to_images
import os


def create_directories(base_path):
    directories = ["geo_jpg", "images"]
    try:
        # ベースディレクトリを作成
        os.makedirs(base_path, exist_ok=True)

        # サブディレクトリを作成
        for directory in directories:
            path = os.path.join(base_path, directory)
            os.makedirs(path, exist_ok=True)
            print(f"Directory '{path}' created successfully")

    except Exception as e:
        print(f"An error occurred: {e}")


def get_basename_without_extension(file_path):
    # ファイル名と拡張子に分割し、ファイル名のみを返す
    return os.path.splitext(os.path.basename(file_path))[0]


if __name__ == '__main__':
    #######################################
    # 変更ポイント
    project_dir = "D://project1"
    movie_basename = "GS010663.360"
    movie_path = "D://2025F2//pointcloud//datas//" + movie_basename
    deltaframe = 10
    resize_rate = 1
    #######################################

    create_directories(project_dir)
    movie_basename = get_basename_without_extension(movie_path)
    out_bin_path = os.path.join(project_dir, movie_basename + ".bin")
    in_bin_path = out_bin_path
    print("in_bin_path: ", in_bin_path)
    out_gpx_path = os.path.join(project_dir, movie_basename + ".gpx")
    print("out_gpx_path: ", out_gpx_path)
    no_aud_mp4 = os.path.join(project_dir, movie_basename + "_noaud.mp4")
    print("no_aud_mp4: ", no_aud_mp4)
    # run_ffmpeg_remove_audio(movie_path, no_aud_mp4)
    run_ffmpeg(movie_path, out_bin_path)
    run_gopro2gpx(in_bin_path, out_gpx_path)

    basename = 'video_img'
    ext = "png"
    save_all_resize_frames(movie_path, os.path.join(
        project_dir, "images"), basename, ext, deltaframe, resize_rate)

    out_txt_path = os.path.join(project_dir, movie_basename + ".txt")
    convert_gpx_to_txt(out_gpx_path, out_txt_path)
    out_csv_path = os.path.join(project_dir, movie_basename + ".csv")
    process_gps_data(out_txt_path, out_csv_path)
    out_excsv_path = os.path.join(project_dir, "ex_" + movie_basename + ".csv")
    expand_gps(movie_path, out_csv_path, out_excsv_path)

    add_geotags_to_images(movie_path, out_excsv_path,
                          os.path.join(project_dir, "geo_jpg/"), project_dir, basename, deltaframe, ext)
