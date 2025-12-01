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
            max-width: 600px;
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
        
        .upload-area {
            border: 3px dashed #ddd;
            border-radius: 12px;
            padding: 40px;
            text-align: center;
            cursor: pointer;
            transition: all 0.3s ease;
            margin-bottom: 30px;
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
        
        .settings-group {
            margin-bottom: 25px;
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
        
        .file-info {
            margin-top: 10px;
            padding: 10px;
            background: #f5f5f5;
            border-radius: 8px;
            font-size: 14px;
            color: #666;
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
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 GIF Maker Live</h1>
        
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

    <script>
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
