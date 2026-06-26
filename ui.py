import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon, QFont, QPalette, QColor
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFileDialog, QProgressBar, QScrollArea,
    QGridLayout, QFrame, QCheckBox, QDoubleSpinBox, QSpinBox,
    QGroupBox, QMessageBox, QSizePolicy, QListWidget, QComboBox
)

# Premium Dark QSS Stylesheet
DARK_STYLESHEET = """
QMainWindow {
    background-color: #12141A;
}

QWidget {
    color: #E2E8F0;
    font-family: 'Segoe UI', -apple-system, sans-serif;
    font-size: 13px;
}

QLabel {
    color: #CBD5E1;
}

QLabel#titleLabel {
    font-size: 20px;
    font-weight: bold;
    color: #00E5FF;
    margin-bottom: 5px;
}

QLabel#subtitleLabel {
    font-size: 12px;
    color: #64748B;
    margin-bottom: 15px;
}

QGroupBox {
    border: 1px solid #2A2F3D;
    border-radius: 8px;
    margin-top: 15px;
    font-weight: bold;
    color: #00E5FF;
    background-color: #1A1D26;
}

QGroupBox::title {
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 5px;
}

QLineEdit {
    background-color: #0B0C10;
    border: 1px solid #2A2F3D;
    border-radius: 6px;
    padding: 6px 10px;
    color: #FFFFFF;
    selection-background-color: #00D2C4;
}

QLineEdit:focus {
    border: 1px solid #00E5FF;
}

QPushButton {
    background-color: #2E3344;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
    color: #FFFFFF;
}

QPushButton:hover {
    background-color: #3E465C;
}

QPushButton:pressed {
    background-color: #242936;
}

QPushButton#btnPrimary {
    background-color: #00D2C4;
    color: #0B0C10;
}

QPushButton#btnPrimary:hover {
    background-color: #00F0E0;
}

QPushButton#btnPrimary:pressed {
    background-color: #00B2A6;
}

QPushButton#btnPrimary:disabled {
    background-color: #243E3B;
    color: #64748B;
}

QProgressBar {
    border: 1px solid #2A2F3D;
    border-radius: 6px;
    background-color: #0B0C10;
    text-align: center;
    color: #FFFFFF;
    font-weight: bold;
}

QProgressBar::chunk {
    background-color: #00D2C4;
    border-radius: 5px;
}

QScrollArea {
    border: 1px solid #2A2F3D;
    border-radius: 8px;
    background-color: #0E1015;
}

QScrollBar:vertical {
    border: none;
    background: #0B0C10;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #2E3344;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::handle:vertical:hover {
    background: #00D2C4;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    border: none;
    background: none;
}

QCheckBox {
    spacing: 5px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #2A2F3D;
    border-radius: 4px;
    background-color: #0B0C10;
}

QCheckBox::indicator:hover {
    border: 1px solid #00E5FF;
}

QCheckBox::indicator:checked {
    background-color: #00D2C4;
    border: 1px solid #00D2C4;
}

QDoubleSpinBox, QSpinBox {
    background-color: #0B0C10;
    border: 1px solid #2A2F3D;
    border-radius: 6px;
    padding: 4px;
    color: #FFFFFF;
}

QDoubleSpinBox:focus, QSpinBox:focus {
    border: 1px solid #00E5FF;
}

/* Face Card Styling */
QFrame#FaceCard {
    background-color: #1A1D26;
    border: 1px solid #2A2F3D;
    border-radius: 8px;
}

QFrame#FaceCard:hover {
    border: 1px solid #64748B;
    background-color: #202430;
}

QFrame#FaceCard[selected="true"] {
    border: 2px solid #00D2C4;
    background-color: #222B30;
}

QListWidget {
    background-color: #0B0C10;
    border: 1px solid #2A2F3D;
    border-radius: 6px;
    padding: 5px;
    color: #FFFFFF;
}

QListWidget::item {
    padding: 6px 10px;
    border-bottom: 1px solid #1A1D26;
}

QListWidget::item:selected {
    background-color: #2E3344;
    color: #00D2C4;
}

QComboBox {
    background-color: #0B0C10;
    border: 1px solid #2A2F3D;
    border-radius: 6px;
    padding: 6px 10px;
    color: #FFFFFF;
}

QComboBox QAbstractItemView {
    background-color: #1A1D26;
    border: 1px solid #2A2F3D;
    selection-background-color: #2E3344;
    selection-color: #00D2C4;
}
"""

