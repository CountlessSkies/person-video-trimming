import os
import shutil
import tempfile
import cv2
import numpy as np
import queue
import threading
from PySide6.QtCore import QThread, Signal
from face_engine import FaceEngine

class ScanWorker(QThread):
    progress = Signal(str, int)  # status_msg, progress_percent
    finished = Signal(str, list, float) # video_path, all_detected_faces, actual_interval
    error = Signal(str)           # error message
    
    def __init__(self, video_path, sample_interval=1.0, similarity_threshold=0.363, min_cluster_size=2):
        super().__init__()
        self.video_path = video_path
        self.sample_interval = sample_interval
        self.similarity_threshold = similarity_threshold
        self.min_cluster_size = min_cluster_size
        self.is_running = True
        
    def stop(self):
        self.is_running = False
        
    def run(self):
        try:
            # 1. Initialize FaceEngine
            self.progress.emit("Initializing AI models...", 0)
            engine = FaceEngine()
            engine.ensure_models_downloaded(lambda msg: self.progress.emit(msg, 0))
            
            # 2. Open Video File using CPU metadata reader first
            cap = cv2.VideoCapture(self.video_path)
            if not cap.isOpened():
                self.error.emit("Failed to open video file.")
                return
                
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release() # Release immediately as we will use FFmpeg for main decoding
            
            if fps <= 0 or total_frames <= 0:
                self.error.emit("Invalid video metadata (FPS or frame count is zero).")
                return
                
            # Configure scaled dimensions for fast face detection
            # Scale down to width = 640 for speed, preserving aspect ratio
            scaled_width = 640
            aspect_ratio = height / width
            scaled_height = int(scaled_width * aspect_ratio)
            scaled_height = scaled_height + (scaled_height % 2)
            
            engine.initialize(input_size=(scaled_width, scaled_height))
            
            # Create thumbnail directory
            temp_dir = os.path.join(tempfile.gettempdir(), "person_trimmer_thumbs")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            os.makedirs(temp_dir, exist_ok=True)
            
            # Setup intervals
            if self.sample_interval <= 0:
                actual_interval = 1.0 / fps
            else:
                actual_interval = self.sample_interval
                
            all_detected_faces = []
            
            # Attempt to spawn GPU-accelerated FFmpeg decoding process
            ffmpeg_process = None
            use_ffmpeg = False
            try:
                import subprocess
                # Command to decode using CUDA on GPU, downsample fps, and scale to 640 width on GPU
                cmd = [
                    "ffmpeg", "-y",
                    "-hwaccel", "cuda",
                    "-i", self.video_path,
                ]
                
                vf_filters = []
                if self.sample_interval > 0:
                    target_fps = 1.0 / self.sample_interval
                    vf_filters.append(f"fps={target_fps}")
                vf_filters.append(f"scale=640:-2")
                
                cmd += [
                    "-vf", ",".join(vf_filters), 
                    "-f", "rawvideo", 
                    "-pix_fmt", "bgr24", 
                    "pipe:1"
                ]
                
                # Start FFmpeg subprocess
                ffmpeg_process = subprocess.Popen(
                    cmd, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.DEVNULL,
                    bufsize=10**8
                )
                use_ffmpeg = True
                print("FaceEngine using GPU-accelerated FFmpeg decoder (nvdec)!")
            except Exception as e:
                print(f"Failed to initialize FFmpeg GPU decoder, falling back to OpenCV CPU: {e}")
                use_ffmpeg = False
                
            frame_size = scaled_width * scaled_height * 3
            
            if use_ffmpeg:
                # GPU/FFmpeg multi-threaded pipeline flow
                frame_queue = queue.Queue(maxsize=64)
                face_queue = queue.Queue(maxsize=64)
                SENTINEL = None
                
                # 1. Reader Thread
                def reader_worker():
                    n = 0
                    try:
                        while self.is_running:
                            raw_frame = ffmpeg_process.stdout.read(frame_size)
                            if not raw_frame or len(raw_frame) != frame_size:
                                break
                            
                            resized_frame = np.frombuffer(raw_frame, dtype=np.uint8).reshape((scaled_height, scaled_width, 3))
                            sec = n * actual_interval
                            frame_idx = int(sec * fps)
                            
                            frame_queue.put((frame_idx, sec, resized_frame))
                            n += 1
                    except Exception as e:
                        print(f"Reader Thread error: {e}")
                    finally:
                        frame_queue.put(SENTINEL)
                
                # 2. Detector Thread
                def detector_worker():
                    while self.is_running:
                        item = frame_queue.get()
                        if item is SENTINEL:
                            face_queue.put(SENTINEL)
                            break
                        
                        frame_idx, sec, frame = item
                        try:
                            faces = engine.detect_faces(frame)
                            face_queue.put((frame_idx, sec, frame, faces))
                        except Exception as e:
                            print(f"Detector Thread error: {e}")
                            face_queue.put((frame_idx, sec, frame, []))
                
                # Launch threads
                t_reader = threading.Thread(target=reader_worker, daemon=True)
                t_detector = threading.Thread(target=detector_worker, daemon=True)
                t_reader.start()
                t_detector.start()
                
                # 3. Main thread (Extractor & progress updates)
                processed_count = 0
                duration = total_frames / fps
                total_expected_frames = max(1, int(duration / actual_interval))
                
                while self.is_running:
                    item = face_queue.get()
                    if item is SENTINEL:
                        break
                    
                    frame_idx, sec, frame, faces = item
                    
                    # Process detected faces
                    for face_idx, face in enumerate(faces):
                        confidence = float(face[14])
                        if confidence < 0.85:
                            continue
                            
                        try:
                            aligned_crop, embedding = engine.extract_embedding(frame, face)
                        except cv2.error:
                            continue
                            
                        x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                        margin_x, margin_y = int(w * 0.15), int(h * 0.15)
                        crop_x = max(0, x - margin_x)
                        crop_y = max(0, y - margin_y)
                        crop_w = min(scaled_width - crop_x, w + 2 * margin_x)
                        crop_h = min(scaled_height - crop_y, h + 2 * margin_y)
                        
                        face_thumb = frame[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
                        
                        thumb_filename = f"face_{frame_idx}_{face_idx}.jpg"
                        thumb_path = os.path.join(temp_dir, thumb_filename)
                        cv2.imwrite(thumb_path, face_thumb)
                        
                        all_detected_faces.append({
                            'embedding': embedding,
                            'frame_idx': frame_idx,
                            'sec': sec,
                            'confidence': confidence,
                            'thumb_path': thumb_path,
                            'face_box': (x, y, w, h),
                            'video_path': self.video_path
                        })
                        
                    processed_count += 1
                    progress_percent = min(90, int((processed_count / total_expected_frames) * 90))
                    self.progress.emit(f"Scanning frame {frame_idx}/{total_frames} ({sec:.1f}s)...", progress_percent)
                    
                # Safe cleanup
                ffmpeg_process.terminate()
                t_reader.join(timeout=1.0)
                t_detector.join(timeout=1.0)
                
            else:
                # OpenCV CPU fallback flow
                cap = cv2.VideoCapture(self.video_path)
                sampling_step = max(1, int(self.sample_interval * fps))
                frame_idx = 0
                while self.is_running:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
                    ret, frame = cap.read()
                    if not ret:
                        break
                        
                    resized_frame = cv2.resize(frame, (scaled_width, scaled_height))
                    faces = engine.detect_faces(resized_frame)
                    
                    for face_idx, face in enumerate(faces):
                        confidence = float(face[14])
                        if confidence < 0.85:
                            continue
                            
                        try:
                            aligned_crop, embedding = engine.extract_embedding(resized_frame, face)
                        except cv2.error:
                            continue
                            
                        x, y, w, h = int(face[0]), int(face[1]), int(face[2]), int(face[3])
                        margin_x, margin_y = int(w * 0.15), int(h * 0.15)
                        crop_x = max(0, x - margin_x)
                        crop_y = max(0, y - margin_y)
                        crop_w = min(scaled_width - crop_x, w + 2 * margin_x)
                        crop_h = min(scaled_height - crop_y, h + 2 * margin_y)
                        
                        face_thumb = resized_frame[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
                        
                        thumb_filename = f"face_{frame_idx}_{face_idx}.jpg"
                        thumb_path = os.path.join(temp_dir, thumb_filename)
                        cv2.imwrite(thumb_path, face_thumb)
                        
                        sec = frame_idx / fps
                        all_detected_faces.append({
                            'embedding': embedding,
                            'frame_idx': frame_idx,
                            'sec': sec,
                            'confidence': confidence,
                            'thumb_path': thumb_path,
                            'face_box': (x, y, w, h),
                            'video_path': self.video_path
                        })
                        
                    progress_percent = int((frame_idx / total_frames) * 90)
                    self.progress.emit(f"Scanning frame {frame_idx}/{total_frames} ({frame_idx/fps:.1f}s)...", progress_percent)
                    
                    frame_idx += sampling_step
                    if frame_idx >= total_frames:
                        break
                        
                cap.release()
            
            if not self.is_running:
                self.progress.emit("Scan cancelled.", 0)
                return
                
            if not all_detected_faces:
                self.progress.emit("No faces detected in the video.", 100)
                self.finished.emit(self.video_path, [], actual_interval)
                return
                
            self.progress.emit("Scanning complete!", 100)
            self.finished.emit(self.video_path, all_detected_faces, actual_interval)
            
        except Exception as e:
            self.error.emit(str(e))

class ExportWorker(QThread):
    progress = Signal(str, int)  # status_msg, progress_percent
    finished = Signal(str)       # output_path
    error = Signal(str)           # error message
    
    def __init__(self, inputs_and_segments, output_video=None, reencode=True):
        """
        inputs_and_segments: dict of {input_video_path: list of segments}
        output_video: str (for combined mode) or None (for separate mode)
        """
        super().__init__()
        self.inputs_and_segments = inputs_and_segments
        self.output_video = output_video
        self.reencode = reencode
        
    def run(self):
        try:
            from video_utils import trim_and_merge_video, trim_and_merge_multiple_videos
            
            if self.output_video:
                # Combined mode: output all segments to 1 file
                trim_and_merge_multiple_videos(
                    self.inputs_and_segments,
                    self.output_video,
                    reencode=self.reencode,
                    progress_callback=self.progress.emit
                )
                self.finished.emit(self.output_video)
            else:
                # Separate mode: output each video's segments separately
                total_videos = len(self.inputs_and_segments)
                last_output = ""
                for idx, (input_video, segments) in enumerate(self.inputs_and_segments.items()):
                    # Determine output name
                    dir_name = os.path.dirname(input_video)
                    base_name = os.path.basename(input_video)
                    name, ext = os.path.splitext(base_name)
                    output_path = os.path.join(dir_name, f"{name}_trimmed{ext}")
                    
                    # Define a wrapped progress callback to show overall progress
                    def sub_callback(status, percent):
                        overall_percent = int((idx / total_videos * 100) + (percent / total_videos))
                        self.progress.emit(f"[{idx+1}/{total_videos}] {status}", overall_percent)
                        
                    trim_and_merge_video(
                        input_video,
                        segments,
                        output_path,
                        reencode=self.reencode,
                        progress_callback=sub_callback
                    )
                    last_output = output_path
                self.finished.emit("separate" if total_videos > 1 else last_output)
        except Exception as e:
            self.error.emit(str(e))

