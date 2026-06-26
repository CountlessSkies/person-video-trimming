import sys
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox, QLabel, QListWidgetItem
from ui import TrimmerAppUI, FaceCard
from worker import ScanWorker, ExportWorker
from video_utils import detections_to_segments

class TrimmerApp(TrimmerAppUI):
    def __init__(self):
        super().__init__()
        
        # Enable Drag and Drop
        self.setAcceptDrops(True)
        
        # Application State
        self.video_paths = []
        self.output_video_path = ""
        self.clusters = []
        self.selected_clusters = set()
        self.scanned_interval = 1.0
        
        # Scan Queue & Worker tracking state
        self.scan_queue = []
        self.active_workers = {}
        self.all_workers = []
        self.scan_results = {}
        self.scan_intervals = {}
        self.scan_progresses = {}
        
        self.export_worker = None
        
        # Connect UI Signals to Handlers
        self.btn_add_video.clicked.connect(self.on_add_video)
        self.btn_remove_video.clicked.connect(self.on_remove_video)
        self.btn_out_browse.clicked.connect(self.on_browse_output)
        self.btn_scan.clicked.connect(self.on_start_scan)
        self.btn_stop.clicked.connect(self.on_stop_scan)
        self.btn_export.clicked.connect(self.on_start_export)
        self.chk_all_frames.toggled.connect(self.spin_interval.setDisabled)
        self.combo_export_mode.currentIndexChanged.connect(self.on_export_mode_changed)
        
        # Initialize export mode layout state
        self.on_export_mode_changed(self.combo_export_mode.currentIndex())
        
        # Check CUDA acceleration availability on startup
        self.check_cuda_status()
        
    def check_cuda_status(self):
        sface_path = os.path.join("models", "face_recognition_sface_2021dec.onnx")
        try:
            import onnxruntime as ort
            available = ort.get_available_providers()
            if 'CUDAExecutionProvider' in available:
                if os.path.exists(sface_path):
                    # Verify CUDA session can be successfully created
                    _ = ort.InferenceSession(sface_path, providers=['CUDAExecutionProvider'])
                self.cuda_status_label.setText("CUDA: Hoạt động (RTX 3060) ✓")
                self.cuda_status_label.setStyleSheet("font-weight: bold; color: #00D2C4;") # Cyan
            else:
                self.cuda_status_label.setText("CUDA: Không hoạt động (CPU) ✗")
                self.cuda_status_label.setStyleSheet("font-weight: bold; color: #E11D48;") # Pinkish Red
        except Exception:
            self.cuda_status_label.setText("CUDA: Không hoạt động (CPU) ✗")
            self.cuda_status_label.setStyleSheet("font-weight: bold; color: #E11D48;")
            
    def get_short_name(self, path):
        name = os.path.basename(path)
        if len(name) > 30:
            return name[:15] + "..." + name[-12:]
        return name
        
    def dragEnterEvent(self, event):
        # Only accept drops if not scanning
        if not self.active_workers and event.mimeData().hasUrls():
            for url in event.mimeData().urls():
                file_path = url.toLocalFile()
                _, ext = os.path.splitext(file_path.lower())
                if ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                    event.acceptProposedAction()
                    return
        event.ignore()
        
    def dropEvent(self, event):
        urls = event.mimeData().urls()
        file_paths = []
        for url in urls:
            file_path = url.toLocalFile()
            _, ext = os.path.splitext(file_path.lower())
            if ext in ['.mp4', '.avi', '.mov', '.mkv', '.webm']:
                file_paths.append(os.path.abspath(file_path))
        if file_paths:
            self.add_videos(file_paths)
            
    def add_videos(self, paths):
        for path in paths:
            if path not in self.video_paths:
                self.video_paths.append(path)
                item = QListWidgetItem(self.get_short_name(path))
                item.setData(Qt.UserRole, path)
                self.video_list.addItem(item)
                
        # Update output suggestion
        if self.video_paths and not self.output_video_path:
            dir_name = os.path.dirname(self.video_paths[0])
            self.output_video_path = os.path.join(dir_name, "combined_trimmed.mp4")
            self.out_path_edit.setText(self.output_video_path)
            
        self.update_ui_state()
        self.progress_bar.setValue(0)
        self.progress_label.setText(f"Đã thêm {len(paths)} video. Sẵn sàng quét.")
        
    def on_add_video(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn Các Video Đầu Vào",
            "",
            "Video Files (*.mp4 *.avi *.mov *.mkv *.webm);;All Files (*)"
        )
        if file_paths:
            self.add_videos(file_paths)
            
    def on_remove_video(self):
        selected_items = self.video_list.selectedItems()
        if not selected_items:
            return
        for item in selected_items:
            path = item.data(Qt.UserRole)
            if path in self.video_paths:
                self.video_paths.remove(path)
            self.video_list.takeItem(self.video_list.row(item))
            
        if not self.video_paths:
            self.output_video_path = ""
            self.out_path_edit.clear()
            self.btn_export.setEnabled(False)
            self.clear_gallery()
            self.progress_bar.setValue(0)
            self.progress_label.setText("Trạng thái: Sẵn sàng")
            
        self.update_ui_state()
        
    def update_ui_state(self):
        has_videos = len(self.video_paths) > 0
        self.btn_scan.setEnabled(has_videos)
        self.btn_remove_video.setEnabled(has_videos)
        
    def on_export_mode_changed(self, index):
        if index == 0:
            self.out_file_widget.hide()
        else:
            self.out_file_widget.show()
            
    def on_browse_output(self):
        if not self.video_paths:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng thêm video đầu vào trước.")
            return
            
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Chọn Nơi Lưu Video Kết Quả Gộp",
            self.output_video_path,
            "Video Files (*.mp4 *.avi *.mov *.mkv *.webm);;All Files (*)"
        )
        if file_path:
            self.output_video_path = os.path.abspath(file_path)
            self.out_path_edit.setText(self.output_video_path)
            
    def on_start_scan(self):
        if not self.video_paths:
            return
            
        # Get parameters from UI
        if self.chk_all_frames.isChecked():
            sample_interval = 0.0
        else:
            sample_interval = self.spin_interval.value()
            
        self.scan_similarity_threshold = self.spin_threshold.value()
        self.scan_min_cluster_size = self.spin_min_cluster.value()
        self.scan_sample_interval = sample_interval
        
        # Lock UI controls during scan
        self.set_ui_locked(True)
        self.clear_gallery()
        
        # Reset scan results and progresses
        self.scan_results.clear()
        self.scan_intervals.clear()
        self.scan_progresses.clear()
        self.active_workers.clear()
        self.all_workers.clear()
        self.scan_queue = self.video_paths.copy()
        
        # Set all list items to "Chờ quét..."
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            short_name = self.get_short_name(item.data(Qt.UserRole))
            item.setText(f"{short_name} - [Đang chờ...]")
            
        # Start queue processing
        self.process_scan_queue()
        
    def process_scan_queue(self):
        # Limit concurrency to 2
        while len(self.active_workers) < 2 and self.scan_queue:
            path = self.scan_queue.pop(0)
            
            worker = ScanWorker(
                video_path=path,
                sample_interval=self.scan_sample_interval,
                similarity_threshold=self.scan_similarity_threshold,
                min_cluster_size=self.scan_min_cluster_size
            )
            worker.progress.connect(lambda msg, p, pth=path: self.on_worker_progress(pth, msg, p))
            worker.finished.connect(self.on_worker_finished)
            worker.error.connect(lambda err, pth=path: self.on_worker_error(pth, err))
            
            self.active_workers[path] = worker
            self.all_workers.append(worker)
            self.scan_progresses[path] = 0
            worker.start()
            
        # If all queue is empty and no workers are running, complete scanning
        if not self.active_workers and not self.scan_queue:
            self.on_all_scans_finished()
            
    def on_worker_progress(self, path, msg, progress):
        self.scan_progresses[path] = progress
        short_name = self.get_short_name(path)
        
        # Update list item text
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.data(Qt.UserRole) == path:
                item.setText(f"{short_name} - [{progress}%]")
                break
                
        # Update overall progress bar
        total_p = sum(self.scan_progresses.get(p, 0) for p in self.video_paths) / len(self.video_paths)
        self.progress_bar.setValue(min(90, int(total_p)))
        self.progress_label.setText(f"Đang quét {short_name}: {msg}")
        
    def on_worker_finished(self, path, faces, val):
        self.scan_results[path] = faces
        self.scan_intervals[path] = val
        self.scan_progresses[path] = 100
        short_name = self.get_short_name(path)
        
        # Update list item text
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.data(Qt.UserRole) == path:
                item.setText(f"{short_name} - [Đã xong ✓]")
                break
                
        self.active_workers.pop(path, None)
        self.process_scan_queue()
        
    def on_worker_error(self, path, err_msg):
        # Stop all running workers safely
        for p, worker in list(self.active_workers.items()):
            worker.stop()
            worker.wait()
        self.active_workers.clear()
        self.scan_queue.clear()
        
        self.set_ui_locked(False)
        short_name = self.get_short_name(path)
        self.progress_label.setText(f"Lỗi khi quét: {short_name}")
        self.progress_bar.setValue(0)
        
        # Update failed file status
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.data(Qt.UserRole) == path:
                item.setText(f"{short_name} - [Lỗi ✗]")
                
        QMessageBox.critical(self, "Lỗi phân tích", f"Đã xảy ra lỗi khi quét {short_name}:\n{err_msg}")
        
    def on_stop_scan(self):
        # Stop all running workers safely
        for p, worker in list(self.active_workers.items()):
            worker.stop()
            worker.wait()
        self.active_workers.clear()
        self.scan_queue.clear()
        
        self.set_ui_locked(False)
        self.progress_label.setText("Trạng thái: Đã dừng phân tích.")
        self.progress_bar.setValue(0)
        
        # Reset all QListWidget items to normal short name text
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            item.setText(self.get_short_name(item.data(Qt.UserRole)))
            
        QMessageBox.information(self, "Thông báo", "Đã dừng quá trình phân tích video.")
        
    def on_all_scans_finished(self):
        self.progress_label.setText("Trạng thái: Gom nhóm khuôn mặt toàn cục...")
        self.progress_bar.setValue(95)
        
        # Aggregate all detected faces from all files
        global_faces = []
        for path, faces in self.scan_results.items():
            global_faces.extend(faces)
            
        if not global_faces:
            self.set_ui_locked(False)
            self.progress_bar.setValue(100)
            self.progress_label.setText("Hoàn thành! Không tìm thấy khuôn mặt nào.")
            self.populate_gallery([])
            return
            
        # Run global clustering
        from face_engine import FaceEngine
        engine = FaceEngine()
        self.clusters = engine.cluster_faces(
            global_faces,
            similarity_threshold=self.scan_similarity_threshold,
            min_cluster_size=self.scan_min_cluster_size
        )
        
        # Determine scanned interval
        if self.scan_intervals:
            self.scanned_interval = next(iter(self.scan_intervals.values()))
        else:
            self.scanned_interval = 1.0
            
        self.set_ui_locked(False)
        self.selected_clusters.clear()
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"Hoàn thành quét! Tìm thấy {len(self.clusters)} người xuất hiện.")
        
        self.populate_gallery(self.clusters)
        
    def on_card_clicked(self, cluster_id, is_selected):
        if is_selected:
            self.selected_clusters.add(cluster_id)
        else:
            self.selected_clusters.discard(cluster_id)
            
        # Enable export button if at least one cluster is selected
        self.btn_export.setEnabled(len(self.selected_clusters) > 0)
        
    def on_start_export(self):
        if not self.video_paths:
            return
        if not self.selected_clusters:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn ít nhất một người cần tách.")
            return
            
        is_combined = self.combo_export_mode.currentIndex() == 1
        if is_combined and not self.output_video_path:
            QMessageBox.warning(self, "Cảnh báo", "Vui lòng chọn nơi lưu video kết quả gộp.")
            return
            
        # Map video_path -> second -> set of cluster IDs detected at that timestamp
        video_sec_to_clusters = {p: {} for p in self.video_paths}
        
        for cluster in self.clusters:
            c_id = cluster['id']
            for face in cluster['faces']:
                vid = face['video_path']
                sec = face['sec']
                if vid not in video_sec_to_clusters:
                    video_sec_to_clusters[vid] = {}
                if sec not in video_sec_to_clusters[vid]:
                    video_sec_to_clusters[vid][sec] = set()
                video_sec_to_clusters[vid][sec].add(c_id)
                
        # Filter seconds per video containing ONLY selected clusters
        video_to_matching_secs = {p: [] for p in self.video_paths}
        video_to_rejected_secs = {p: [] for p in self.video_paths}
        
        for vid, sec_dict in video_sec_to_clusters.items():
            for sec, cluster_ids in sec_dict.items():
                if cluster_ids.issubset(self.selected_clusters) and len(cluster_ids) > 0:
                    video_to_matching_secs[vid].append(sec)
                else:
                    video_to_rejected_secs[vid].append(sec)
                    
        # Convert seconds to segments per video
        video_to_segments = {}
        for vid in self.video_paths:
            matching_secs = video_to_matching_secs[vid]
            rejected_secs = video_to_rejected_secs[vid]
            if not matching_secs:
                continue
                
            sample_interval = self.scan_intervals.get(vid, self.scanned_interval)
            segments = detections_to_segments(
                matching_secs,
                sampling_interval=sample_interval,
                max_gap=sample_interval + 0.5,
                min_duration=1.0,
                rejected_seconds=rejected_secs
            )
            if segments:
                video_to_segments[vid] = segments
                
        if not video_to_segments:
            QMessageBox.warning(
                self, 
                "Cảnh báo", 
                "Không có phân đoạn nào thỏa mãn điều kiện chỉ có người bạn chọn xuất hiện."
            )
            return
            
        # Lock UI during export
        self.set_ui_locked(True)
        self.btn_export.setEnabled(False)
        
        reencode = self.chk_reencode.isChecked()
        output_dest = self.output_video_path if is_combined else None
        
        self.export_worker = ExportWorker(
            inputs_and_segments=video_to_segments,
            output_video=output_dest,
            reencode=reencode
        )
        self.export_worker.progress.connect(self.update_progress)
        self.export_worker.finished.connect(self.on_export_finished)
        self.export_worker.error.connect(self.on_export_error)
        self.export_worker.start()
        
    def on_export_finished(self, out_path):
        self.set_ui_locked(False)
        self.btn_export.setEnabled(True)
        self.progress_bar.setValue(100)
        self.progress_label.setText("Trạng thái: Hoàn thành xuất video!")
        
        if out_path == "separate":
            QMessageBox.information(
                self, 
                "Xuất Video Thành Công", 
                "Các video riêng rẽ đã được cắt và lưu thành công!"
            )
        else:
            QMessageBox.information(
                self, 
                "Xuất Video Thành Công", 
                f"Video đã được gộp và lưu tại:\n{out_path}"
            )
            
    def on_export_error(self, err_msg):
        self.set_ui_locked(False)
        self.btn_export.setEnabled(True)
        self.progress_label.setText("Trạng thái: Lỗi khi xuất video.")
        self.progress_bar.setValue(0)
        QMessageBox.critical(self, "Lỗi xuất video", f"Đã xảy ra lỗi:\n{err_msg}")
        
    def update_progress(self, status_msg, progress_percent):
        self.progress_label.setText(f"Trạng thái: {status_msg}")
        self.progress_bar.setValue(progress_percent)
        
    def set_ui_locked(self, locked):
        self.btn_add_video.setDisabled(locked)
        self.btn_remove_video.setDisabled(locked)
        self.btn_out_browse.setDisabled(locked)
        self.btn_scan.setDisabled(locked)
        self.btn_stop.setEnabled(locked)
        self.chk_all_frames.setDisabled(locked)
        if locked:
            self.spin_interval.setDisabled(True)
        else:
            self.spin_interval.setDisabled(self.chk_all_frames.isChecked())
        self.spin_threshold.setDisabled(locked)
        self.spin_min_cluster.setDisabled(locked)
        self.chk_reencode.setDisabled(locked)
        
        for i in range(self.grid_layout.count()):
            item = self.grid_layout.itemAt(i)
            if item:
                widget = item.widget()
                if isinstance(widget, FaceCard):
                    widget.setDisabled(locked)
                    
    def clear_gallery(self):
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
                
    def populate_gallery(self, clusters):
        self.clear_gallery()
        
        if not clusters:
            no_face_label = QLabel("Không tìm thấy khuôn mặt nào đạt điều kiện.", self.scroll_widget)
            no_face_label.setStyleSheet("color: #64748B; font-style: italic; font-size: 14px;")
            self.grid_layout.addWidget(no_face_label, 0, 0)
            return
            
        cols = 3  # 3 columns fit side-by-side panel layout perfectly
        for idx, cluster in enumerate(clusters):
            row = idx // cols
            col = idx % cols
            
            card = FaceCard(
                cluster_id=cluster['id'],
                thumb_path=cluster['representative_thumb'],
                face_count=len(cluster['faces']),
                parent=self.scroll_widget
            )
            card.clicked.connect(self.on_card_clicked)
            self.grid_layout.addWidget(card, row, col)
            
    def closeEvent(self, event):
        # Stop background workers safely before exiting
        for p, worker in list(self.active_workers.items()):
            worker.stop()
            worker.wait()
        self.active_workers.clear()
        
        if self.export_worker and self.export_worker.isRunning():
            self.export_worker.terminate()
            self.export_worker.wait()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_DontCreateNativeWidgetSiblings)
    
    window = TrimmerApp()
    window.show()
    sys.exit(app.exec())