class FaceCard(QFrame):
    clicked = Signal(int, bool)  # cluster_id, is_selected
    
    def __init__(self, cluster_id, thumb_path, face_count, parent=None):
        super().__init__(parent)
        self.cluster_id = cluster_id
        self.is_selected = False
        self.setObjectName("FaceCard")
        self.setFrameShape(QFrame.StyledPanel)
        
        # Set dynamic property for QSS styling
        self.setProperty("selected", "false")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignCenter)
        
        # 1. Face Thumbnail
        self.img_label = QLabel(self)
        self.img_label.setFixedSize(110, 110)
        self.img_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        
        pixmap = QPixmap(thumb_path)
        if pixmap.isNull():
            self.img_label.setText("No Image")
            self.img_label.setStyleSheet("color: #64748B; border: 1px dashed #2A2F3D; border-radius: 6px;")
        else:
            self.img_label.setPixmap(pixmap.scaled(
                110, 110, 
                Qt.KeepAspectRatioByExpanding, 
                Qt.SmoothTransformation
            ))
            # Clip label to give rounded corners to image
            self.img_label.setStyleSheet("border-radius: 6px; border: 1px solid #2A2F3D;")
            
        self.img_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.img_label)
        
        # 2. Checkbox for selection
        self.checkbox = QCheckBox(f"Người {cluster_id + 1}\n({face_count} lần)", self)
        self.checkbox.setAttribute(Qt.WA_TransparentForMouseEvents)  # Forward clicks to card
        self.checkbox.setStyleSheet("font-weight: bold; color: #E2E8F0;")
        layout.addWidget(self.checkbox)
        
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedWidth(136)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.toggle_selection()
            
    def toggle_selection(self):
        self.is_selected = not self.is_selected
        self.checkbox.setChecked(self.is_selected)
        
        # Update styling
        self.setProperty("selected", "true" if self.is_selected else "false")
        self.style().unpolish(self)
        self.style().polish(self)
        
        self.clicked.emit(self.cluster_id, self.is_selected)

class TrimmerAppUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Talkshow Person Video Trimmer - Antigravity")
        self.resize(1100, 720)
        self.setStyleSheet(DARK_STYLESHEET)
        
        # Main Layout container
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        
        # --- HEADER ---
        header_layout = QVBoxLayout()
        header_layout.setSpacing(2)
        title_label = QLabel("Talkshow Person Video Trimmer", self)
        title_label.setObjectName("titleLabel")
        header_layout.addWidget(title_label)
        
        subtitle_label = QLabel("Tự động phân tích video, gom nhóm khuôn mặt và tách các đoạn chỉ có người bạn chọn.", self)
        subtitle_label.setObjectName("subtitleLabel")
        header_layout.addWidget(subtitle_label)
        main_layout.addLayout(header_layout)
        
        # --- SIDE-BY-SIDE PANELS ---
        split_layout = QHBoxLayout()
        split_layout.setSpacing(20)
        
        # Left Panel (Inputs & Settings)
        left_panel = QWidget(self)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(15)
        
        # Right Panel (Gallery & Export)
        right_panel = QWidget(self)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(15)
        
        # --- VIDEO SELECTION GROUP (Left Panel) ---
        video_group = QGroupBox("1. Danh Sách Video Đầu Vào (Hỗ trợ kéo thả nhiều file)", self)
        video_layout = QVBoxLayout(video_group)
        video_layout.setContentsMargins(15, 20, 15, 15)
        video_layout.setSpacing(10)
        
        self.video_list = QListWidget(self)
        self.video_list.setFixedHeight(120)
        video_layout.addWidget(self.video_list)
        
        button_layout = QHBoxLayout()
        self.btn_add_video = QPushButton("Thêm Video...", self)
        self.btn_add_video.setObjectName("btnPrimary")
        button_layout.addWidget(self.btn_add_video)
        
        self.btn_remove_video = QPushButton("Xóa Video", self)
        button_layout.addWidget(self.btn_remove_video)
        video_layout.addLayout(button_layout)
        
        left_layout.addWidget(video_group)
        
        # --- SETTINGS GROUP (Left Panel) ---
        settings_group = QGroupBox("2. Cài Đặt Phân Tích (Tùy Chọn)", self)
        settings_layout = QGridLayout(settings_group)
        settings_layout.setContentsMargins(15, 20, 15, 15)
        settings_layout.setSpacing(10)
        
        # Row 0 Col 0-1: Sampling rate
        settings_layout.addWidget(QLabel("Giãn cách quét (giây):", self), 0, 0)
        self.spin_interval = QDoubleSpinBox(self)
        self.spin_interval.setRange(0.1, 10.0)
        self.spin_interval.setValue(1.0)
        self.spin_interval.setSingleStep(0.5)
        self.spin_interval.setSuffix(" s")
        settings_layout.addWidget(self.spin_interval, 0, 1)
        
        # Row 0 Col 2-3: Min cluster size
        settings_layout.addWidget(QLabel("Số lần xuất hiện tối thiểu:", self), 0, 2)
        self.spin_min_cluster = QSpinBox(self)
        self.spin_min_cluster.setRange(1, 100)
        self.spin_min_cluster.setValue(3)
        self.spin_min_cluster.setSuffix(" lần")
        settings_layout.addWidget(self.spin_min_cluster, 0, 3)
        
        # Row 1 Col 0-1: Checkbox to scan every frame
        self.chk_all_frames = QCheckBox("Quét từng frame (Rất chậm, chính xác nhất)", self)
        self.chk_all_frames.setChecked(False)
        settings_layout.addWidget(self.chk_all_frames, 1, 0, 1, 2)
        
        # Row 1 Col 2-3: Similarity threshold
        settings_layout.addWidget(QLabel("Độ khớp khuôn mặt:", self), 1, 2)
        self.spin_threshold = QDoubleSpinBox(self)
        self.spin_threshold.setRange(0.10, 0.90)
        self.spin_threshold.setValue(0.36)  # Default SFace threshold
        self.spin_threshold.setSingleStep(0.02)
        settings_layout.addWidget(self.spin_threshold, 1, 3)
        
        # Row 2 Col 0-3: Scan action buttons (Start / Stop)
        scan_btn_layout = QHBoxLayout()
        self.btn_scan = QPushButton("Bắt Đầu Phân Tích", self)
        self.btn_scan.setObjectName("btnPrimary")
        self.btn_scan.setEnabled(False)
        scan_btn_layout.addWidget(self.btn_scan, 2)  # stretch = 2
        
        self.btn_stop = QPushButton("Dừng Phân Tích", self)
        self.btn_stop.setEnabled(False)
        scan_btn_layout.addWidget(self.btn_stop, 1)  # stretch = 1
        
        settings_layout.addLayout(scan_btn_layout, 2, 0, 1, 4)
        
        left_layout.addWidget(settings_group)
        
        # --- PROGRESS BAR AND STATUS (Left Panel) ---
        self.progress_layout = QVBoxLayout()
        
        status_header_layout = QHBoxLayout()
        self.progress_label = QLabel("Trạng thái: Sẵn sàng", self)
        self.progress_label.setFixedHeight(20)
        self.progress_label.setWordWrap(False)
        self.progress_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        status_header_layout.addWidget(self.progress_label, 1)  # stretch = 1
        
        # CUDA Acceleration Status Label
        self.cuda_status_label = QLabel("CUDA: Kiểm tra...", self)
        self.cuda_status_label.setStyleSheet("font-weight: bold; color: #64748B;")
        self.cuda_status_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.cuda_status_label.setFixedHeight(20)
        self.cuda_status_label.setWordWrap(False)
        status_header_layout.addWidget(self.cuda_status_label, 0)  # stretch = 0
        
        self.progress_layout.addLayout(status_header_layout)
        
        self.progress_bar = QProgressBar(self)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_layout.addWidget(self.progress_bar)
        left_layout.addLayout(self.progress_layout)
        
        # Add a stretch spacer to keep left layout items snug at the top
        left_layout.addStretch()
        
        # --- FACES GALLERY GROUP (Right Panel) ---
        self.gallery_group = QGroupBox("3. Chọn Người Muốn Tách (Sau khi quét)", self)
        gallery_layout = QVBoxLayout(self.gallery_group)
        gallery_layout.setContentsMargins(15, 20, 15, 15)
        
        # Scroll Area for Grid
        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_widget = QWidget()
        self.grid_layout = QGridLayout(self.scroll_widget)
        self.grid_layout.setSpacing(10)
        self.grid_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.scroll_area.setWidget(self.scroll_widget)
        gallery_layout.addWidget(self.scroll_area)
        
        right_layout.addWidget(self.gallery_group, 1) # Faces gallery gets the vertical expansion
        
        # --- EXPORT GROUP (Right Panel) ---
        export_group = QGroupBox("4. Xuất Video Kết Quả", self)
        export_layout = QVBoxLayout(export_group)
        export_layout.setContentsMargins(15, 20, 15, 15)
        export_layout.setSpacing(10)
        
        # Row 1: Export Mode Selection
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("Chế độ xuất:", self))
        self.combo_export_mode = QComboBox(self)
        self.combo_export_mode.addItems([
            "Xuất riêng rẽ (Cắt riêng từng video gốc)",
            "Xuất gộp (Ghép tất cả đoạn của người này thành 1 file)"
        ])
        mode_layout.addWidget(self.combo_export_mode)
        export_layout.addLayout(mode_layout)
        
        # Row 2: Combined Output File Selection (visible only in combined mode)
        self.out_file_widget = QWidget(self)
        out_file_layout = QHBoxLayout(self.out_file_widget)
        out_file_layout.setContentsMargins(0, 0, 0, 0)
        self.out_path_edit = QLineEdit(self)
        self.out_path_edit.setPlaceholderText("Đường dẫn lưu file video kết quả gộp...")
        self.out_path_edit.setReadOnly(True)
        out_file_layout.addWidget(self.out_path_edit)
        
        self.btn_out_browse = QPushButton("Duyệt Nơi Lưu...", self)
        out_file_layout.addWidget(self.btn_out_browse)
        export_layout.addWidget(self.out_file_widget)
        
        export_options_layout = QHBoxLayout()
        self.chk_reencode = QCheckBox("Re-encode video (Cắt chính xác)", self)
        self.chk_reencode.setChecked(True)
        export_options_layout.addWidget(self.chk_reencode)
        
        self.btn_export = QPushButton("Xuất Video", self)
        self.btn_export.setObjectName("btnPrimary")
        self.btn_export.setEnabled(False)
        export_options_layout.addWidget(self.btn_export)
        export_layout.addLayout(export_options_layout)
        
        right_layout.addWidget(export_group)
        
        # Assemble Left and Right Panels
        split_layout.addWidget(left_panel, 1)
        split_layout.addWidget(right_panel, 1)
        
        main_layout.addLayout(split_layout)

