import os
import sys
import threading
import datetime
import time
import subprocess
import json
import re
from pathlib import Path
import cv2
import numpy as np
import pandas as pd
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from fractions import Fraction
import piexif
from PIL import Image
from scipy.interpolate import interp1d

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)

class NodeJSTelemetryExtractor:
    """Node.js telemetry extraction wrapper for pointcloud_ws structure"""
    
    def __init__(self, workspace_root=None, nodejs_script_path=None):
        self.workspace_root = Path(workspace_root) if workspace_root else self.find_workspace_root()
        self.nodejs_script_path = nodejs_script_path or self.find_nodejs_script()
        self.node_path = self.find_node_executable()
        self.ffmpeg_path = self.find_ffmpeg_executable()
    
    def find_workspace_root(self):
        """Find the pointcloud_ws workspace root"""
        current_path = Path.cwd()
        
        # Search upwards for pointcloud_ws directory
        for parent in [current_path] + list(current_path.parents):
            if parent.name == "pointcloud_ws":
                logging.info(f"Found workspace root: {parent}")
                return parent
            
            # Look for workspace indicators
            pointcloud_ws_path = parent / "pointcloud_ws"
            if pointcloud_ws_path.exists():
                logging.info(f"Found workspace root: {pointcloud_ws_path}")
                return pointcloud_ws_path
        
        # Fallback to current directory
        logging.warning("Workspace root not found, using current directory")
        return current_path
    
    def find_nodejs_script(self):
        """Find the Node.js telemetry extraction script"""
        if not self.workspace_root:
            return None
            
        possible_paths = [
            self.workspace_root / "src" / "gps_ver2" / "gopro_360_to_csv.js",
            self.workspace_root / "src" / "gps_ver2" / "gopro_360_to_csv_with_gps.js",
            Path("gopro_360_to_csv.js"),
            Path("gopro_360_to_csv_with_gps.js")
        ]
        
        for path in possible_paths:
            if path.exists():
                logging.info(f"Found Node.js script: {path}")
                return str(path.resolve())
        
        logging.warning("Node.js script not found")
        return None
    
    def find_node_executable(self):
        """Find Node.js executable in workspace"""
        if not self.workspace_root:
            return "node"
            
        node_paths = [
            self.workspace_root / "include" / "nodejs18" / "bin" / "node",
            self.workspace_root / "include" / "nodejs18" / "node.exe",
            "node"
        ]
        
        for node_path in node_paths:
            try:
                if isinstance(node_path, Path) and node_path.exists():
                    logging.info(f"Found Node.js: {node_path}")
                    return str(node_path)
                elif node_path == "node":
                    # Test system node
                    result = subprocess.run([node_path, "--version"], capture_output=True)
                    if result.returncode == 0:
                        logging.info("Using system Node.js")
                        return node_path
            except:
                continue
        
        logging.warning("Node.js executable not found")
        return "node"
    
    def find_ffmpeg_executable(self):
        """Find FFmpeg executable in workspace"""
        if not self.workspace_root:
            return "ffmpeg"
            
        ffmpeg_paths = [
            self.workspace_root / "include" / "ffmpeg" / "ffmpeg",
            self.workspace_root / "include" / "ffmpeg" / "ffmpeg.exe",
            "ffmpeg"
        ]
        
        for ffmpeg_path in ffmpeg_paths:
            try:
                if isinstance(ffmpeg_path, Path) and ffmpeg_path.exists():
                    logging.info(f"Found FFmpeg: {ffmpeg_path}")
                    return str(ffmpeg_path)
                elif ffmpeg_path == "ffmpeg":
                    # Test system ffmpeg
                    result = subprocess.run([ffmpeg_path, "-version"], capture_output=True)
                    if result.returncode == 0:
                        logging.info("Using system FFmpeg")
                        return ffmpeg_path
            except:
                continue
        
        logging.warning("FFmpeg executable not found")
        return "ffmpeg"
    
    def extract_telemetry_from_360(self, video_360_path, output_dir=None):
        """Extract telemetry from .360 file using Node.js script"""
        if not self.nodejs_script_path:
            logging.error("Node.js telemetry script not found")
            return None
        
        if not self.node_path:
            logging.error("Node.js executable not found")
            return None
        
        try:
            # Use workspace movies directory if video is there, otherwise use provided path
            video_path = Path(video_360_path)
            workspace_movies_dir = self.workspace_root / "movies" if self.workspace_root else None
            
            # If output_dir not specified, use workspace output directory
            if not output_dir:
                if self.workspace_root:
                    output_dir = self.workspace_root / "src" / "gps_ver2" / "output"
                else:
                    output_dir = Path.cwd() / "output"
            
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Copy video to movies directory if it's not already there
            video_filename = video_path.name
            
            if workspace_movies_dir and workspace_movies_dir.exists():
                target_video_path = workspace_movies_dir / video_filename
                if not target_video_path.exists() and video_path.exists():
                    import shutil
                    logging.info(f"Copying video to workspace movies directory: {target_video_path}")
                    shutil.copy2(video_path, target_video_path)
                video_for_processing = target_video_path
            else:
                video_for_processing = video_path
            
            # Prepare command
            cmd = [str(self.node_path), str(self.nodejs_script_path), video_filename]
            
            logging.info(f"Running Node.js extractor: {' '.join(cmd)}")
            logging.info(f"Working directory: {output_path}")
            
            # Set working directory to output directory
            original_cwd = os.getcwd()
            
            try:
                os.chdir(output_path)
                
                # Set environment variables for the workspace
                env = os.environ.copy()
                if self.workspace_root:
                    env['WORKSPACE_ROOT'] = str(self.workspace_root)
                    env['MOVIES_DIR'] = str(workspace_movies_dir) if workspace_movies_dir else ""
                    env['FFMPEG_PATH'] = str(self.ffmpeg_path)
                
                # Run Node.js script with timeout
                result = subprocess.run(
                    cmd, 
                    capture_output=True, 
                    text=True, 
                    timeout=600,  # 10 minutes timeout
                    cwd=str(output_path),
                    env=env
                )
                
                if result.returncode == 0:
                    # Look for generated CSV file
                    base_name = video_path.stem
                    csv_candidates = [
                        f"{base_name}_telemetry.csv",
                        f"{base_name}.csv",
                        "telemetry.csv",
                        "output.csv"
                    ]
                    
                    for csv_name in csv_candidates:
                        csv_path = output_path / csv_name
                        if csv_path.exists() and csv_path.stat().st_size > 100:
                            logging.info(f"Telemetry CSV found: {csv_path}")
                            return str(csv_path)
                    
                    # List all CSV files in output directory for debugging
                    csv_files = list(output_path.glob("*.csv"))
                    if csv_files:
                        logging.info(f"Found CSV files: {[f.name for f in csv_files]}")
                        # Return the largest CSV file (likely the telemetry data)
                        largest_csv = max(csv_files, key=lambda f: f.stat().st_size)
                        if largest_csv.stat().st_size > 100:
                            logging.info(f"Using largest CSV file: {largest_csv}")
                            return str(largest_csv)
                    
                    logging.error("No valid telemetry CSV found after extraction")
                    logging.info(f"Node.js stdout: {result.stdout}")
                    return None
                else:
                    logging.error(f"Node.js extraction failed (code {result.returncode})")
                    logging.error(f"stderr: {result.stderr}")
                    logging.info(f"stdout: {result.stdout}")
                    return None
                    
            finally:
                os.chdir(original_cwd)
                
        except subprocess.TimeoutExpired:
            logging.error("Node.js extraction timed out (10 minutes)")
            return None
        except Exception as e:
            logging.error(f"Error running Node.js extraction: {e}")
            return None

