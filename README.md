# GIF Maker Live

A web application to convert video files to GIFs using FastAPI.

## Features

- Upload video files (MP4, AVI, MOV, WebM)
- Configure GIF settings:
  - Frame rate (FPS): 1-30
  - Width: 100-800 pixels
- Preview and download generated GIFs
- Drag and drop file upload
- Progress indicator during conversion

## Requirements

- Python 3.8+
- FFmpeg installed on the system

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/tpC529/gifmakerlive.git
   cd gifmakerlive
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Install FFmpeg (if not already installed):
   
   **Ubuntu/Debian:**
   ```bash
   sudo apt-get update
   sudo apt-get install -y ffmpeg
   ```
   
   **macOS:**
   ```bash
   brew install ffmpeg
   ```
   
   **Windows:**
   Download from https://ffmpeg.org/download.html and add to PATH.

## Running the Application

Start the FastAPI server:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000
```

Or run directly with Python:

```bash
python app.py
```

Open your browser and navigate to http://localhost:8000

## API Endpoints

- `GET /` - Web interface
- `GET /health` - Health check endpoint
- `POST /convert` - Convert video to GIF
  - Form data: `file` (video file), `fps` (int), `width` (int)
- `GET /download/{filename}` - Download generated GIF

## Desktop Version

The original desktop version (`live.py`) uses PyQt6 for a native GUI experience with live camera recording capabilities. To use it:

```bash
pip install PyQt6 opencv-python ffmpeg-python numpy
python live.py
```

## License

MIT License
