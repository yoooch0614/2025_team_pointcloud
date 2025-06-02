import os
import threading
import datetime
import time
from pathlib import Path
import cv2
import numpy as np
import logging
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
import json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

def get_rotation_matrix(yaw_radian: float, pitch_radian: float) -> np.ndarray:
    R_yaw = np.array([
        [np.cos(yaw_radian), 0, np.sin(yaw_radian)],
        [0, 1, 0],
        [-np.sin(yaw_radian), 0, np.cos(yaw_radian)]
    ], dtype=np.float32)

    R_pitch = np.array([
        [1, 0, 0],
        [0, np.cos(pitch_radian), -np.sin(pitch_radian)],
        [0, np.sin(pitch_radian), np.cos(pitch_radian)]
    ], dtype=np.float32)

    return np.dot(R_pitch, R_yaw)

@lru_cache(maxsize=None)
def precompute_mapping(W: int, H: int, FOV_rad: float, yaw_radian: float, pitch_radian: float, pano_width: int, pano_height: int) -> tuple:
    f = (0.5 * W) / np.tan(FOV_rad / 2)

    u, v = np.meshgrid(np.arange(W), np.arange(H), indexing='xy')
    u = u.astype(np.float32)
    v = v.astype(np.float32)

    x = u - (W / 2.0)
    y = (H / 2.0) - v
    z = np.full_like(x, f, dtype=np.float32)

    norm = np.sqrt(x**2 + y**2 + z**2)
    x_norm = x / norm
    y_norm = y / norm
    z_norm = z / norm

    R = get_rotation_matrix(yaw_radian, pitch_radian)
    vectors = np.stack((x_norm, y_norm, z_norm), axis=0)  # Shape: (3, H, W)
    rotated = R @ vectors.reshape(3, -1)
    rotated = rotated.reshape(3, H, W)
    x_rot, y_rot, z_rot = rotated

    theta_prime = np.arccos(z_rot).astype(np.float32)
    phi_prime = (np.arctan2(y_rot, x_rot) % (2 * np.pi)).astype(np.float32)

    U = (phi_prime * pano_width) / (2 * np.pi)
    V = (theta_prime * pano_height) / np.pi

    U = np.clip(U, 0, pano_width - 1).astype(np.float32)
    V = np.clip(V, 0, pano_height - 1).astype(np.float32)

    return U, V

def interpolate_color(U: np.ndarray, V: np.ndarray, img: np.ndarray, method: str = 'bilinear') -> np.ndarray:
    interpolation_methods = {
        'nearest': cv2.INTER_NEAREST,
        'bilinear': cv2.INTER_LINEAR,
        'bicubic': cv2.INTER_CUBIC
    }
    interp = interpolation_methods.get(method, cv2.INTER_LINEAR)
    remapped = cv2.remap(img, U, V, interpolation=interp, borderMode=cv2.BORDER_REFLECT)
    return remapped

def panorama_to_plane(pano_array: np.ndarray, U: np.ndarray, V: np.ndarray) -> np.ndarray:
    return interpolate_color(U, V, pano_array)

def process_video_frame(frame: np.ndarray, args, precomputed_mappings: dict) -> list:
    """
    Process a single video frame with the panorama to plane projection.
    Returns a list of processed frames (one for each yaw angle).
    """
    processed_frames = []
    try:
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frame_height, frame_width, _ = frame_rgb.shape
        
        for yaw in args['yaw_angles']:
            U, V = precomputed_mappings[yaw]
            output_image_array = panorama_to_plane(frame_rgb, U, V)
            # Convert back to BGR for OpenCV
            output_bgr = cv2.cvtColor(output_image_array, cv2.COLOR_RGB2BGR)
            processed_frames.append((yaw, output_bgr))
            
    except Exception as e:
        logging.error(f"Failed to process video frame: {e}")
        
    return processed_frames

class VideoPanoramaGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("360° Video to Plane Projection")
        self.profile_file = Path.home() / ".panorama_to_plane" / "profiles.json"
        self.profile_file.parent.mkdir(parents=True, exist_ok=True)
        self.load_profiles()
        
        # Set up the main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Create input and settings frames
        self.create_input_frame(main_frame)
        self.create_settings_frame(main_frame)
        self.create_control_frame(main_frame)
        self.create_log_frame(main_frame)
        self.create_profile_frame(main_frame)
        
        # Set up logging
        self.setup_logging()

    def create_input_frame(self, parent):
        input_frame = ttk.LabelFrame(parent, text="Input/Output", padding="10")
        input_frame.pack(fill="x", pady=5)
        
        # Video input
        ttk.Label(input_frame, text="Input 360° Video:").grid(row=0, column=0, sticky="w", pady=5)
        self.input_video_var = tk.StringVar()
        self.input_video_entry = ttk.Entry(input_frame, textvariable=self.input_video_var, width=60)
        self.input_video_entry.grid(row=0, column=1, padx=5, sticky="we")
        ttk.Button(input_frame, text="Browse", command=self.browse_input_video).grid(row=0, column=2, padx=5)
        
        # Output directory
        ttk.Label(input_frame, text="Output Directory:").grid(row=1, column=0, sticky="w", pady=5)
        self.output_dir_var = tk.StringVar()
        self.output_dir_entry = ttk.Entry(input_frame, textvariable=self.output_dir_var, width=60)
        self.output_dir_entry.grid(row=1, column=1, padx=5, sticky="we")
        ttk.Button(input_frame, text="Browse", command=self.browse_output_dir).grid(row=1, column=2, padx=5)
        
        # Configure grid columns
        input_frame.columnconfigure(1, weight=1)

    def create_settings_frame(self, parent):
        settings_frame = ttk.LabelFrame(parent, text="Processing Settings", padding="10")
        settings_frame.pack(fill="x", pady=5)
        
        # Create a two-column layout
        left_column = ttk.Frame(settings_frame)
        left_column.grid(row=0, column=0, padx=10, sticky="nw")
        
        right_column = ttk.Frame(settings_frame)
        right_column.grid(row=0, column=1, padx=10, sticky="nw")
        
        # Left column settings - Frame extraction and output
        ttk.Label(left_column, text="Frame Settings:").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        
        ttk.Label(left_column, text="Extract every N frames:").grid(row=1, column=0, sticky="w", pady=2)
        self.frame_interval_var = tk.IntVar(value=15)
        self.frame_interval_spin = ttk.Spinbox(left_column, from_=1, to=300, textvariable=self.frame_interval_var, width=10)
        self.frame_interval_spin.grid(row=1, column=1, padx=5, sticky="w")
        
        # Output format
        ttk.Label(left_column, text="Output Format:").grid(row=3, column=0, sticky="w", pady=2)
        self.format_var = tk.StringVar(value="jpg")
        format_combo = ttk.Combobox(left_column, textvariable=self.format_var, 
                                     values=["jpg", "png"], state="readonly", width=8)
        format_combo.grid(row=3, column=1, padx=5, sticky="w")
        
        # Organize by Yaw option
        ttk.Label(left_column, text="Organize by Yaw Angle:").grid(row=4, column=0, sticky="w", pady=2)
        self.organize_by_yaw_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(left_column, text="", variable=self.organize_by_yaw_var).grid(row=4, column=1, padx=5, sticky="w")
        
        ttk.Label(left_column, text="Save individual views:").grid(row=5, column=0, sticky="w", pady=2)
        self.save_separate_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(left_column, text="", variable=self.save_separate_var).grid(row=5, column=1, padx=5, sticky="w")
        
        # Right column settings - Projection parameters
        ttk.Label(right_column, text="Projection Settings:").grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 5))
        
        ttk.Label(right_column, text="Field of View (FOV) [degrees]:").grid(row=1, column=0, sticky="w", pady=2)
        self.fov_var = tk.IntVar(value=90)
        self.fov_spin = ttk.Spinbox(right_column, from_=10, to=180, textvariable=self.fov_var, width=10)
        self.fov_spin.grid(row=1, column=1, padx=5, sticky="w")
        
        ttk.Label(right_column, text="Output Width [px]:").grid(row=2, column=0, sticky="w", pady=2)
        self.width_var = tk.IntVar(value=1500)
        self.width_spin = ttk.Spinbox(right_column, from_=100, to=5000, textvariable=self.width_var, width=10)
        self.width_spin.grid(row=2, column=1, padx=5, sticky="w")
        
        ttk.Label(right_column, text="Output Height [px]:").grid(row=3, column=0, sticky="w", pady=2)
        self.height_var = tk.IntVar(value=1500)
        self.height_spin = ttk.Spinbox(right_column, from_=100, to=5000, textvariable=self.height_var, width=10)
        self.height_spin.grid(row=3, column=1, padx=5, sticky="w")
        
        ttk.Label(right_column, text="Pitch Angle [degrees]:").grid(row=4, column=0, sticky="w", pady=2)
        self.pitch_var = tk.IntVar(value=90)
        self.pitch_spin = ttk.Spinbox(right_column, from_=1, to=179, textvariable=self.pitch_var, width=10)
        self.pitch_spin.grid(row=4, column=1, padx=5, sticky="w")
        
        ttk.Label(right_column, text="Yaw Angles [degrees, comma-separated]:").grid(row=5, column=0, sticky="w", pady=2)
        self.yaw_var = tk.StringVar(value="0,90,180,270")
        self.yaw_entry = ttk.Entry(right_column, textvariable=self.yaw_var, width=25)
        self.yaw_entry.grid(row=5, column=1, padx=5, sticky="w")
        
        ttk.Label(right_column, text="Worker Threads:").grid(row=6, column=0, sticky="w", pady=2)
        self.worker_var = tk.IntVar(value=max(1, os.cpu_count() or 1))
        self.worker_spin = ttk.Spinbox(right_column, from_=1, to=os.cpu_count()*2, 
                                      textvariable=self.worker_var, width=10)
        self.worker_spin.grid(row=6, column=1, padx=5, sticky="w")

    def create_control_frame(self, parent):
        control_frame = ttk.Frame(parent, padding="10")
        control_frame.pack(fill="x", pady=5)
        
        # Start button
        self.start_button = ttk.Button(control_frame, text="Start Processing", command=self.start_processing)
        self.start_button.pack(pady=5)
        
        # Progress bar and label
        progress_frame = ttk.Frame(control_frame)
        progress_frame.pack(fill="x", pady=5)
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100, length=400)
        self.progress_bar.pack(side="left", fill="x", expand=True, padx=5)
        
        self.progress_label = ttk.Label(progress_frame, text="0%")
        self.progress_label.pack(side="right", padx=5)

    def create_log_frame(self, parent):
        log_frame = ttk.LabelFrame(parent, text="Processing Log", padding="10")
        log_frame.pack(fill="both", expand=True, pady=5)
        
        # Log text widget with scrollbar
        log_scroll = ttk.Scrollbar(log_frame)
        log_scroll.pack(side="right", fill="y")
        
        self.log_text = tk.Text(log_frame, height=10, state='disabled', yscrollcommand=log_scroll.set)
        self.log_text.pack(fill="both", expand=True)
        
        log_scroll.config(command=self.log_text.yview)

    def create_profile_frame(self, parent):
        profile_frame = ttk.LabelFrame(parent, text="Profile Management", padding="10")
        profile_frame.pack(fill="x", pady=5)
        
        # Profile name and save
        profile_row1 = ttk.Frame(profile_frame)
        profile_row1.pack(fill="x", pady=2)
        
        ttk.Label(profile_row1, text="Profile Name:").pack(side="left", padx=5)
        self.profile_name_var = tk.StringVar()
        profile_name_entry = ttk.Entry(profile_row1, textvariable=self.profile_name_var, width=30)
        profile_name_entry.pack(side="left", padx=5)
        
        ttk.Button(profile_row1, text="Save Profile", command=self.save_profile).pack(side="left", padx=5)
        
        # Profile selection and load
        profile_row2 = ttk.Frame(profile_frame)
        profile_row2.pack(fill="x", pady=2)
        
        ttk.Label(profile_row2, text="Select Profile:").pack(side="left", padx=5)
        self.selected_profile = tk.StringVar()
        self.profile_combo = ttk.Combobox(profile_row2, textvariable=self.selected_profile, 
                                          values=self.get_profile_names(), state="readonly", width=28)
        self.profile_combo.pack(side="left", padx=5)
        
        ttk.Button(profile_row2, text="Load Profile", command=self.load_profile).pack(side="left", padx=5)
        ttk.Button(profile_row2, text="Delete Profile", command=self.delete_profile).pack(side="left", padx=5)

    def setup_logging(self):
        self.logger = logging.getLogger()
        self.logger.handlers = []
        handler = TextHandler(self.log_text)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def browse_input_video(self):
        filetypes = [
            ("Video files", "*.mp4 *.avi *.mov *.mkv *.webm"),
            ("All files", "*.*")
        ]
        filename = filedialog.askopenfilename(filetypes=filetypes)
        if filename:
            self.input_video_var.set(filename)
            
            # Suggest output directory based on input file
            input_path = Path(filename)
            default_output = input_path.parent / f"{input_path.stem}_processed"
            self.output_dir_var.set(str(default_output))

    def browse_output_dir(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_dir_var.set(directory)

    def get_profile_names(self):
        if self.profile_file.exists():
            with open(self.profile_file, 'r') as f:
                profiles = json.load(f)
            return list(profiles.keys())
        return []

    def load_profiles(self):
        self.profiles = {}
        if self.profile_file.exists():
            with open(self.profile_file, 'r') as f:
                self.profiles = json.load(f)

    def save_profiles_to_file(self):
        with open(self.profile_file, 'w') as f:
            json.dump(self.profiles, f, indent=4)

    def save_profile(self):
        name = self.profile_name_var.get().strip()
        if not name:
            messagebox.showerror("Error", "Profile name cannot be empty.")
            return
            
        self.profiles[name] = {
            'frame_interval': self.frame_interval_var.get(),
            'output_format': self.format_var.get(),
            'FOV': self.fov_var.get(),
            'output_width': self.width_var.get(),
            'output_height': self.height_var.get(),
            'pitch': self.pitch_var.get(),
            'yaw_angles': self.yaw_var.get(),
            'num_workers': self.worker_var.get(),
            'save_separate': self.save_separate_var.get(),
            'organize_by_yaw': self.organize_by_yaw_var.get()
        }
        
        self.save_profiles_to_file()
        self.profile_combo['values'] = self.get_profile_names()
        messagebox.showinfo("Success", f"Profile '{name}' saved successfully.")

    def load_profile(self):
        name = self.selected_profile.get()
        if not name:
            messagebox.showerror("Error", "No profile selected.")
            return
            
        profile = self.profiles.get(name, {})
        
        # Load all settings from profile
        self.frame_interval_var.set(profile.get('frame_interval', 15))
        self.format_var.set(profile.get('output_format', "jpg"))
        self.fov_var.set(profile.get('FOV', 90))
        self.width_var.set(profile.get('output_width', 1500))
        self.height_var.set(profile.get('output_height', 1500))
        self.pitch_var.set(profile.get('pitch', 90))
        self.yaw_var.set(profile.get('yaw_angles', "0,90,180,270"))
        self.worker_var.set(profile.get('num_workers', max(1, os.cpu_count() or 1)))
        self.save_separate_var.set(profile.get('save_separate', True))
        self.organize_by_yaw_var.set(profile.get('organize_by_yaw', False))
        
        messagebox.showinfo("Success", f"Profile '{name}' loaded successfully.")

    def delete_profile(self):
        name = self.selected_profile.get()
        if not name:
            messagebox.showerror("Error", "No profile selected.")
            return
            
        if messagebox.askyesno("Confirm", f"Are you sure you want to delete profile '{name}'?"):
            del self.profiles[name]
            self.save_profiles_to_file()
            self.profile_combo['values'] = self.get_profile_names()
            self.selected_profile.set('')
            messagebox.showinfo("Success", f"Profile '{name}' deleted successfully.")

    def start_processing(self):
        # Get input parameters
        video_path = self.input_video_var.get()
        output_dir = self.output_dir_var.get()
        
        # Validate inputs
        if not video_path or not os.path.isfile(video_path):
            messagebox.showerror("Error", "Please select a valid video file.")
            return
            
        if not output_dir:
            messagebox.showerror("Error", "Please specify an output directory.")
            return
            
        # Parse yaw angles
        try:
            yaw_angles = [int(yaw.strip()) for yaw in self.yaw_var.get().split(",") if yaw.strip().isdigit()]
            if not yaw_angles:
                raise ValueError("No valid yaw angles specified.")
                
            for yaw in yaw_angles:
                if not (0 <= yaw <= 360):
                    raise ValueError(f"Yaw angle {yaw} is outside the valid range (0-360 degrees).")
                    
            # Get other settings
            frame_interval = int(self.frame_interval_var.get())
            if frame_interval < 1:
                raise ValueError("Frame interval must be at least 1.")
                
            pitch = int(self.pitch_var.get())
            if not (1 <= pitch <= 179):
                raise ValueError("Pitch must be between 1 and 179 degrees.")
                
            fov = int(self.fov_var.get())
            output_width = int(self.width_var.get())
            output_height = int(self.height_var.get())
            output_format = self.format_var.get()
            num_workers = int(self.worker_var.get())
            save_separate = self.save_separate_var.get()
            
            if not save_separate:
                raise ValueError("Save individual views must be selected.")
                
        except ValueError as e:
            messagebox.showerror("Invalid Settings", str(e))
            return
            
        # Package settings
        settings = {
            'video_path': video_path,
            'output_dir': output_dir,
            'frame_interval': frame_interval,
            'FOV': fov,
            'output_width': output_width,
            'output_height': output_height,
            'pitch': pitch,
            'yaw_angles': sorted(list(set(yaw_angles))),
            'output_format': output_format,
            'num_workers': num_workers,
            'save_separate': save_separate,
            'organize_by_yaw': self.organize_by_yaw_var.get()
        }
        
        # Disable UI while processing
        self.start_button.config(state='disabled')
        
        # Clear log and reset progress
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state='disabled')
        self.progress_var.set(0)
        self.progress_label.config(text="0%")
        
        # Start processing in a separate thread
        threading.Thread(target=self.process_video, args=(settings,), daemon=True).start()

    def process_video(self, settings):
        try:
            # Create timestamp for this run
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            video_path = Path(settings['video_path'])
            output_base_dir = Path(settings['output_dir'])
            
            # Make sure output directory exists
            output_base_dir.mkdir(parents=True, exist_ok=True)
            logging.info(f"Output directory: {output_base_dir}")
            
            # Open the video
            logging.info(f"Opening video file: {video_path}")
            cap = cv2.VideoCapture(str(video_path))
            
            if not cap.isOpened():
                logging.error(f"Failed to open video file: {video_path}")
                messagebox.showerror("Error", f"Failed to open video file: {video_path}")
                self.start_button.config(state='normal')
                return
                
            # Get video info
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            video_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            video_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            
            logging.info(f"Video info: {video_width}x{video_height}, {fps:.2f} fps, {total_frames} frames")
            
            # Create output directories for each yaw angle if organizing by yaw
            yaw_folders = {}
            if settings['organize_by_yaw']:
                for yaw in settings['yaw_angles']:
                    yaw_dir = output_base_dir / f"yaw_{yaw}"
                    yaw_dir.mkdir(exist_ok=True)
                    yaw_folders[yaw] = yaw_dir
                logging.info(f"Created separate directories for each yaw angle")
            
            # Precompute projection mappings
            logging.info(f"Precomputing projection mappings...")
            FOV_rad = np.radians(settings['FOV'])
            pitch_rad = np.radians(settings['pitch'])
            precomputed_mappings = {}
            
            for yaw in settings['yaw_angles']:
                yaw_rad = np.radians(yaw)
                U, V = precompute_mapping(
                    W=settings['output_width'],
                    H=settings['output_height'],
                    FOV_rad=FOV_rad,
                    yaw_radian=yaw_rad,
                    pitch_radian=pitch_rad,
                    pano_width=video_width,
                    pano_height=video_height
                )
                precomputed_mappings[yaw] = (U, V)
            
            # Process the frames
            logging.info(f"Starting frame processing with interval {settings['frame_interval']}...")
            frame_id = 0
            processed_count = 0
            start_time = time.time()
            
            # Create a thread pool for parallel processing
            executor = ThreadPoolExecutor(max_workers=settings['num_workers'])
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                    
                # Process frame at the specified interval
                if frame_id % settings['frame_interval'] == 0:
                    # Create a future for this frame
                    future = executor.submit(
                        process_video_frame, 
                        frame, 
                        settings, 
                        precomputed_mappings
                    )
                    
                    # Get the processed frame projections
                    processed_frames = future.result()
                    
                    # Save separate images if requested
                    if settings['save_separate']:
                        for yaw, processed_frame in processed_frames:
                            # Choose the correct output directory based on organize_by_yaw setting
                            if settings['organize_by_yaw']:
                                output_path = yaw_folders[yaw] / f"frame_{processed_count:05d}.{settings['output_format']}"
                            else:
                                output_path = output_base_dir / f"frame_{processed_count:05d}_yaw_{yaw}.{settings['output_format']}"
                            
                            cv2.imwrite(str(output_path), processed_frame)
                    
                    # Update progress
                    processed_count += 1
                    progress = (frame_id / total_frames) * 100
                    self.update_progress(progress)
                    
                    # Log progress periodically
                    if processed_count % 10 == 0:
                        elapsed = time.time() - start_time
                        frames_per_second = processed_count / elapsed if elapsed > 0 else 0
                        logging.info(f"Processed {processed_count} frames ({frames_per_second:.2f} fps)")
                
                frame_id += 1
            
            # Cleanup
            cap.release()
            executor.shutdown()
                
            elapsed_time = time.time() - start_time
            logging.info(f"Processing completed in {elapsed_time:.2f} seconds")
            logging.info(f"Processed {processed_count} frames out of {total_frames} total frames")
            
            # Show completion message
            def show_completion():
                messagebox.showinfo(
                    "Processing Complete", 
                    f"Successfully processed video with {len(settings['yaw_angles'])} yaw angles.\n"
                    f"Output saved to: {output_base_dir}"
                )
                
            self.root.after(0, show_completion)
            
        except Exception as e:
            logging.error(f"Error processing video: {e}")
            messagebox.showerror("Error", f"Failed to process video: {str(e)}")
        finally:
            # Re-enable the UI
            self.start_button.config(state='normal')
            
    def update_progress(self, progress_value):
        """Update the progress bar and label."""
        self.progress_var.set(progress_value)
        self.progress_label.config(text=f"{progress_value:.1f}%")
        
        # Force UI update
        self.root.update_idletasks()

class TextHandler(logging.Handler):
    """Handler to redirect logging to a text widget."""
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        
    def emit(self, record):
        msg = self.format(record)
        def append():
            self.text_widget.config(state='normal')
            self.text_widget.insert(tk.END, msg + '\n')
            self.text_widget.see(tk.END)
            self.text_widget.config(state='disabled')
        self.text_widget.after(0, append)

def main():
    root = tk.Tk()
    app = VideoPanoramaGUI(root)
    root.geometry("1000x800")  # Initial window size
    root.mainloop()

if __name__ == "__main__":
    main()