class GPSInterpolator:
    """GPS data interpolation and processing"""
    
    @staticmethod
    def load_and_validate_gps_csv(csv_path):
        """Load and validate GPS CSV data"""
        try:
            df = pd.read_csv(csv_path)
            
            # Check for required columns
            required_cols = ['latitude', 'longitude']
            if not all(col in df.columns for col in required_cols):
                # Try alternative column names
                alt_mapping = {
                    'Latitude': 'latitude',
                    'Longitude': 'longitude',
                    'lat': 'latitude',
                    'lon': 'longitude',
                    'lng': 'longitude'
                }
                
                for old_col, new_col in alt_mapping.items():
                    if old_col in df.columns:
                        df = df.rename(columns={old_col: new_col})
            
            # Validate we have the required columns now
            if 'latitude' not in df.columns or 'longitude' not in df.columns:
                raise ValueError("GPS CSV must contain latitude and longitude columns")
            
            # Filter out invalid GPS coordinates
            valid_mask = (df['latitude'] != 0) & (df['longitude'] != 0) & \
                        (df['latitude'].notna()) & (df['longitude'].notna()) & \
                        (abs(df['latitude']) <= 90) & (abs(df['longitude']) <= 180)
            
            df_valid = df[valid_mask].copy()
            
            if len(df_valid) == 0:
                raise ValueError("No valid GPS coordinates found")
            
            # Add timestamp if not present
            if 'timestamp' not in df_valid.columns:
                if 'index' in df_valid.columns:
                    df_valid['timestamp'] = df_valid['index'] * 0.033333  # 30fps assumption
                else:
                    df_valid['timestamp'] = df_valid.index * 0.033333
            
            # Ensure altitude column exists
            if 'altitude' not in df_valid.columns:
                df_valid['altitude'] = 0.0
            
            logging.info(f"Loaded GPS data: {len(df_valid)} valid points")
            return df_valid
            
        except Exception as e:
            logging.error(f"Failed to load GPS CSV: {e}")
            return None
    
    @staticmethod
    def interpolate_gps_for_frames(gps_df, total_frames, fps=30.0):
        """Interpolate GPS data to match video frame count"""
        try:
            if gps_df is None or len(gps_df) == 0:
                return None
            
            # Create frame timestamps
            frame_timestamps = np.array([i / fps for i in range(total_frames)])
            
            # Get GPS timestamps
            gps_timestamps = gps_df['timestamp'].values
            
            # Create interpolation functions
            lat_interp = interp1d(
                gps_timestamps, 
                gps_df['latitude'].values,
                kind='linear', 
                fill_value='extrapolate',
                bounds_error=False
            )
            
            lon_interp = interp1d(
                gps_timestamps,
                gps_df['longitude'].values,
                kind='linear',
                fill_value='extrapolate',
                bounds_error=False
            )
            
            alt_interp = interp1d(
                gps_timestamps,
                gps_df['altitude'].values,
                kind='linear',
                fill_value='extrapolate',
                bounds_error=False
            )
            
            # Interpolate for each frame
            interpolated_data = {
                'frame': list(range(total_frames)),
                'timestamp': frame_timestamps.tolist(),
                'latitude': lat_interp(frame_timestamps).tolist(),
                'longitude': lon_interp(frame_timestamps).tolist(),
                'altitude': alt_interp(frame_timestamps).tolist()
            }
            
            interpolated_df = pd.DataFrame(interpolated_data)
            
            logging.info(f"GPS data interpolated for {total_frames} frames")
            return interpolated_df
            
        except Exception as e:
            logging.error(f"Failed to interpolate GPS data: {e}")
            return None

