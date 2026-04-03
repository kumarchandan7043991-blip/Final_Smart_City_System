# Configuration for Smart City Traffic System

import os

# Server settings
HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', 5001))
DEBUG = False

# Paths (relative to backend/)
MODEL_PATH = 'models/yolov8n.pt'
DATA_FILE = '../data/detections.jsonl'
UPLOAD_FOLDER = '../uploads'
FRONTEND_BUILD_PATH = '../frontend/build'

# YOLO settings
VEHICLE_CLASSES = {
    2: 'car',
    3: 'bike',
    5: 'bus',
    7: 'truck'
}
CONFIDENCE_THRESHOLD = 0.3

# History settings
MAX_HISTORY_LENGTH = 10