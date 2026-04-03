# Smart City Traffic Monitoring System

A real-time vehicle detection and traffic monitoring system using YOLOv8 and computer vision.

## Architecture

- **Backend** (Python Flask): Handles video processing, vehicle detection, and API endpoints
- **Frontend** (React): Dashboard with real-time metrics and charts
- **Data**: Persistent storage of detection logs

## Project Structure

```
├── backend/                    # Python Flask backend
│   ├── app.py                 # Main application
│   ├── config.py              # Configuration settings
│   ├── models/
│   │   └── yolov8n.pt        # YOLOv8 model weights
│   └── requirements.txt       # Python dependencies
├── frontend/                   # React dashboard
│   ├── src/
│   ├── public/
│   ├── build/                 # Built React app
│   └── package.json
├── data/
│   └── detections.jsonl       # Detection logs
├── uploads/                   # User-uploaded videos
├── run.bat                    # Startup script
└── README.md
```

## Local Setup

1. **Install Python dependencies:**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Install Node.js dependencies:**
   ```bash
   cd frontend
   npm install
   ```

3. **Run the application:**
   - Windows: Double-click `run.bat`
   - Or manually:
     ```bash
     # Terminal 1: Start backend
     cd backend
     python app.py

     # Terminal 2: Start frontend
     cd frontend
     npm start
     ```

4. Open http://localhost:3001 in your browser

## API Endpoints

- `GET /api/traffic` - Get current traffic data and history
- `GET /video_feed?video_path=<path>` - Stream video with detections
- `POST /upload_video` - Upload video file for processing

## Deployment

### Option 1: Railway (Recommended)

1. Push this repo to GitHub
2. Go to [Railway.app](https://railway.app) and sign up
3. Create new project from GitHub repo
4. Railway will auto-detect Python app and deploy
5. The app will be live at the generated URL

### Option 2: Heroku

1. Install Heroku CLI
2. Move backend files to root (or adjust paths)
3. `heroku create`
4. `git push heroku main`
5. App will be live

### Option 3: Local Demo with ngrok

1. Run the backend locally
2. Download ngrok from https://ngrok.com
3. Sign up for free account and get auth token
4. Run `ngrok http 5001`
5. Share the generated URL

## Features

- Real-time vehicle detection (cars, bikes, buses, trucks)
- Traffic density analysis (LOW/MEDIUM/HIGH)
- Congestion prediction
- Interactive dashboard with charts
- Video upload and streaming
- Webcam support