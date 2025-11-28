import ffmpeg
import os
import sys
import tempfile
import cv2
import numpy as np
from datetime import datetime
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QPushButton, QLineEdit, 
                             QSlider, QMessageBox, QProgressBar, QComboBox,
                             QGroupBox, QGridLayout)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer
from PyQt6.QtGui import QPixmap, QFont, QImage

class CameraWorker(QThread):
    frame_ready = pyqtSignal(np.ndarray)
    error = pyqtSignal(str)
    
    def __init__(self, camera_index=0):
        super().__init__()
        self.camera_index = camera_index
        self.running = False
        self.cap = None
        
    def run(self):
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                self.error.emit(f"Could not open camera {self.camera_index}")
                return
                
            self.running = True
            while self.running:
                ret, frame = self.cap.read()
                if ret:
                    self.frame_ready.emit(frame)
                else:
                    self.error.emit("Failed to read frame from camera")
                    break
                    
        except Exception as e:
            self.error.emit(f"Camera error: {str(e)}")
        finally:
            if self.cap:
                self.cap.release()
    
    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()

class RecordingWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)
    
    def __init__(self, frames, fps, width, output_file):
        super().__init__()
        self.frames = frames
        self.fps = fps
        self.width = width
        self.output_file = output_file
        
    def run(self):
        try:
            self.progress.emit("Converting frames to GIF...")
            
            # Create temporary video file
            temp_video = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            temp_video_path = temp_video.name
            temp_video.close()
            
            # Calculate height maintaining aspect ratio
            if self.frames:
                original_height, original_width = self.frames[0].shape[:2]
                height = int((self.width * original_height) / original_width)
            else:
                height = int(self.width * 0.75)  # Default aspect ratio
            
            # Create video writer
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            out = cv2.VideoWriter(temp_video_path, fourcc, self.fps, (self.width, height))
            
            # Write frames to video
            for i, frame in enumerate(self.frames):
                # Resize frame
                resized_frame = cv2.resize(frame, (self.width, height))
                out.write(resized_frame)
                
                if i % 5 == 0:  # Update progress every 5 frames
                    progress = (i / len(self.frames)) * 50  # First 50% for video creation
                    self.progress.emit(f"Processing frame {i + 1}/{len(self.frames)} ({progress:.0f}%)")
            
            out.release()
            
            # Convert video to GIF using FFmpeg
            self.progress.emit("Converting video to GIF...")
            (
                ffmpeg
                .input(temp_video_path)
                .filter('fps', fps=self.fps, round='up')
                .filter('scale', self.width, -1, flags='lanczos')
                .output(self.output_file, loop=0)
                .run(overwrite_output=True, quiet=True)
            )
            
            # Clean up temporary video
            try:
                os.unlink(temp_video_path)
            except:
                pass
                
            self.finished.emit(self.output_file)
            
        except Exception as e:
            self.error.emit(str(e))

class LiveGifMakerWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.camera_worker = None
        self.recording_worker = None
        self.recorded_frames = []
        self.is_recording = False
        self.fps = 8
        self.width = 320
        self.output_filename = "live_recording"
        self.max_frames = 150  # Limit recording length (about 10 seconds at 15 fps)
        
        self.init_ui()
        self.init_camera()
        
    def init_ui(self):
        self.setWindowTitle("Live GIF Recorder")
        self.setGeometry(100, 100, 900, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("Live GIF Recorder")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)
        
        # Camera selection group
        camera_group = QGroupBox("Camera Settings")
        camera_layout = QGridLayout(camera_group)
        
        camera_layout.addWidget(QLabel("Camera:"), 0, 0)
        self.camera_combo = QComboBox()
        self.populate_cameras()
        self.camera_combo.currentIndexChanged.connect(self.change_camera)
        camera_layout.addWidget(self.camera_combo, 0, 1)
        
        layout.addWidget(camera_group)
        
        # Live preview group
        preview_group = QGroupBox("Live Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        self.camera_label = QLabel("Starting camera...")
        self.camera_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.camera_label.setMinimumHeight(400)
        self.camera_label.setStyleSheet("QLabel { border: 2px solid gray; background-color: #000000; color: white; }")
        preview_layout.addWidget(self.camera_label)
        
        # Recording controls
        recording_layout = QHBoxLayout()
        
        self.record_btn = QPushButton("Start Recording")
        self.record_btn.clicked.connect(self.toggle_recording)
        self.record_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }")
        
        self.frames_label = QLabel("Frames: 0")
        
        recording_layout.addWidget(self.record_btn)
        recording_layout.addStretch()
        recording_layout.addWidget(self.frames_label)
        
        preview_layout.addLayout(recording_layout)
        layout.addWidget(preview_group)
        
        # Settings group
        settings_group = QGroupBox("GIF Settings")
        settings_layout = QGridLayout(settings_group)
        
        # Output filename
        settings_layout.addWidget(QLabel("Output Filename:"), 0, 0)
        self.filename_input = QLineEdit(self.output_filename)
        self.filename_input.textChanged.connect(self.update_filename)
        settings_layout.addWidget(self.filename_input, 0, 1)
        settings_layout.addWidget(QLabel(".gif"), 0, 2)
        
        # FPS setting
        settings_layout.addWidget(QLabel("Frame Rate (FPS):"), 1, 0)
        self.fps_slider = QSlider(Qt.Orientation.Horizontal)
        self.fps_slider.setMinimum(1)
        self.fps_slider.setMaximum(30)
        self.fps_slider.setValue(self.fps)
        self.fps_slider.valueChanged.connect(self.update_fps)
        self.fps_label = QLabel(str(self.fps))
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(self.fps_slider)
        fps_layout.addWidget(self.fps_label)
        fps_widget = QWidget()
        fps_widget.setLayout(fps_layout)
        settings_layout.addWidget(fps_widget, 1, 1, 1, 2)
        
        # Width setting
        settings_layout.addWidget(QLabel("Width (pixels):"), 2, 0)
        self.width_slider = QSlider(Qt.Orientation.Horizontal)
        self.width_slider.setMinimum(100)
        self.width_slider.setMaximum(800)
        self.width_slider.setValue(self.width)
        self.width_slider.valueChanged.connect(self.update_width)
        self.width_label = QLabel(str(self.width))
        width_layout = QHBoxLayout()
        width_layout.addWidget(self.width_slider)
        width_layout.addWidget(self.width_label)
        width_widget = QWidget()
        width_widget.setLayout(width_layout)
        settings_layout.addWidget(width_widget, 2, 1, 1, 2)
        
        # Max recording length
        settings_layout.addWidget(QLabel("Max Frames:"), 3, 0)
        self.max_frames_slider = QSlider(Qt.Orientation.Horizontal)
        self.max_frames_slider.setMinimum(30)
        self.max_frames_slider.setMaximum(300)
        self.max_frames_slider.setValue(self.max_frames)
        self.max_frames_slider.valueChanged.connect(self.update_max_frames)
        self.max_frames_label = QLabel(str(self.max_frames))
        max_frames_layout = QHBoxLayout()
        max_frames_layout.addWidget(self.max_frames_slider)
        max_frames_layout.addWidget(self.max_frames_label)
        max_frames_widget = QWidget()
        max_frames_widget.setLayout(max_frames_layout)
        settings_layout.addWidget(max_frames_widget, 3, 1, 1, 2)
        
        layout.addWidget(settings_group)
        
        # Create GIF button
        button_layout = QHBoxLayout()
        self.create_gif_btn = QPushButton("Create GIF from Recording")
        self.create_gif_btn.clicked.connect(self.create_gif)
        self.create_gif_btn.setEnabled(False)
        self.create_gif_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 10px; }")
        
        button_layout.addStretch()
        button_layout.addWidget(self.create_gif_btn)
        button_layout.addStretch()
        
        layout.addLayout(button_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready to record")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("QLabel { padding: 10px; background-color: #e8f4f8; border-radius: 5px; }")
        layout.addWidget(self.status_label)

    def populate_cameras(self):
        # Try to find available cameras
        self.camera_combo.clear()
        for i in range(5):  # Check first 5 camera indices
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                self.camera_combo.addItem(f"Camera {i}", i)
                cap.release()
        
        if self.camera_combo.count() == 0:
            self.camera_combo.addItem("No cameras found", -1)

    def init_camera(self):
        if self.camera_combo.count() > 0:
            camera_index = self.camera_combo.currentData()
            if camera_index >= 0:
                self.start_camera(camera_index)
    
    def start_camera(self, camera_index):
        if self.camera_worker:
            self.camera_worker.stop()
            self.camera_worker.wait()
        
        self.camera_worker = CameraWorker(camera_index)
        self.camera_worker.frame_ready.connect(self.update_camera_display)
        self.camera_worker.error.connect(self.on_camera_error)
        self.camera_worker.start()
    
    def change_camera(self, index):
        camera_index = self.camera_combo.currentData()
        if camera_index >= 0:
            self.start_camera(camera_index)
    
    def update_camera_display(self, frame):
        # Convert frame to QImage and display
        rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        
        # Scale image to fit display
        pixmap = QPixmap.fromImage(qt_image)
        scaled_pixmap = pixmap.scaled(
            self.camera_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.camera_label.setPixmap(scaled_pixmap)
        
        # Store frame if recording
        if self.is_recording:
            self.recorded_frames.append(frame.copy())
            self.frames_label.setText(f"Frames: {len(self.recorded_frames)}")
            
            # Stop recording if max frames reached
            if len(self.recorded_frames) >= self.max_frames:
                self.toggle_recording()
                QMessageBox.information(self, "Recording Complete", f"Maximum frame limit reached ({self.max_frames} frames)")
    
    def on_camera_error(self, error_message):
        self.camera_label.setText(f"Camera Error: {error_message}")
        self.status_label.setText(f"Camera Error: {error_message}")
    
    def toggle_recording(self):
        if not self.is_recording:
            # Start recording
            self.recorded_frames.clear()
            self.is_recording = True
            self.record_btn.setText("Stop Recording")
            self.record_btn.setStyleSheet("QPushButton { background-color: #ff9800; color: white; font-weight: bold; padding: 10px; }")
            self.status_label.setText("Recording... Click 'Stop Recording' to finish")
            self.create_gif_btn.setEnabled(False)
        else:
            # Stop recording
            self.is_recording = False
            self.record_btn.setText("Start Recording")
            self.record_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 10px; }")
            
            if len(self.recorded_frames) > 0:
                self.status_label.setText(f"Recording stopped. {len(self.recorded_frames)} frames captured")
                self.create_gif_btn.setEnabled(True)
            else:
                self.status_label.setText("No frames recorded")

    def update_filename(self):
        self.output_filename = self.filename_input.text()

    def update_fps(self, value):
        self.fps = value
        self.fps_label.setText(str(value))

    def update_width(self, value):
        self.width = value
        self.width_label.setText(str(value))
    
    def update_max_frames(self, value):
        self.max_frames = value
        self.max_frames_label.setText(str(value))

    def create_gif(self):
        if not self.recorded_frames:
            QMessageBox.warning(self, "Warning", "No frames recorded!")
            return
        
        if not self.output_filename.strip():
            QMessageBox.warning(self, "Warning", "Please enter an output filename!")
            return
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.output_filename}_{timestamp}.gif"
        
        # Set output path to Downloads folder - using your correct user directory
        downloads_folder = r'C:\Users\mwilliams\Downloads'
        output_file = os.path.join(downloads_folder, filename)
        
        # Disable buttons during processing
        self.create_gif_btn.setEnabled(False)
        self.record_btn.setEnabled(False)
        
        # Show progress bar
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)
        
        # Start GIF creation
        self.recording_worker = RecordingWorker(
            self.recorded_frames.copy(),
            self.fps,
            self.width,
            output_file
        )
        self.recording_worker.finished.connect(self.on_gif_creation_finished)
        self.recording_worker.error.connect(self.on_gif_creation_error)
        self.recording_worker.progress.connect(self.on_progress_update)
        self.recording_worker.start()

    def on_gif_creation_finished(self, output_file):
        self.progress_bar.setVisible(False)
        self.enable_buttons()
        
        file_size = os.path.getsize(output_file)
        file_size_mb = file_size / (1024 * 1024)
        
        QMessageBox.information(
            self,
            "Success",
            f"GIF created successfully!\n\nFile: {os.path.basename(output_file)}\nFrames: {len(self.recorded_frames)}\nSize: {file_size_mb:.1f} MB\nLocation: {os.path.dirname(output_file)}"
        )
        self.status_label.setText(f"GIF created successfully! Size: {file_size_mb:.1f} MB")

    def on_gif_creation_error(self, error_message):
        self.progress_bar.setVisible(False)
        self.enable_buttons()
        
        QMessageBox.critical(self, "Error", f"GIF creation failed:\n{error_message}")
        self.status_label.setText(f"Error: {error_message}")

    def on_progress_update(self, message):
        self.status_label.setText(message)

    def enable_buttons(self):
        self.create_gif_btn.setEnabled(len(self.recorded_frames) > 0)
        self.record_btn.setEnabled(True)

    def closeEvent(self, event):
        # Stop camera worker
        if self.camera_worker:
            self.camera_worker.stop()
            self.camera_worker.wait()
        
        # Stop recording worker
        if self.recording_worker and self.recording_worker.isRunning():
            reply = QMessageBox.question(
                self,
                "Confirm Exit",
                "GIF creation is in progress. Are you sure you want to exit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.recording_worker.terminate()
                self.recording_worker.wait()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()

def main():
    app = QApplication(sys.argv)
    window = LiveGifMakerWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