class FrameExtractor:
    """Video frame extraction with GPS overlay"""
    
    @staticmethod
    def extract_frames_with_gps(video_path, gps_df, output_dir, frame_interval=30, 
                               show_gps_overlay=True, include_orientation=False):
        """Extract frames from video with GPS information"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise Exception(f"Cannot open video: {video_path}")
            
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            
            logging.info(f"Video info: {total_frames} frames, {fps:.2f} fps")
            
            output_path = Path(output_dir)
            output_path.mkdir(parents=True, exist_ok=True)
            
            frame_id = 0
            saved_count = 0
            digit = len(str(total_frames // frame_interval))
            
            extracted_frames_info = []
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Extract frame at specified interval
                if frame_id % frame_interval == 0:
                    frame_gps_data = None
                    
                    # Get GPS data for this frame
                    if gps_df is not None and frame_id < len(gps_df):
                        gps_row = gps_df.iloc[frame_id]
                        frame_gps_data = {
                            'latitude': float(gps_row['latitude']),
                            'longitude': float(gps_row['longitude']),
                            'altitude': float(gps_row['altitude']),
                            'timestamp': gps_row.get('timestamp', frame_id / fps)
                        }
                        
                        # Add GPS overlay to frame if requested
                        if show_gps_overlay and frame_gps_data:
                            frame = FrameExtractor.add_gps_overlay(frame, frame_gps_data)
                    
                    # Save frame
                    frame_filename = f'frame_{saved_count:0{digit}d}.jpg'
                    frame_path = output_path / frame_filename
                    cv2.imwrite(str(frame_path), frame)
                    
                    # Store frame information
                    extracted_frames_info.append({
                        'frame_id': frame_id,
                        'saved_id': saved_count,
                        'filename': frame_filename,
                        'gps_data': frame_gps_data
                    })
                    
                    saved_count += 1
                    
                    if saved_count % 10 == 0:
                        logging.info(f"Extracted {saved_count} frames...")
                
                frame_id += 1
            
            cap.release()
            
            logging.info(f"Frame extraction completed: {saved_count} frames extracted")
            return extracted_frames_info
            
        except Exception as e:
            logging.error(f"Failed to extract frames: {e}")
            return None
    
    @staticmethod
    def add_gps_overlay(frame, gps_data):
        """Add GPS information overlay to frame"""
        try:
            if gps_data:
                text = f"Lat: {gps_data['latitude']:.6f}, Lon: {gps_data['longitude']:.6f}, Alt: {gps_data['altitude']:.1f}m"
                
                # Add semi-transparent background
                overlay = frame.copy()
                cv2.rectangle(overlay, (10, 10), (800, 60), (0, 0, 0), -1)
                frame = cv2.addWeighted(frame, 0.7, overlay, 0.3, 0)
                
                # Add text
                cv2.putText(frame, text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX,
                           0.8, (0, 255, 0), 2, cv2.LINE_AA)
            
            return frame
            
        except Exception as e:
            logging.warning(f"Failed to add GPS overlay: {e}")
            return frame

class GeotagProcessor:
    """EXIF geotagging for images"""
    
    @staticmethod
    def degrees_to_dms(decimal_degrees):
        """Convert decimal degrees to degrees, minutes, seconds"""
        is_negative = decimal_degrees < 0
        decimal_degrees = abs(decimal_degrees)
        
        degrees = int(decimal_degrees)
        minutes_float = (decimal_degrees - degrees) * 60
        minutes = int(minutes_float)
        seconds = (minutes_float - minutes) * 60
        
        return degrees, minutes, seconds, is_negative
    
    @staticmethod
    def create_rational(number):
        """Create rational number for EXIF"""
        frac = Fraction(number).limit_denominator(1000000)
        return (frac.numerator, frac.denominator)
    
    @staticmethod
    def add_gps_exif(image_path, output_path, latitude, longitude, altitude=0):
        """Add GPS EXIF data to image"""
        try:
            # Convert coordinates
            lat_deg, lat_min, lat_sec, lat_neg = GeotagProcessor.degrees_to_dms(latitude)
            lon_deg, lon_min, lon_sec, lon_neg = GeotagProcessor.degrees_to_dms(longitude)
            
            # Create rational numbers for EXIF
            lat_rational = (
                GeotagProcessor.create_rational(lat_deg),
                GeotagProcessor.create_rational(lat_min),
                GeotagProcessor.create_rational(lat_sec)
            )
            
            lon_rational = (
                GeotagProcessor.create_rational(lon_deg),
                GeotagProcessor.create_rational(lon_min),
                GeotagProcessor.create_rational(lon_sec)
            )
            
            alt_rational = GeotagProcessor.create_rational(abs(altitude))
            
            # Create GPS IFD
            gps_ifd = {
                piexif.GPSIFD.GPSVersionID: (2, 0, 0, 0),
                piexif.GPSIFD.GPSLatitudeRef: 'S' if lat_neg else 'N',
                piexif.GPSIFD.GPSLatitude: lat_rational,
                piexif.GPSIFD.GPSLongitudeRef: 'W' if lon_neg else 'E',
                piexif.GPSIFD.GPSLongitude: lon_rational,
                piexif.GPSIFD.GPSAltitudeRef: 1 if altitude < 0 else 0,
                piexif.GPSIFD.GPSAltitude: alt_rational
            }
            
            # Create EXIF dict and dump
            exif_dict = {"GPS": gps_ifd}
            exif_bytes = piexif.dump(exif_dict)
            
            # Save image with GPS EXIF
            img = Image.open(image_path)
            img.save(output_path, quality=95, exif=exif_bytes)
            
            return True
            
        except Exception as e:
            logging.error(f"Failed to add GPS EXIF to {image_path}: {e}")
            return False

class GoProDualInputGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GoPro Dual Input GPS Frame Extractor")
        self.root.geometry("1000x800")
        
        # Find workspace and initialize
        self.workspace_root = self.find_workspace_root()
        self.initialize_workspace_paths()
        
        # Processing state
        self.is_processing = False
        self.processing_thread = None
        
        # Create UI
        self.create_widgets()
        self.setup_logging()
        
        # Auto-detect workspace settings
        self.auto_configure_workspace()
    
    def find_workspace_root(self):
        """Find the pointcloud_ws workspace root"""
        current_path = Path.cwd()
        
        # Search upwards for pointcloud_ws directory
        for parent in [current_path] + list(current_path.parents):
            if parent.name == "pointcloud_ws":
                logging.info(f"Found workspace root: {parent}")
                return parent
            
            # Look for workspace indicators
            pointcloud_ws_path = parent / "pointcloud_ws"
            if pointcloud_ws_path.exists():
                logging.info(f"Found workspace root: {pointcloud_ws_path}")
                return pointcloud_ws_path
        
        # Fallback to current directory
        logging.warning("pointcloud_ws not found, using current directory")
        return current_path
    
    def initialize_workspace_paths(self):
        """Initialize workspace-specific paths"""
        if self.workspace_root:
            self.movies_dir = self.workspace_root / "movies"
            self.output_dir_default = self.workspace_root / "src" / "gps_ver2" / "output"
            self.include_dir = self.workspace_root / "include"
        else:
            self.movies_dir = Path.cwd() / "movies"
            self.output_dir_default = Path.cwd() / "output"
            self.include_dir = Path.cwd() / "include"
    
    def auto_configure_workspace(self):
        """Auto-configure workspace settings"""
        if not self.workspace_root:
            return
        
        try:
            # Auto-set Node.js script path
            script_path = self.workspace_root / "src" / "gps_ver2" / "gopro_360_to_csv.js"
            if script_path.exists():
                self.nodejs_script_var.set(str(script_path))
            
            # Auto-set default output directory
            if self.output_dir_default:
                self.output_dir_var.set(str(self.output_dir_default))
            
            # List available videos in movies directory
            if self.movies_dir.exists():
                video_files = list(self.movies_dir.glob("*.360")) + list(self.movies_dir.glob("*.mov"))
                if video_files:
                    self.update_video_suggestions(video_files)
                    
        except Exception as e:
            logging.warning(f"Failed to auto-configure workspace: {e}")
    
    def update_video_suggestions(self, video_files):
        """Update video file suggestions based on workspace movies directory"""
        try:
            # Find matching .360 and .mov files
            video_360_files = [f for f in video_files if f.suffix == ".360"]
            video_mov_files = [f for f in video_files if f.suffix in [".mov", ".mp4"]]
            
            if video_360_files:
                # Auto-suggest first .360 file
                self.video_360_var.set(str(video_360_files[0]))
                
            if video_mov_files:
                # Try to find matching .mov file
                for mov_file in video_mov_files:
                    for video_360_file in video_360_files:
                        if mov_file.stem.replace("_", "").replace("-", "") == video_360_file.stem.replace("_", "").replace("-", ""):
                            self.video_mov_var.set(str(mov_file))
                            break
                    else:
                        continue
                    break
                else:
                    # No matching file found, use first .mov file
                    self.video_mov_var.set(str(video_mov_files[0]))
                    
            logging.info(f"Found {len(video_360_files)} .360 files and {len(video_mov_files)} .mov files in workspace")
            
        except Exception as e:
            logging.warning(f"Failed to update video suggestions: {e}")
        
    def create_widgets(self):
        # Main container with tabs
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Input tab
        self.create_input_tab(notebook)
        
        # Settings tab  
        self.create_settings_tab(notebook)
        
        # Processing tab
        self.create_processing_tab(notebook)
    
    def create_input_tab(self, parent):
        frame = ttk.Frame(parent)
        parent.add(frame, text="Input Files & Settings")
        
        # Input files section
        input_frame = ttk.LabelFrame(frame, text="Input Files", padding=10)
        input_frame.pack(fill="x", padx=10, pady=5)
        
        # .360 video file
        ttk.Label(input_frame, text=".360 Video File (GPS source):").grid(row=0, column=0, sticky="w", pady=5)
        self.video_360_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.video_360_var, width=70).grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(input_frame, text="Browse", command=self.browse_360_video).grid(row=0, column=2, padx=5)
        
        # .mov video file
        ttk.Label(input_frame, text=".mov Video File (frame source):").grid(row=1, column=0, sticky="w", pady=5)
        self.video_mov_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.video_mov_var, width=70).grid(row=1, column=1, padx=5, sticky="ew")
        ttk.Button(input_frame, text="Browse", command=self.browse_mov_video).grid(row=1, column=2, padx=5)
        
        input_frame.columnconfigure(1, weight=1)
        
        # Output settings
        output_frame = ttk.LabelFrame(frame, text="Output Settings", padding=10)
        output_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(output_frame, text="Output Directory:").grid(row=0, column=0, sticky="w", pady=5)
        self.output_dir_var = tk.StringVar()
        ttk.Entry(output_frame, textvariable=self.output_dir_var, width=70).grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(output_frame, text="Browse", command=self.browse_output_dir).grid(row=0, column=2, padx=5)
        
        output_frame.columnconfigure(1, weight=1)
        
        # Processing settings
        settings_frame = ttk.LabelFrame(frame, text="Processing Settings", padding=10)
        settings_frame.pack(fill="x", padx=10, pady=5)
        
        # Frame interval
        ttk.Label(settings_frame, text="Frame Interval (extract every N frames):").grid(row=0, column=0, sticky="w", pady=5)
        self.frame_interval_var = tk.IntVar(value=30)
        frame_spin = ttk.Spinbox(settings_frame, from_=1, to=300, textvariable=self.frame_interval_var, width=10)
        frame_spin.grid(row=0, column=1, sticky="w", padx=5)
        
        # GPS overlay option
        ttk.Label(settings_frame, text="Show GPS overlay on frames:").grid(row=1, column=0, sticky="w", pady=5)
        self.show_gps_overlay_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, variable=self.show_gps_overlay_var).grid(row=1, column=1, sticky="w", padx=5)
        
        # Camera orientation option
        ttk.Label(settings_frame, text="Include camera orientation data:").grid(row=2, column=0, sticky="w", pady=5)
        self.include_orientation_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(settings_frame, variable=self.include_orientation_var).grid(row=2, column=1, sticky="w", padx=5)
        
        # Add GPS EXIF tags
        ttk.Label(settings_frame, text="Add GPS EXIF tags to images:").grid(row=3, column=0, sticky="w", pady=5)
        self.add_gps_exif_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(settings_frame, variable=self.add_gps_exif_var).grid(row=3, column=1, sticky="w", padx=5)
        
        # Control buttons
        control_frame = ttk.Frame(frame)
        control_frame.pack(fill="x", padx=10, pady=20)
        
        self.start_button = ttk.Button(control_frame, text="Start Processing", 
                                      command=self.start_processing, style="Accent.TButton")
        self.start_button.pack(side="left", padx=10)
        
        self.stop_button = ttk.Button(control_frame, text="Stop Processing", 
                                     command=self.stop_processing, state="disabled")
        self.stop_button.pack(side="left", padx=10)
    
    def create_settings_tab(self, parent):
        frame = ttk.Frame(parent)
        parent.add(frame, text="Advanced Settings")
        
        # Workspace info
        workspace_frame = ttk.LabelFrame(frame, text="Workspace Information", padding=10)
        workspace_frame.pack(fill="x", padx=10, pady=5)
        
        workspace_info = f"Workspace Root: {self.workspace_root}\n"
        workspace_info += f"Movies Directory: {self.movies_dir}\n"
        workspace_info += f"Output Directory: {self.output_dir_default}"
        
        workspace_label = ttk.Label(workspace_frame, text=workspace_info, font=("TkDefaultFont", 9))
        workspace_label.pack(anchor="w")
        
        ttk.Button(workspace_frame, text="Refresh Workspace", 
                  command=self.refresh_workspace).pack(pady=5)
        
        # Node.js settings
        nodejs_frame = ttk.LabelFrame(frame, text="Node.js Telemetry Extractor", padding=10)
        nodejs_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(nodejs_frame, text="Node.js Script Path:").grid(row=0, column=0, sticky="w", pady=5)
        self.nodejs_script_var = tk.StringVar()
        ttk.Entry(nodejs_frame, textvariable=self.nodejs_script_var, width=70).grid(row=0, column=1, padx=5, sticky="ew")
        ttk.Button(nodejs_frame, text="Browse", command=self.browse_nodejs_script).grid(row=0, column=2, padx=5)
        
        nodejs_frame.columnconfigure(1, weight=1)
        
        # GPS interpolation settings
        gps_frame = ttk.LabelFrame(frame, text="GPS Interpolation", padding=10)
        gps_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(gps_frame, text="Video FPS (for timestamp calculation):").grid(row=0, column=0, sticky="w", pady=5)
        self.video_fps_var = tk.DoubleVar(value=30.0)
        ttk.Spinbox(gps_frame, from_=1.0, to=120.0, increment=1.0, 
                   textvariable=self.video_fps_var, width=10).grid(row=0, column=1, sticky="w", padx=5)
        
        # Test buttons
        test_frame = ttk.LabelFrame(frame, text="Testing & Validation", padding=10)
        test_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(test_frame, text="Test Environment", 
                  command=self.test_nodejs_script).pack(side="left", padx=5)
        ttk.Button(test_frame, text="Validate .360 File", 
                  command=self.validate_360_file).pack(side="left", padx=5)
        ttk.Button(test_frame, text="List Available Videos", 
                  command=self.list_available_videos).pack(side="left", padx=5)
    
    def refresh_workspace(self):
        """Refresh workspace configuration"""
        try:
            self.workspace_root = self.find_workspace_root()
            self.initialize_workspace_paths()
            self.auto_configure_workspace()
            messagebox.showinfo("Refresh", "Workspace configuration refreshed!")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh workspace: {e}")
    
    def list_available_videos(self):
        """List available video files in workspace"""
        try:
            if not self.movies_dir.exists():
                messagebox.showinfo("No Videos", f"Movies directory not found: {self.movies_dir}")
                return
            
            video_files = []
            for ext in ["*.360", "*.mov", "*.mp4"]:
                video_files.extend(self.movies_dir.glob(ext))
            
            if not video_files:
                messagebox.showinfo("No Videos", f"No video files found in: {self.movies_dir}")
                return
            
            # Group by type
            video_360 = [f for f in video_files if f.suffix == ".360"]
            video_mov = [f for f in video_files if f.suffix in [".mov", ".mp4"]]
            
            message = f"Available videos in {self.movies_dir}:\n\n"
            
            if video_360:
                message += f".360 files ({len(video_360)}):\n"
                for f in video_360:
                    size_mb = f.stat().st_size / (1024*1024)
                    message += f"  • {f.name} ({size_mb:.1f} MB)\n"
                message += "\n"
            
            if video_mov:
                message += f".mov/.mp4 files ({len(video_mov)}):\n"
                for f in video_mov:
                    size_mb = f.stat().st_size / (1024*1024)
                    message += f"  • {f.name} ({size_mb:.1f} MB)\n"
            
            messagebox.showinfo("Available Videos", message)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to list videos: {e}")
    
    def create_processing_tab(self, parent):
        frame = ttk.Frame(parent)
        parent.add(frame, text="Processing Log")
        
        # Progress section
        progress_frame = ttk.LabelFrame(frame, text="Progress", padding=10)
        progress_frame.pack(fill="x", padx=10, pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill="x", pady=5)
        
        self.status_label = ttk.Label(progress_frame, text="Ready to process")
        self.status_label.pack(pady=5)
        
        # Log section
        log_frame = ttk.LabelFrame(frame, text="Processing Log", padding=5)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Log text with scrollbar
        log_container = ttk.Frame(log_frame)
        log_container.pack(fill="both", expand=True)
        
        self.log_text = tk.Text(log_container, state='disabled', wrap='word', height=20)
        log_scrollbar = ttk.Scrollbar(log_container, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scrollbar.pack(side="right", fill="y")
    
    def setup_logging(self):
        """Setup logging to display in GUI"""
        class GUILogHandler(logging.Handler):
            def __init__(self, text_widget):
                super().__init__()
                self.text_widget = text_widget
                
            def emit(self, record):
                msg = self.format(record)
                self.text_widget.after(0, lambda: self.append_log(msg))
                
            def append_log(self, message):
                self.text_widget.config(state='normal')
                self.text_widget.insert(tk.END, message + '\n')
                self.text_widget.see(tk.END)
                self.text_widget.config(state='disabled')
        
        # Add GUI handler to logger
        gui_handler = GUILogHandler(self.log_text)
        gui_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(message)s'))
        logging.getLogger().addHandler(gui_handler)
    
    def browse_360_video(self):
        """Browse for .360 video file"""
        # Start in workspace movies directory if available
        initial_dir = str(self.movies_dir) if self.movies_dir.exists() else None
        
        filetypes = [("360 Video files", "*.360"), ("All files", "*.*")]
        filename = filedialog.askopenfilename(
            title="Select .360 Video File", 
            filetypes=filetypes,
            initialdir=initial_dir
        )
        if filename:
            self.video_360_var.set(filename)
    
    def browse_mov_video(self):
        """Browse for .mov video file"""
        # Start in workspace movies directory if available
        initial_dir = str(self.movies_dir) if self.movies_dir.exists() else None
        
        filetypes = [("MOV Video files", "*.mov *.mp4"), ("All files", "*.*")]
        filename = filedialog.askopenfilename(
            title="Select .mov Video File", 
            filetypes=filetypes,
            initialdir=initial_dir
        )
        if filename:
            self.video_mov_var.set(filename)
            # Auto-suggest output directory based on workspace structure
            video_path = Path(filename)
            if self.workspace_root:
                suggested_output = self.workspace_root / "src" / "gps_ver2" / "output" / f"{video_path.stem}_frames"
            else:
                suggested_output = video_path.parent / f"{video_path.stem}_gps_frames"
            self.output_dir_var.set(str(suggested_output))
    
    def browse_output_dir(self):
        """Browse for output directory"""
        # Start in workspace output directory if available
        initial_dir = str(self.output_dir_default.parent) if self.output_dir_default else None
        
        directory = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=initial_dir
        )
        if directory:
            self.output_dir_var.set(directory)
    
    def browse_nodejs_script(self):
        """Browse for Node.js script"""
        # Start in workspace src directory if available
        initial_dir = str(self.workspace_root / "src" / "gps_ver2") if self.workspace_root else None
        
        filetypes = [("JavaScript files", "*.js"), ("All files", "*.*")]
        filename = filedialog.askopenfilename(
            title="Select Node.js Script", 
            filetypes=filetypes,
            initialdir=initial_dir
        )
        if filename:
            self.nodejs_script_var.set(filename)
    
    def test_nodejs_script(self):
        """Test if Node.js script is working"""
        script_path = self.nodejs_script_var.get()
        
        if not script_path:
            extractor = NodeJSTelemetryExtractor(workspace_root=str(self.workspace_root))
            script_path = extractor.nodejs_script_path
            node_path = extractor.node_path
        else:
            extractor = NodeJSTelemetryExtractor(workspace_root=str(self.workspace_root), nodejs_script_path=script_path)
            node_path = extractor.node_path
        
        if not script_path or not os.path.exists(script_path):
            messagebox.showerror("Error", "Node.js script not found!")
            return
        
        try:
            # Test Node.js availability
            result = subprocess.run([node_path, "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                node_version = result.stdout.strip()
                
                # Test FFmpeg availability
                ffmpeg_info = ""
                if extractor.ffmpeg_path:
                    try:
                        ffmpeg_result = subprocess.run([extractor.ffmpeg_path, "-version"], 
                                                     capture_output=True, text=True)
                        if ffmpeg_result.returncode == 0:
                            ffmpeg_version = ffmpeg_result.stdout.split('\n')[0]
                            ffmpeg_info = f"\nFFmpeg: {ffmpeg_version}"
                    except:
                        ffmpeg_info = "\nFFmpeg: Not available"
                
                workspace_info = f"\nWorkspace: {self.workspace_root}" if self.workspace_root else ""
                
                messagebox.showinfo("Environment Test", 
                    f"Node.js: {node_version}"
                    f"{ffmpeg_info}"
                    f"{workspace_info}"
                    f"\nScript: {script_path}"
                )
            else:
                messagebox.showerror("Error", f"Node.js not working: {result.stderr}")
        except Exception as e:
            messagebox.showerror("Error", f"Error testing environment: {e}")
    
    def validate_360_file(self):
        """Validate .360 file format"""
        video_path = self.video_360_var.get()
        if not video_path:
            messagebox.showerror("Error", "Please select a .360 video file first")
            return
        
        if not os.path.exists(video_path):
            messagebox.showerror("Error", "Selected .360 file does not exist")
            return
        
        try:
            # Test with workspace FFmpeg if available
            extractor = NodeJSTelemetryExtractor(workspace_root=str(self.workspace_root))
            ffmpeg_path = extractor.ffmpeg_path
            
            # Get video info using ffprobe if available
            ffprobe_path = str(Path(ffmpeg_path).parent / "ffprobe") if ffmpeg_path else "ffprobe"
            
            try:
                result = subprocess.run([
                    ffprobe_path, "-v", "quiet", "-print_format", "json", 
                    "-show_format", "-show_streams", video_path
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    import json
                    info = json.loads(result.stdout)
                    format_info = info.get('format', {})
                    streams = info.get('streams', [])
                    
                    video_streams = [s for s in streams if s.get('codec_type') == 'video']
                    data_streams = [s for s in streams if s.get('codec_type') == 'data']
                    
                    info_text = f"File: {Path(video_path).name}\n"
                    info_text += f"Size: {int(format_info.get('size', 0)) / (1024*1024):.1f} MB\n"
                    info_text += f"Duration: {float(format_info.get('duration', 0)):.1f} seconds\n"
                    info_text += f"Video streams: {len(video_streams)}\n"
                    info_text += f"Data streams: {len(data_streams)}\n"
                    
                    if video_streams:
                        vs = video_streams[0]
                        info_text += f"Resolution: {vs.get('width')}x{vs.get('height')}\n"
                        info_text += f"FPS: {eval(vs.get('r_frame_rate', '0/1')):.2f}\n"
                    
                    messagebox.showinfo("Video Information", info_text)
                else:
                    raise Exception("ffprobe failed")
                    
            except:
                # Fallback to OpenCV
                cap = cv2.VideoCapture(video_path)
                if cap.isOpened():
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    cap.release()
                    
                    info = f"Video Info (OpenCV):\nFrames: {frame_count}\nFPS: {fps:.2f}\nResolution: {width}x{height}"
                    messagebox.showinfo("Video Validation", info)
                else:
                    messagebox.showerror("Error", "Cannot open .360 video file")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Error validating video: {e}") 
    
    def start_processing(self):
        """Start the dual video processing workflow"""
        # Validate inputs
        video_360_path = self.video_360_var.get()
        video_mov_path = self.video_mov_var.get()
        output_dir = self.output_dir_var.get()
        
        if not video_360_path or not os.path.exists(video_360_path):
            messagebox.showerror("Error", "Please select a valid .360 video file")
            return
        
        if not video_mov_path or not os.path.exists(video_mov_path):
            messagebox.showerror("Error", "Please select a valid .mov video file")
            return
        
        if not output_dir:
            messagebox.showerror("Error", "Please specify an output directory")
            return
        
        # Update UI state
        self.is_processing = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.progress_var.set(0)
        self.update_status("Initializing processing...")
        
        # Clear log
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        
        # Start processing in separate thread
        self.processing_thread = threading.Thread(target=self.process_dual_videos, daemon=True)
        self.processing_thread.start()
    
    def stop_processing(self):
        """Stop the current processing"""
        self.is_processing = False
        self.update_status("Stopping processing...")
        
        if self.processing_thread and self.processing_thread.is_alive():
            # Give thread time to finish gracefully
            self.processing_thread.join(timeout=2)
        
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.update_status("Processing stopped by user")
    
    def process_dual_videos(self):
        """Main processing workflow for dual video input"""
        try:
            video_360_path = self.video_360_var.get()
            video_mov_path = self.video_mov_var.get()
            output_dir = Path(self.output_dir_var.get())
            
            # Create output directories
            output_dir.mkdir(parents=True, exist_ok=True)
            frames_dir = output_dir / "frames"
            geotagged_dir = output_dir / "geotagged_frames"
            frames_dir.mkdir(exist_ok=True)
            geotagged_dir.mkdir(exist_ok=True)
            
            # Get video info
            cap_mov = cv2.VideoCapture(video_mov_path)
            if not cap_mov.isOpened():
                raise Exception(f"Cannot open .mov video: {video_mov_path}")
            
            total_frames = int(cap_mov.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap_mov.get(cv2.CAP_PROP_FPS)
            cap_mov.release()
            
            logging.info(f"MOV video: {total_frames} frames, {fps:.2f} fps")
            
            if not self.is_processing:
                return
            
            # Step 1: Extract GPS data from .360 video
            self.update_status("Extracting GPS data from .360 video...", 10)
            
            nodejs_script_path = self.nodejs_script_var.get()
            extractor = NodeJSTelemetryExtractor(
                workspace_root=str(self.workspace_root),
                nodejs_script_path=nodejs_script_path
            )
            
            # Use workspace output directory
            workspace_output_dir = self.workspace_root / "src" / "gps_ver2" / "output" if self.workspace_root else output_dir
            
            gps_csv_path = extractor.extract_telemetry_from_360(video_360_path, str(workspace_output_dir))
            
            if not gps_csv_path:
                raise Exception("Failed to extract GPS data from .360 video")
            
            if not self.is_processing:
                return
            
            # Step 2: Load and validate GPS data
            self.update_status("Processing GPS data...", 20)
            
            gps_df = GPSInterpolator.load_and_validate_gps_csv(gps_csv_path)
            if gps_df is None:
                raise Exception("Failed to load valid GPS data")
            
            if not self.is_processing:
                return
            
            # Step 3: Interpolate GPS data for video frames
            self.update_status("Interpolating GPS data for video frames...", 30)
            
            video_fps = self.video_fps_var.get()
            interpolated_gps = GPSInterpolator.interpolate_gps_for_frames(
                gps_df, total_frames, fps=video_fps
            )
            
            if interpolated_gps is None:
                raise Exception("Failed to interpolate GPS data")
            
            # Save interpolated GPS data
            interpolated_csv_path = output_dir / "interpolated_gps.csv"
            interpolated_gps.to_csv(interpolated_csv_path, index=False)
            logging.info(f"Interpolated GPS data saved: {interpolated_csv_path}")
            
            if not self.is_processing:
                return
            
            # Step 4: Extract frames from .mov video
            self.update_status("Extracting frames from .mov video...", 40)
            
            frame_interval = self.frame_interval_var.get()
            show_overlay = self.show_gps_overlay_var.get()
            include_orientation = self.include_orientation_var.get()
            
            extracted_frames = FrameExtractor.extract_frames_with_gps(
                video_mov_path, 
                interpolated_gps, 
                str(frames_dir),
                frame_interval=frame_interval,
                show_gps_overlay=show_overlay,
                include_orientation=include_orientation
            )
            
            if not extracted_frames:
                raise Exception("Failed to extract frames from .mov video")
            
            if not self.is_processing:
                return
            
            # Step 5: Add GPS EXIF tags to frames if requested
            if self.add_gps_exif_var.get():
                self.update_status("Adding GPS EXIF tags to frames...", 70)
                
                self.add_gps_exif_to_frames(extracted_frames, frames_dir, geotagged_dir)
            
            if not self.is_processing:
                return
            
            # Step 6: Generate summary report
            self.update_status("Generating summary report...", 90)
            
            self.generate_processing_report(
                output_dir, extracted_frames, gps_df, interpolated_gps
            )
            
            # Complete
            self.update_status("Processing completed successfully!", 100)
            
            # Show completion dialog
            self.root.after(0, lambda: self.show_completion_dialog(output_dir, len(extracted_frames)))
            
        except Exception as e:
            logging.error(f"Processing failed: {e}")
            self.root.after(0, lambda: messagebox.showerror("Processing Error", f"Processing failed:\n{str(e)}"))
        
        finally:
            # Reset UI state
            self.is_processing = False
            self.root.after(0, lambda: self.reset_ui_state())
    
    def add_gps_exif_to_frames(self, extracted_frames, frames_dir, geotagged_dir):
        """Add GPS EXIF tags to extracted frames"""
        try:
            success_count = 0
            total_frames = len(extracted_frames)
            
            for i, frame_info in enumerate(extracted_frames):
                if not self.is_processing:
                    break
                
                frame_path = frames_dir / frame_info['filename']
                geotagged_path = geotagged_dir / f"gps_{frame_info['filename']}"
                
                gps_data = frame_info.get('gps_data')
                if gps_data and frame_path.exists():
                    success = GeotagProcessor.add_gps_exif(
                        str(frame_path),
                        str(geotagged_path),
                        gps_data['latitude'],
                        gps_data['longitude'],
                        gps_data['altitude']
                    )
                    
                    if success:
                        success_count += 1
                
                # Update progress
                if i % 5 == 0:
                    progress = 70 + (i / total_frames) * 20  # 70-90% range
                    self.update_progress(progress)
            
            logging.info(f"Added GPS EXIF tags to {success_count}/{total_frames} frames")
            
        except Exception as e:
            logging.error(f"Failed to add GPS EXIF tags: {e}")
    
    def generate_processing_report(self, output_dir, extracted_frames, gps_df, interpolated_gps):
        """Generate a summary report of the processing"""
        try:
            report_path = output_dir / "processing_report.txt"
            
            with open(report_path, 'w', encoding='utf-8') as f:
                f.write("GoPro Dual Input GPS Frame Extraction Report\n")
                f.write("=" * 50 + "\n\n")
                
                f.write(f"Processing Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                
                f.write("Input Files:\n")
                f.write(f"  .360 Video: {self.video_360_var.get()}\n")
                f.write(f"  .mov Video: {self.video_mov_var.get()}\n\n")
                
                f.write("Processing Settings:\n")
                f.write(f"  Frame Interval: {self.frame_interval_var.get()}\n")
                f.write(f"  GPS Overlay: {self.show_gps_overlay_var.get()}\n")
                f.write(f"  Include Orientation: {self.include_orientation_var.get()}\n")
                f.write(f"  Add GPS EXIF: {self.add_gps_exif_var.get()}\n\n")
                
                f.write("Results:\n")
                f.write(f"  GPS Points Extracted: {len(gps_df) if gps_df is not None else 0}\n")
                f.write(f"  GPS Points Interpolated: {len(interpolated_gps) if interpolated_gps is not None else 0}\n")
                f.write(f"  Frames Extracted: {len(extracted_frames)}\n\n")
                
                if gps_df is not None and len(gps_df) > 0:
                    f.write("GPS Data Summary:\n")
                    f.write(f"  Latitude Range: {gps_df['latitude'].min():.6f} to {gps_df['latitude'].max():.6f}\n")
                    f.write(f"  Longitude Range: {gps_df['longitude'].min():.6f} to {gps_df['longitude'].max():.6f}\n")
                    f.write(f"  Altitude Range: {gps_df['altitude'].min():.1f}m to {gps_df['altitude'].max():.1f}m\n\n")
                
                f.write("Output Files:\n")
                f.write(f"  Frames Directory: frames/\n")
                if self.add_gps_exif_var.get():
                    f.write(f"  Geotagged Frames: geotagged_frames/\n")
                f.write(f"  Interpolated GPS Data: interpolated_gps.csv\n")
                f.write(f"  Processing Report: processing_report.txt\n")
            
            logging.info(f"Processing report saved: {report_path}")
            
        except Exception as e:
            logging.error(f"Failed to generate processing report: {e}")
    
    def show_completion_dialog(self, output_dir, frame_count):
        """Show completion dialog with results"""
        message = (
            f"Processing completed successfully!\n\n"
            f"Results:\n"
            f"• Extracted {frame_count} frames\n"
            f"• GPS data interpolated for all frames\n"
        )
        
        if self.add_gps_exif_var.get():
            message += f"• GPS EXIF tags added to frames\n"
        
        message += f"\nOutput directory:\n{output_dir}"
        
        result = messagebox.showinfo("Processing Complete", message)
        
        # Ask if user wants to open output directory
        if messagebox.askyesno("Open Output", "Would you like to open the output directory?"):
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(str(output_dir))
                elif os.name == 'posix':  # macOS and Linux
                    subprocess.run(['open' if sys.platform == 'darwin' else 'xdg-open', str(output_dir)])
            except Exception as e:
                logging.error(f"Failed to open output directory: {e}")
    
    def reset_ui_state(self):
        """Reset UI to ready state"""
        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.update_status("Ready to process")
    
    def update_status(self, message, progress=None):
        """Update status label and optionally progress"""
        self.status_label.config(text=message)
        if progress is not None:
            self.update_progress(progress)
        logging.info(message)
    
    def update_progress(self, value):
        """Update progress bar"""
        self.progress_var.set(min(100, max(0, value)))
        self.root.update_idletasks()

def main():
    """Main function to run the application"""
    # Create the main window
    root = tk.Tk()
    
    # Set minimum window size
    root.minsize(900, 600)
    
    # Try to set application icon
    try:
        # If you have an icon file, uncomment and modify this line:
        # root.iconbitmap("icon.ico")
        pass
    except:
        pass
    
    # Center window on screen
    root.update_idletasks()
    width = 1000
    height = 800
    x = (root.winfo_screenwidth() // 2) - (width // 2)
    y = (root.winfo_screenheight() // 2) - (height // 2)
    root.geometry(f"{width}x{height}+{x}+{y}")
    
    # Create and run the application
    app = GoProDualInputGUI(root)
    
    # Handle window closing
    def on_closing():
        if app.is_processing:
            if messagebox.askokcancel("Quit", "Processing is in progress. Do you want to stop and quit?"):
                app.stop_processing()
                root.destroy()
        else:
            root.destroy()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Start the GUI event loop
    root.mainloop()

if __name__ == "__main__":
    # Check dependencies
    try:
        import cv2
        import pandas as pd
        import numpy as np
        import piexif
        from PIL import Image
        from scipy.interpolate import interp1d
    except ImportError as e:
        print(f"Missing required dependency: {e}")
        print("\nPlease install required packages:")
        print("pip install opencv-python pandas numpy pillow piexif scipy")
        sys.exit(1)
    
    main()