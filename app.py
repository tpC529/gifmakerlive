"""
FastAPI web application for GIF creation from video uploads.
This is the web-based version of the live.py desktop application.
"""

import os
import subprocess
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

# Create directories for uploads and output
BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = FastAPI(
    title="GIF Maker Live - Web",
    description="Convert video files to GIFs via web interface",
    version="1.0.0"
)

# Add CORS middleware for broader compatibility
# Note: In production, replace "*" with specific allowed origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,  # Disabled for wildcard origins
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


def convert_video_to_gif(
    video_path: str,
    output_path: str,
    fps: int = 10,
    width: int = 320
) -> str:
    """
    Convert a video file to GIF using FFmpeg.
    
    Args:
        video_path: Path to the input video file
        output_path: Path for the output GIF file
        fps: Frames per second for the GIF
        width: Width of the output GIF (height auto-calculated)
    
    Returns:
        Path to the created GIF file
    """
    try:
        # Use FFmpeg subprocess to convert video to GIF
        cmd = [
            'ffmpeg',
            '-y',  # Overwrite output
            '-i', video_path,
            '-vf', f'fps={fps},scale={width}:-1:flags=lanczos',
            '-loop', '0',
            output_path
        ]
        result = subprocess.run(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120  # 2 minute timeout
        )
        if result.returncode != 0:
            raise Exception(f"FFmpeg error: {result.stderr.decode('utf-8', errors='ignore')}")
        return output_path
    except subprocess.TimeoutExpired:
        raise HTTPException(
            status_code=500,
            detail="Video conversion timed out"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"FFmpeg error: {str(e)}"
        )


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the main HTML page."""
    html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GIF Maker Live - Web</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        
        .container {
            max-width: 700px;
            margin: 0 auto;
            background: white;
            border-radius: 16px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 40px;
        }
        
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
            font-size: 2rem;
        }
        
        /* Tab navigation */
        .tab-nav {
            display: flex;
            margin-bottom: 25px;
            border-radius: 8px;
            overflow: hidden;
            border: 2px solid #667eea;
        }
        
        .tab-btn {
            flex: 1;
            padding: 12px;
            border: none;
            background: white;
            cursor: pointer;
            font-weight: 600;
            font-size: 14px;
            color: #667eea;
            transition: all 0.3s ease;
        }
        
        .tab-btn.active {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .tab-btn:hover:not(.active) {
            background: #f0f0ff;
        }
        
        .tab-content {
            display: none;
        }
        
        .tab-content.active {
            display: block;
        }
        
        /* Camera section styles */
        .camera-container {
            position: relative;
            margin-bottom: 20px;
            background: #000;
            border-radius: 12px;
            overflow: hidden;
            min-height: 300px;
        }
        
        #cameraPreview {
            width: 100%;
            display: block;
            border-radius: 12px;
        }
        
        .camera-placeholder {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            min-height: 300px;
            color: white;
            text-align: center;
            padding: 20px;
        }
        
        .camera-placeholder-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        
        .recording-indicator {
            position: absolute;
            top: 15px;
            left: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
            background: rgba(244, 67, 54, 0.9);
            color: white;
            padding: 8px 15px;
            border-radius: 20px;
            font-weight: 600;
            font-size: 14px;
            opacity: 0;
            transition: opacity 0.3s ease;
        }
        
        .recording-indicator.active {
            opacity: 1;
        }
        
        .recording-dot {
            width: 10px;
            height: 10px;
            background: white;
            border-radius: 50%;
            animation: pulse 1s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .camera-controls {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .camera-select-container {
            flex: 1;
        }
        
        .camera-select-container select {
            width: 100%;
            padding: 10px;
            border: 2px solid #ddd;
            border-radius: 8px;
            font-size: 14px;
            background: white;
            cursor: pointer;
        }
        
        .camera-select-container select:focus {
            outline: none;
            border-color: #667eea;
        }
        
        .btn-start-camera {
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-weight: 600;
            transition: all 0.3s ease;
        }
        
        .btn-start-camera:hover {
            background: #5a6fd6;
        }
        
        .btn-record {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            background: #f44336;
            color: white;
            margin-bottom: 15px;
        }
        
        .btn-record:hover:not(:disabled) {
            background: #d32f2f;
            transform: translateY(-2px);
        }
        
        .btn-record.recording {
            background: #ff9800;
        }
        
        .btn-record.recording:hover {
            background: #f57c00;
        }
        
        .btn-record:disabled {
            opacity: 0.6;
            cursor: not-allowed;
            transform: none;
        }
        
        .recording-stats {
            display: flex;
            justify-content: space-between;
            padding: 12px;
            background: #f5f5f5;
            border-radius: 8px;
            margin-bottom: 20px;
            font-size: 14px;
        }
        
        .stat-item {
            text-align: center;
        }
        
        .stat-label {
            color: #666;
            font-size: 12px;
        }
        
        .stat-value {
            font-weight: 600;
            color: #333;
            font-size: 16px;
        }
        
        /* Upload area styles */
        .upload-area {
            border: 3px dashed #ddd;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 20px;
            background: #fafafa;
        }
        
        .upload-area:hover {
            border-color: #667eea;
            background: #f0f0ff;
        }
        
        .upload-area.dragover {
            border-color: #667eea;
            background: #e8e8ff;
        }
        
        .upload-icon {
            font-size: 48px;
            margin-bottom: 15px;
        }
        
        .upload-text {
            color: #666;
            font-size: 16px;
        }
        
        #fileInput {
            display: none;
        }
        
        .file-info {
            margin-bottom: 20px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 8px;
            font-size: 14px;
            color: #666;
        }
        
        /* Common settings styles */
        .settings-group {
            margin-bottom: 20px;
        }
        
        .settings-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: 600;
            color: #444;
        }
        
        .slider-container {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        input[type="range"] {
            flex: 1;
            height: 8px;
            border-radius: 4px;
            background: #ddd;
            outline: none;
            -webkit-appearance: none;
        }
        
        input[type="range"]::-webkit-slider-thumb {
            -webkit-appearance: none;
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background: #667eea;
            cursor: pointer;
        }
        
        .slider-value {
            min-width: 50px;
            text-align: right;
            font-weight: 600;
            color: #667eea;
        }
        
        .btn {
            width: 100%;
            padding: 15px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
        }
        
        .btn-primary:hover:not(:disabled) {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        
        .btn-primary:disabled {
            opacity: 0.6;
            cursor: not-allowed;
        }
        
        .status {
            margin-top: 20px;
            padding: 15px;
            border-radius: 8px;
            text-align: center;
            display: none;
        }
        
        .status.info {
            background: #e3f2fd;
            color: #1976d2;
            display: block;
        }
        
        .status.success {
            background: #e8f5e9;
            color: #388e3c;
            display: block;
        }
        
        .status.error {
            background: #ffebee;
            color: #d32f2f;
            display: block;
        }
        
        .preview-container {
            margin-top: 20px;
            text-align: center;
        }
        
        .preview-container img {
            max-width: 100%;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        }
        
        .download-btn {
            margin-top: 15px;
            background: #4CAF50;
            color: white;
        }
        
        .download-btn:hover {
            background: #45a049;
        }
        
        .progress-bar {
            width: 100%;
            height: 8px;
            background: #ddd;
            border-radius: 4px;
            margin-top: 10px;
            overflow: hidden;
        }
        
        .progress-fill {
            height: 100%;
            background: linear-gradient(90deg, #667eea, #764ba2);
            width: 0%;
            transition: width 0.3s ease;
        }
        
        /* Responsive */
        @media (max-width: 600px) {
            .container {
                padding: 20px;
            }
            
            h1 {
                font-size: 1.5rem;
            }
            
            .camera-controls {
                flex-direction: column;
            }
            
            .recording-stats {
                flex-wrap: wrap;
                gap: 10px;
            }
            
            .stat-item {
                flex: 1;
                min-width: 80px;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 GIF Maker Live</h1>
        
        <!-- Tab Navigation -->
        <div class="tab-nav">
            <button class="tab-btn active" data-tab="camera">📹 Live Camera</button>
            <button class="tab-btn" data-tab="upload">📁 Upload Video</button>
        </div>
        
        <!-- Camera Tab -->
        <div id="cameraTab" class="tab-content active">
            <div class="camera-container" id="cameraContainer">
                <video id="cameraPreview" autoplay playsinline muted></video>
                <div class="camera-placeholder" id="cameraPlaceholder">
                    <div class="camera-placeholder-icon">📷</div>
                    <p>Click "Start Camera" to begin</p>
                    <p><small>Camera access required</small></p>
                </div>
                <div class="recording-indicator" id="recordingIndicator">
                    <div class="recording-dot"></div>
                    <span>REC</span>
                </div>
            </div>
            
            <div class="camera-controls">
                <div class="camera-select-container">
                    <select id="cameraSelect">
                        <option value="">Select camera...</option>
                    </select>
                </div>
                <button class="btn-start-camera" id="startCameraBtn">Start Camera</button>
            </div>
            
            <button class="btn-record" id="recordBtn" disabled>🔴 Start Recording</button>
            
            <div class="recording-stats">
                <div class="stat-item">
                    <div class="stat-label">Duration</div>
                    <div class="stat-value" id="recordingDuration">0:00</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Frames</div>
                    <div class="stat-value" id="frameCount">0</div>
                </div>
                <div class="stat-item">
                    <div class="stat-label">Max Frames</div>
                    <div class="stat-value" id="maxFramesDisplay">150</div>
                </div>
            </div>
            
            <div class="settings-group">
                <label>Frame Rate (FPS)</label>
                <div class="slider-container">
                    <input type="range" id="cameraFpsSlider" min="1" max="30" value="8">
                    <span class="slider-value" id="cameraFpsValue">8</span>
                </div>
            </div>
            
            <div class="settings-group">
                <label>Width (pixels)</label>
                <div class="slider-container">
                    <input type="range" id="cameraWidthSlider" min="100" max="800" value="320">
                    <span class="slider-value" id="cameraWidthValue">320</span>
                </div>
            </div>
            
            <div class="settings-group">
                <label>Max Frames</label>
                <div class="slider-container">
                    <input type="range" id="maxFramesSlider" min="30" max="300" value="150">
                    <span class="slider-value" id="maxFramesValue">150</span>
                </div>
            </div>
            
            <button class="btn btn-primary" id="createGifBtn" disabled>Create GIF</button>
            
            <div class="status" id="cameraStatus"></div>
            
            <div class="progress-bar" id="cameraProgressBar" style="display: none;">
                <div class="progress-fill" id="cameraProgressFill"></div>
            </div>
            
            <div class="preview-container" id="cameraPreviewContainer" style="display: none;">
                <img id="cameraGifPreview" src="" alt="Generated GIF">
                <a id="cameraDownloadLink" href="" download>
                    <button class="btn download-btn">⬇️ Download GIF</button>
                </a>
            </div>
        </div>
        
        <!-- Upload Tab -->
        <div id="uploadTab" class="tab-content">
            <div class="upload-area" id="uploadArea">
                <div class="upload-icon">📁</div>
                <div class="upload-text">
                    <strong>Click to upload</strong> or drag and drop<br>
                    <small>MP4, AVI, MOV, WebM supported</small>
                </div>
                <input type="file" id="fileInput" accept="video/*">
            </div>
            
            <div class="file-info" id="fileInfo" style="display: none;">
                Selected: <span id="fileName"></span>
            </div>
            
            <div class="settings-group">
                <label>Frame Rate (FPS)</label>
                <div class="slider-container">
                    <input type="range" id="fpsSlider" min="1" max="30" value="10">
                    <span class="slider-value" id="fpsValue">10</span>
                </div>
            </div>
            
            <div class="settings-group">
                <label>Width (pixels)</label>
                <div class="slider-container">
                    <input type="range" id="widthSlider" min="100" max="800" value="320">
                    <span class="slider-value" id="widthValue">320</span>
                </div>
            </div>
            
            <button class="btn btn-primary" id="convertBtn" disabled>
                Convert to GIF
            </button>
            
            <div class="status" id="status"></div>
            
            <div class="progress-bar" id="progressBar" style="display: none;">
                <div class="progress-fill" id="progressFill"></div>
            </div>
            
            <div class="preview-container" id="previewContainer" style="display: none;">
                <img id="gifPreview" src="" alt="Generated GIF">
                <a id="downloadLink" href="" download>
                    <button class="btn download-btn">⬇️ Download GIF</button>
                </a>
            </div>
        </div>
    </div>

    <script>
        // Tab Navigation
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');
        
        tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const tabId = btn.dataset.tab;
                
                tabBtns.forEach(b => b.classList.remove('active'));
                tabContents.forEach(c => c.classList.remove('active'));
                
                btn.classList.add('active');
                document.getElementById(tabId + 'Tab').classList.add('active');
            });
        });
        
        // ============ CAMERA TAB ============
        const cameraPreview = document.getElementById('cameraPreview');
        const cameraPlaceholder = document.getElementById('cameraPlaceholder');
        const cameraSelect = document.getElementById('cameraSelect');
        const startCameraBtn = document.getElementById('startCameraBtn');
        const recordBtn = document.getElementById('recordBtn');
        const recordingIndicator = document.getElementById('recordingIndicator');
        const recordingDuration = document.getElementById('recordingDuration');
        const frameCount = document.getElementById('frameCount');
        const maxFramesDisplay = document.getElementById('maxFramesDisplay');
        const cameraFpsSlider = document.getElementById('cameraFpsSlider');
        const cameraFpsValue = document.getElementById('cameraFpsValue');
        const cameraWidthSlider = document.getElementById('cameraWidthSlider');
        const cameraWidthValue = document.getElementById('cameraWidthValue');
        const maxFramesSlider = document.getElementById('maxFramesSlider');
        const maxFramesValue = document.getElementById('maxFramesValue');
        const createGifBtn = document.getElementById('createGifBtn');
        const cameraStatus = document.getElementById('cameraStatus');
        const cameraProgressBar = document.getElementById('cameraProgressBar');
        const cameraProgressFill = document.getElementById('cameraProgressFill');
        const cameraPreviewContainer = document.getElementById('cameraPreviewContainer');
        const cameraGifPreview = document.getElementById('cameraGifPreview');
        const cameraDownloadLink = document.getElementById('cameraDownloadLink');
        
        let mediaStream = null;
        let mediaRecorder = null;
        let recordedChunks = [];
        let isRecording = false;
        let recordingStartTime = null;
        let durationInterval = null;
        let estimatedFrames = 0;
        
        // Populate camera list
        async function getCameras() {
            try {
                // Request permission first to get device labels
                await navigator.mediaDevices.getUserMedia({ video: true });
                const devices = await navigator.mediaDevices.enumerateDevices();
                const videoDevices = devices.filter(device => device.kind === 'videoinput');
                
                cameraSelect.innerHTML = '';
                if (videoDevices.length === 0) {
                    cameraSelect.innerHTML = '<option value="">No cameras found</option>';
                    return;
                }
                
                videoDevices.forEach((device, index) => {
                    const option = document.createElement('option');
                    option.value = device.deviceId;
                    option.textContent = device.label || `Camera ${index + 1}`;
                    cameraSelect.appendChild(option);
                });
                
                // Stop the initial stream
                const stream = await navigator.mediaDevices.getUserMedia({ video: true });
                stream.getTracks().forEach(track => track.stop());
                
            } catch (err) {
                console.error('Error getting cameras:', err);
                cameraSelect.innerHTML = '<option value="">Camera access denied</option>';
                showCameraStatus('error', getCameraErrorMessage(err));
            }
        }
        
        function getCameraErrorMessage(err) {
            if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
                return 'Camera access denied. Please allow camera permissions in your browser settings.';
            } else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
                return 'No camera found. Please connect a camera and try again.';
            } else if (err.name === 'NotReadableError' || err.name === 'TrackStartError') {
                return 'Camera is already in use by another application.';
            } else if (err.name === 'OverconstrainedError') {
                return 'Camera does not support the requested settings.';
            } else if (err.name === 'NotSupportedError') {
                return 'Camera access is not supported in this browser. Please use HTTPS.';
            }
            return `Camera error: ${err.message}`;
        }
        
        // Start camera
        async function startCamera() {
            try {
                // Stop existing stream
                if (mediaStream) {
                    mediaStream.getTracks().forEach(track => track.stop());
                }
                
                const deviceId = cameraSelect.value;
                const constraints = {
                    video: deviceId ? { deviceId: { exact: deviceId } } : true,
                    audio: false
                };
                
                mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
                cameraPreview.srcObject = mediaStream;
                cameraPlaceholder.style.display = 'none';
                cameraPreview.style.display = 'block';
                
                recordBtn.disabled = false;
                startCameraBtn.textContent = 'Restart Camera';
                showCameraStatus('success', 'Camera started successfully!');
                
                // Hide status after 2 seconds
                setTimeout(() => {
                    cameraStatus.className = 'status';
                    cameraStatus.style.display = 'none';
                }, 2000);
                
            } catch (err) {
                console.error('Error starting camera:', err);
                showCameraStatus('error', getCameraErrorMessage(err));
            }
        }
        
        // Show camera status
        function showCameraStatus(type, message) {
            cameraStatus.className = `status ${type}`;
            cameraStatus.textContent = message;
            cameraStatus.style.display = 'block';
        }
        
        // Start/Stop recording
        function toggleRecording() {
            if (!isRecording) {
                startRecording();
            } else {
                stopRecording();
            }
        }
        
        function startRecording() {
            recordedChunks = [];
            
            // Determine the best mime type
            const mimeTypes = [
                'video/webm;codecs=vp9',
                'video/webm;codecs=vp8',
                'video/webm',
                'video/mp4'
            ];
            
            let selectedMimeType = '';
            for (const mimeType of mimeTypes) {
                if (MediaRecorder.isTypeSupported(mimeType)) {
                    selectedMimeType = mimeType;
                    break;
                }
            }
            
            if (!selectedMimeType) {
                showCameraStatus('error', 'No supported video format found in this browser.');
                return;
            }
            
            try {
                mediaRecorder = new MediaRecorder(mediaStream, { mimeType: selectedMimeType });
                
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        recordedChunks.push(event.data);
                    }
                };
                
                mediaRecorder.onstop = () => {
                    createGifBtn.disabled = recordedChunks.length === 0;
                };
                
                mediaRecorder.start(100); // Collect data every 100ms
                isRecording = true;
                recordingStartTime = Date.now();
                
                // Update UI
                recordBtn.textContent = '⏹️ Stop Recording';
                recordBtn.classList.add('recording');
                recordingIndicator.classList.add('active');
                createGifBtn.disabled = true;
                
                // Start duration timer
                const maxFrames = parseInt(maxFramesSlider.value);
                const fps = parseInt(cameraFpsSlider.value);
                const maxDuration = (maxFrames / fps) * 1000;
                
                durationInterval = setInterval(() => {
                    const elapsed = Date.now() - recordingStartTime;
                    const seconds = Math.floor(elapsed / 1000);
                    const minutes = Math.floor(seconds / 60);
                    const secs = seconds % 60;
                    recordingDuration.textContent = `${minutes}:${secs.toString().padStart(2, '0')}`;
                    
                    // Estimate frames
                    estimatedFrames = Math.floor((elapsed / 1000) * fps);
                    frameCount.textContent = Math.min(estimatedFrames, maxFrames);
                    
                    // Auto-stop at max duration
                    if (elapsed >= maxDuration) {
                        stopRecording();
                    }
                }, 100);
                
                showCameraStatus('info', 'Recording... Press stop when done.');
                
            } catch (err) {
                console.error('Error starting recording:', err);
                showCameraStatus('error', `Recording error: ${err.message}`);
            }
        }
        
        function stopRecording() {
            if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                mediaRecorder.stop();
            }
            
            isRecording = false;
            
            // Clear timer
            if (durationInterval) {
                clearInterval(durationInterval);
                durationInterval = null;
            }
            
            // Update UI
            recordBtn.textContent = '🔴 Start Recording';
            recordBtn.classList.remove('recording');
            recordingIndicator.classList.remove('active');
            
            if (recordedChunks.length > 0) {
                showCameraStatus('success', `Recording stopped. ${estimatedFrames} frames captured. Click "Create GIF" to convert.`);
                createGifBtn.disabled = false;
            } else {
                showCameraStatus('info', 'No frames recorded.');
            }
        }
        
        // Create GIF from recording
        async function createGifFromRecording() {
            if (recordedChunks.length === 0) {
                showCameraStatus('error', 'No recording available.');
                return;
            }
            
            createGifBtn.disabled = true;
            recordBtn.disabled = true;
            cameraProgressBar.style.display = 'block';
            cameraProgressFill.style.width = '30%';
            showCameraStatus('info', 'Processing recording...');
            cameraPreviewContainer.style.display = 'none';
            
            try {
                // Create blob from recorded chunks
                const mimeType = recordedChunks.length > 0 && recordedChunks[0].type ? recordedChunks[0].type : 'video/webm';
                const blob = new Blob(recordedChunks, { type: mimeType });
                
                // Determine file extension
                const ext = blob.type.includes('mp4') ? 'mp4' : 'webm';
                
                const formData = new FormData();
                formData.append('file', blob, `recording.${ext}`);
                formData.append('fps', cameraFpsSlider.value);
                formData.append('width', cameraWidthSlider.value);
                
                cameraProgressFill.style.width = '60%';
                
                const response = await fetch('/convert', {
                    method: 'POST',
                    body: formData
                });
                
                cameraProgressFill.style.width = '90%';
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Conversion failed');
                }
                
                const result = await response.json();
                cameraProgressFill.style.width = '100%';
                
                showCameraStatus('success', `GIF created successfully! Size: ${result.file_size}`);
                
                // Show preview and download link
                cameraGifPreview.src = `/download/${result.filename}?t=${Date.now()}`;
                cameraDownloadLink.href = `/download/${result.filename}`;
                cameraDownloadLink.download = result.filename;
                cameraPreviewContainer.style.display = 'block';
                
            } catch (err) {
                console.error('Error creating GIF:', err);
                showCameraStatus('error', `Error: ${err.message}`);
            } finally {
                createGifBtn.disabled = recordedChunks.length === 0;
                recordBtn.disabled = !mediaStream;
                setTimeout(() => {
                    cameraProgressBar.style.display = 'none';
                    cameraProgressFill.style.width = '0%';
                }, 1000);
            }
        }
        
        // Event listeners for camera tab
        startCameraBtn.addEventListener('click', startCamera);
        recordBtn.addEventListener('click', toggleRecording);
        createGifBtn.addEventListener('click', createGifFromRecording);
        
        cameraFpsSlider.addEventListener('input', () => {
            cameraFpsValue.textContent = cameraFpsSlider.value;
        });
        
        cameraWidthSlider.addEventListener('input', () => {
            cameraWidthValue.textContent = cameraWidthSlider.value;
        });
        
        maxFramesSlider.addEventListener('input', () => {
            maxFramesValue.textContent = maxFramesSlider.value;
            maxFramesDisplay.textContent = maxFramesSlider.value;
        });
        
        cameraSelect.addEventListener('change', () => {
            if (mediaStream) {
                startCamera();
            }
        });
        
        // Initialize camera list on page load
        getCameras();
        
        // ============ UPLOAD TAB ============
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const fileInfo = document.getElementById('fileInfo');
        const fileName = document.getElementById('fileName');
        const fpsSlider = document.getElementById('fpsSlider');
        const fpsValue = document.getElementById('fpsValue');
        const widthSlider = document.getElementById('widthSlider');
        const widthValue = document.getElementById('widthValue');
        const convertBtn = document.getElementById('convertBtn');
        const status = document.getElementById('status');
        const progressBar = document.getElementById('progressBar');
        const progressFill = document.getElementById('progressFill');
        const previewContainer = document.getElementById('previewContainer');
        const gifPreview = document.getElementById('gifPreview');
        const downloadLink = document.getElementById('downloadLink');
        
        let selectedFile = null;
        
        // Upload area click handler
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // Drag and drop handlers
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });
        
        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('dragover');
        });
        
        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            const files = e.dataTransfer.files;
            if (files.length > 0 && files[0].type.startsWith('video/')) {
                handleFileSelect(files[0]);
            }
        });
        
        // File input change handler
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFileSelect(e.target.files[0]);
            }
        });
        
        function handleFileSelect(file) {
            selectedFile = file;
            fileName.textContent = file.name;
            fileInfo.style.display = 'block';
            convertBtn.disabled = false;
            previewContainer.style.display = 'none';
            status.className = 'status';
            status.style.display = 'none';
        }
        
        // Slider handlers
        fpsSlider.addEventListener('input', () => {
            fpsValue.textContent = fpsSlider.value;
        });
        
        widthSlider.addEventListener('input', () => {
            widthValue.textContent = widthSlider.value;
        });
        
        // Convert button handler
        convertBtn.addEventListener('click', async () => {
            if (!selectedFile) return;
            
            convertBtn.disabled = true;
            status.className = 'status info';
            status.textContent = 'Uploading and converting...';
            progressBar.style.display = 'block';
            progressFill.style.width = '30%';
            previewContainer.style.display = 'none';
            
            const formData = new FormData();
            formData.append('file', selectedFile);
            formData.append('fps', fpsSlider.value);
            formData.append('width', widthSlider.value);
            
            try {
                progressFill.style.width = '60%';
                
                const response = await fetch('/convert', {
                    method: 'POST',
                    body: formData
                });
                
                progressFill.style.width = '90%';
                
                if (!response.ok) {
                    const error = await response.json();
                    throw new Error(error.detail || 'Conversion failed');
                }
                
                const result = await response.json();
                progressFill.style.width = '100%';
                
                status.className = 'status success';
                status.textContent = `GIF created successfully! Size: ${result.file_size}`;
                
                // Show preview and download link
                gifPreview.src = `/download/${result.filename}?t=${Date.now()}`;
                downloadLink.href = `/download/${result.filename}`;
                downloadLink.download = result.filename;
                previewContainer.style.display = 'block';
                
            } catch (error) {
                status.className = 'status error';
                status.textContent = `Error: ${error.message}`;
            } finally {
                convertBtn.disabled = false;
                setTimeout(() => {
                    progressBar.style.display = 'none';
                    progressFill.style.width = '0%';
                }, 1000);
            }
        });
        
        // Cleanup on page unload
        window.addEventListener('beforeunload', () => {
            if (mediaStream) {
                mediaStream.getTracks().forEach(track => track.stop());
            }
        });
    </script>
</body>
</html>
    """
    return HTMLResponse(content=html_content)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "gif-maker-live"}


