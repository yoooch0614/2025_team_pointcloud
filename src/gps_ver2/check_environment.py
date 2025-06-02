#!/usr/bin/env python3
"""
GoPro GPS処理システム環境確認スクリプト
"""

import sys
import subprocess
import importlib
from pathlib import Path
import os

def check_python_version():
    """Python版本检查"""
    print("=" * 50)
    print("Python環境の確認")
    print("=" * 50)
    
    version = sys.version_info
    print(f"Python版本: {version.major}.{version.minor}.{version.micro}")
    
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(" Python 3.8以降が必要です")
        return False
    else:
        print(" Python版本は要求を満たしています")
        return True

def check_python_packages():
    """Python包检查"""
    print("\n" + "=" * 50)
    print("Pythonパッケージの確認")
    print("=" * 50)
    
    required_packages = {
        'cv2': 'opencv-python',
        'pandas': 'pandas',
        'numpy': 'numpy',
        'PIL': 'pillow',
        'piexif': 'piexif',
        'scipy': 'scipy',
        'requests': 'requests'
    }
    
    all_ok = True
    
    for module_name, package_name in required_packages.items():
        try:
            module = importlib.import_module(module_name)
            version = getattr(module, '__version__', 'バージョン不明')
            print(f" {package_name}: {version}")
        except ImportError:
            print(f" {package_name}: インストールされていません")
            all_ok = False
    
    return all_ok

def check_external_tools():
    """外部ツールの確認"""
    print("\n" + "=" * 50)
    print("外部ツールの確認")
    print("=" * 50)
    
    tools = {
        'ffmpeg': 'FFmpeg',
        'node': 'Node.js',
        'npm': 'npm'
    }
    
    all_ok = True
    
    for cmd, name in tools.items():
        try:
            result = subprocess.run([cmd, '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                print(f" {name}: {version_line}")
            else:
                print(f" {name}: 実行できません")
                all_ok = False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print(f" {name}: 見つかりません")
            all_ok = False
        except Exception as e:
            print(f" {name}: エラー - {e}")
            all_ok = False
    
    # gopro2gpxの確認
    gopro2gpx_paths = [
        'gopro2gpx',
        'gopro2gpx.exe',
        r'C:\Users\user\go\bin\gopro2gpx.exe',
        os.path.expanduser('~/go/bin/gopro2gpx')
    ]
    
    gopro2gpx_found = False
    for path in gopro2gpx_paths:
        try:
            result = subprocess.run([path, '--help'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0 or 'usage' in result.stderr.lower():
                print(f" gopro2gpx: {path}")
                gopro2gpx_found = True
                break
        except:
            continue
    
    if not gopro2gpx_found:
        print(" gopro2gpx: 見つかりません")
        all_ok = False
    
    return all_ok

def check_workspace_structure():
    """ワークスペース構造の確認"""
    print("\n" + "=" * 50)
    print("ワークスペース構造の確認")
    print("=" * 50)
    
    current_path = Path.cwd()
    workspace_root = None
    
    # pointcloud_wsフォルダを探す
    for parent in [current_path] + list(current_path.parents):
        if parent.name == "pointcloud_ws":
            workspace_root = parent
            break
        pointcloud_ws_path = parent / "pointcloud_ws"
        if pointcloud_ws_path.exists():
            workspace_root = pointcloud_ws_path
            break
    
    if workspace_root:
        print(f" ワークスペースルート: {workspace_root}")
        
        # 重要なディレクトリの確認
        important_dirs = [
            "movies",
            "src/gps_ver2",
            "include"
        ]
        
        for dir_path in important_dirs:
            full_path = workspace_root / dir_path
            if full_path.exists():
                print(f" {dir_path}: 存在します")
            else:
                print(f"  {dir_path}: 存在しません（作成を推奨）")
        
        # Node.jsスクリプトの確認
        script_path = workspace_root / "src" / "gps_ver2" / "gopro_360_to_csv.js"
        if script_path.exists():
            print(f" Node.jsスクリプト: {script_path}")
        else:
            print(f" Node.jsスクリプト: {script_path} が見つかりません")
    else:
        print("  pointcloud_wsワークスペースが見つかりません")
        print(f"現在のディレクトリ: {current_path}")
    
    return workspace_root is not None

def check_video_files():
    """ビデオファイルの確認"""
    print("\n" + "=" * 50)
    print("ビデオファイルの確認")
    print("=" * 50)
    
    current_path = Path.cwd()
    movies_dirs = []
    
    # moviesディレクトリを探す
    workspace_root = None
    for parent in [current_path] + list(current_path.parents):
        if parent.name == "pointcloud_ws":
            workspace_root = parent
            break
        pointcloud_ws_path = parent / "pointcloud_ws"
        if pointcloud_ws_path.exists():
            workspace_root = pointcloud_ws_path
            break
    
    if workspace_root:
        movies_dirs.append(workspace_root / "movies")
    movies_dirs.append(current_path / "movies")
    
    for movies_dir in movies_dirs:
        if movies_dir.exists():
            print(f" ビデオディレクトリ: {movies_dir}")
            
            video_extensions = ['.360', '.mov', '.mp4']
            video_files = []
            
            for ext in video_extensions:
                video_files.extend(list(movies_dir.glob(f'*{ext}')))
            
            if video_files:
                print(f" ビデオファイル ({len(video_files)}個):")
                for video_file in video_files[:5]:  # 最初の5個だけ表示
                    size_mb = video_file.stat().st_size / (1024 * 1024)
                    print(f"   • {video_file.name} ({size_mb:.1f} MB)")
                if len(video_files) > 5:
                    print(f"   ... および他{len(video_files) - 5}個")
            else:
                print("  ビデオファイルが見つかりません")
            break
    else:
        print("  moviesディレクトリが見つかりません")

def generate_setup_recommendations():
    """セットアップ推奨事項の生成"""
    print("\n" + "=" * 50)
    print("セットアップ推奨事項")
    print("=" * 50)
    
    print("1. 不足しているパッケージのインストール:")
    print("   pip install -r requirements.txt")
    
    print("\n2. 必要なディレクトリの作成:")
    print("   mkdir -p pointcloud_ws/{movies,src/gps_ver2,include}")
    
    print("\n3. 外部ツールのインストール:")
    print("   - FFmpeg: https://ffmpeg.org/download.html")
    print("   - Node.js: https://nodejs.org/")
    print("   - gopro2gpx: go install github.com/juanirache/gopro2gpx@latest")
    
    print("\n4. ビデオファイルの配置:")
    print("   .360および.movファイルをmovies/フォルダに配置")

def main():
    """メイン関数"""
    print("GoPro GPS処理システム環境確認")
    print("=" * 50)
    
    checks = [
        ("Python版本", check_python_version),
        ("Pythonパッケージ", check_python_packages),
        ("外部ツール", check_external_tools),
        ("ワークスペース構造", check_workspace_structure)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f" {check_name}チェック中にエラー: {e}")
            results.append((check_name, False))
    
    # ビデオファイルの確認（必須ではない）
    check_video_files()
    
    # 結果サマリー
    print("\n" + "=" * 50)
    print("確認結果サマリー")
    print("=" * 50)
    
    all_passed = True
    for check_name, result in results:
        status = " 通過" if result else " 失敗"
        print(f"{check_name}: {status}")
        if not result:
            all_passed = False
    
    if all_passed:
        print("\n すべての確認が通過しました！")
        print("gopro_dual_input_gui.py を実行して処理を開始できます。")
    else:
        print("\n  いくつかの問題が見つかりました。")
        generate_setup_recommendations()
    
    return all_passed

if __name__ == "__main__":
    main()
