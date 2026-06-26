import os
import urllib.request
import numpy as np
import cv2
import threading

# ONNX Model URLs from OpenCV Zoo
YUNET_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
SFACE_URL = "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"

class FaceEngine:
    _init_lock = threading.Lock()
    def __init__(self, models_dir="models"):
        self.models_dir = models_dir
        os.makedirs(self.models_dir, exist_ok=True)
        self.yunet_path = os.path.join(self.models_dir, "face_detection_yunet_2023mar.onnx")
        self.sface_path = os.path.join(self.models_dir, "face_recognition_sface_2021dec.onnx")
        
        self.detector = None
        self.recognizer = None
        self.ort_session = None

    def ensure_models_downloaded(self, progress_callback=None):
        """Downloads the ONNX models if they do not exist."""
        def download_file(url, filepath, name):
            if not os.path.exists(filepath):
                if progress_callback:
                    progress_callback(f"Downloading {name} model...")
                urllib.request.urlretrieve(url, filepath)
        
        download_file(YUNET_URL, self.yunet_path, "YuNet Face Detector")
        download_file(SFACE_URL, self.sface_path, "SFace Face Recognizer")

    def initialize(self, input_size=(320, 320)):
        """Initializes the face detector and face recognizer with the given input size."""
        FaceEngine._init_lock.acquire()
        try:
            self.ensure_models_downloaded()
            
            # 1. Initialize YuNet Face Detector on CPU (standard OpenCV DNN)
            # Positional arguments are used for compatibility with OpenCV Python bindings
            self.detector = cv2.FaceDetectorYN.create(
                self.yunet_path,
                "",
                input_size,
                0.85,
                0.3,
                10,
                cv2.dnn.DNN_BACKEND_OPENCV,
                cv2.dnn.DNN_TARGET_CPU
            )
            
            # 2. Initialize SFace Face Recognizer (OpenCV CPU baseline)
            self.recognizer = cv2.FaceRecognizerSF.create(
                self.sface_path,
                "",
                cv2.dnn.DNN_BACKEND_OPENCV,
                cv2.dnn.DNN_TARGET_CPU
            )
            
            # 3. Initialize SFace via ONNX Runtime GPU (CUDA) if available
            self.ort_session = None
            try:
                import onnxruntime as ort
                available_providers = ort.get_available_providers()
                providers = []
                if 'CUDAExecutionProvider' in available_providers:
                    providers.append('CUDAExecutionProvider')
                providers.append('CPUExecutionProvider')
                
                # Load SFace model session with GPU execution support
                self.ort_session = ort.InferenceSession(self.sface_path, providers=providers)
                print(f"FaceEngine initialized SFace with ONNX Runtime. Active Providers: {self.ort_session.get_providers()}")
            except Exception as e:
                print(f"Failed to initialize SFace with ONNX Runtime, falling back to OpenCV DNN CPU: {e}")
        finally:
            FaceEngine._init_lock.release()

    def set_input_size(self, width, height):
        """Updates the input size of the detector for new frame dimensions."""
        if self.detector:
            self.detector.setInputSize((width, height))

    def detect_faces(self, frame):
        """Detects faces in the frame and returns a list of faces."""
        if self.detector is None:
            raise RuntimeError("FaceEngine is not initialized.")
        
        retval, faces = self.detector.detect(frame)
        if retval and faces is not None:
            return faces
        return []

    def extract_embedding(self, frame, face):
        """Aligns the face and extracts its 128-dimensional embedding vector."""
        if self.recognizer is None:
            raise RuntimeError("FaceEngine is not initialized.")
        
        # Align and crop face using OpenCV C++ (extremely fast, ~0.1ms)
        aligned_face = self.recognizer.alignCrop(frame, face)
        
        # Extract features using ONNX Runtime GPU (CUDA) if initialized, otherwise fallback to CPU
        if self.ort_session is not None:
            try:
                # Preprocess aligned face: BGR to RGB (swapRB=True), transpose to NCHW [1, 3, 112, 112]
                rgb_face = cv2.cvtColor(aligned_face, cv2.COLOR_BGR2RGB)
                input_data = rgb_face.astype(np.float32)
                input_data = np.transpose(input_data, (2, 0, 1))
                input_data = np.expand_dims(input_data, axis=0)
                
                # Run GPU inference
                ort_outputs = self.ort_session.run(None, {'data': input_data})
                embedding = ort_outputs[0]
                return aligned_face, embedding
            except Exception as e:
                print(f"ONNX Runtime inference failed, falling back to OpenCV DNN CPU: {e}")
        
        # CPU Fallback
        embedding = self.recognizer.feature(aligned_face)
        return aligned_face, embedding

    @staticmethod
    def cosine_similarity(emb1, emb2):
        """Computes cosine similarity between two face embeddings."""
        e1 = emb1.flatten()
        e2 = emb2.flatten()
        dot_product = np.dot(e1, e2)
        norm_e1 = np.linalg.norm(e1)
        norm_e2 = np.linalg.norm(e2)
        if norm_e1 == 0 or norm_e2 == 0:
            return 0.0
        return float(dot_product / (norm_e1 * norm_e2))

    def cluster_faces(self, all_detected_faces, similarity_threshold=0.363, min_cluster_size=2):
        """Clusters face embeddings using simple distance-based clustering."""
        clusters = [] # list of lists of face dicts
        
        for face in all_detected_faces:
            emb = face['embedding']
            best_match_idx = -1
            best_score = -1.0
            
            for idx, cluster in enumerate(clusters):
                rep_emb = cluster[0]['embedding']
                score = self.cosine_similarity(emb, rep_emb)
                if score > best_score:
                    best_score = score
                    best_match_idx = idx
            
            if best_score >= similarity_threshold:
                clusters[best_match_idx].append(face)
            else:
                clusters.append([face])
        
        valid_clusters = []
        cluster_id = 0
        
        clusters.sort(key=len, reverse=True)
        for cluster in clusters:
            if len(cluster) >= min_cluster_size:
                best_face = max(cluster, key=lambda f: f['confidence'])
                
                valid_clusters.append({
                    'id': cluster_id,
                    'faces': cluster,
                    'representative_thumb': best_face['thumb_path']
                })
                cluster_id += 1
                
        return valid_clusters