@app.post("/convert")
async def convert_video(
    file: UploadFile = File(...),
    fps: int = Form(default=10),
    width: int = Form(default=320)
):
    """
    Convert an uploaded video file to GIF.
    
    Args:
        file: The video file to convert
        fps: Frames per second for the output GIF (1-30)
        width: Width of the output GIF in pixels (100-800)
    
    Returns:
        JSON with the filename and file size of the created GIF
    """
    # Validate parameters
    fps = max(1, min(30, fps))
    width = max(100, min(800, width))
    
    # Validate file extension
    allowed_extensions = {'.mp4', '.avi', '.mov', '.webm', '.mkv', '.m4v'}
    file_ext = Path(file.filename or '').suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Maximum file size: 100MB
    max_file_size = 100 * 1024 * 1024
    
    # Generate unique filename
    unique_id = str(uuid.uuid4())[:8]
    video_ext = file_ext or '.mp4'
    video_path = UPLOAD_DIR / f"{unique_id}{video_ext}"
    gif_filename = f"output_{unique_id}.gif"
    gif_path = OUTPUT_DIR / gif_filename
    
    try:
        # Read uploaded video with size limit
        content = await file.read()
        if len(content) > max_file_size:
            raise HTTPException(
                status_code=400,
                detail=f"File too large. Maximum size is {max_file_size // (1024*1024)}MB"
            )
        
        with open(video_path, 'wb') as f:
            f.write(content)
        
        # Convert to GIF
        convert_video_to_gif(
            str(video_path),
            str(gif_path),
            fps=fps,
            width=width
        )
        
        # Get file size
        file_size = os.path.getsize(gif_path)
        if file_size < 1024:
            size_str = f"{file_size} bytes"
        elif file_size < 1024 * 1024:
            size_str = f"{file_size / 1024:.1f} KB"
        else:
            size_str = f"{file_size / (1024 * 1024):.1f} MB"
        
        return {
            "filename": gif_filename,
            "file_size": size_str,
            "fps": fps,
            "width": width
        }
        
    finally:
        # Clean up uploaded video file
        if video_path.exists():
            try:
                os.unlink(video_path)
            except Exception:
                pass


@app.get("/download/{filename}")
async def download_gif(filename: str):
    """
    Download a generated GIF file.
    
    Args:
        filename: Name of the GIF file to download
    
    Returns:
        The GIF file as a downloadable response
    """
    # Validate filename to prevent directory traversal
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(status_code=400, detail="Invalid filename")
    
    file_path = OUTPUT_DIR / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    return FileResponse(
        path=str(file_path),
        media_type="image/gif",
        filename=filename
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
