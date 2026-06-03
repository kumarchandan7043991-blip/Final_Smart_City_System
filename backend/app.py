import logging
import os
import cv2
import json
from datetime import datetime
from flask import Flask, request, Response, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from ultralytics import YOLO
from config import *

app = Flask(__name__, static_folder=FRONTEND_BUILD_PATH + '/static', static_url_path='/static')
CORS(app)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.logger.setLevel(logging.INFO)
logging.basicConfig(level=logging.INFO)
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Lazy-load YOLOv8 model to keep startup lightweight and Render-safe.
model = None


def get_model():
    global model
    if model is None:
        try:
            model = YOLO(MODEL_PATH)
        except Exception as exc:
            app.logger.exception("Failed to load YOLO model")
            raise exc
    return model

# COCO Class IDs for vehicles: 2=car, 3=motorcycle(bike), 5=bus, 7=truck
VEHICLE_CLASSES = VEHICLE_CLASSES

DATA_FILE = DATA_FILE

current_counts = {
    "timestamp": "",
    "vehicle_count": 0,
    "cars": 0,
    "bikes": 0,
    "buses": 0,
    "trucks": 0,
    "density": "LOW",
    "prediction": "STABLE",
    "confidence": 0.5
}

traffic_history = []

def get_density(vehicle_count: int) -> str:
    if vehicle_count <= 10:
        return "LOW"
    elif vehicle_count <= 30:
        return "MEDIUM"
    else:
        return "HIGH"

def update_history(history: list, new_data: dict) -> list:
    history.append(new_data)
    if len(history) > MAX_HISTORY_LENGTH:
        history.pop(0)
    return history

def predict_congestion(history: list):
    if len(history) < 3:
        return "STABLE", 0.5

    counts = [h["vehicle_count"] for h in history]

    if counts[-1] > counts[-2] > counts[-3]:
        return "CONGESTION_INCOMING", 0.8
    else:
        return "STABLE", 0.6

def generate_frames(video_path):
    global current_counts, traffic_history

    if isinstance(video_path, str) and video_path.isdigit():
        video_path = int(video_path)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        app.logger.error("Error opening video stream or file: %s", video_path)
        return

    try:
        model_instance = get_model()
        while True:
            success, frame = cap.read()
            if not success:
                break

            results = model_instance(frame, classes=list(VEHICLE_CLASSES.keys()), conf=CONFIDENCE_THRESHOLD, stream=True)

            temp_counts = {
                "cars": 0,
                "bikes": 0,
                "buses": 0,
                "trucks": 0
            }
            total_vehicles = 0

            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    cls = int(box.cls[0])
                    conf = float(box.conf[0])

                    if cls in VEHICLE_CLASSES:
                        class_name = VEHICLE_CLASSES[cls]

                        if class_name == 'car':
                            temp_counts['cars'] += 1
                        elif class_name == 'bike':
                            temp_counts['bikes'] += 1
                        elif class_name == 'bus':
                            temp_counts['buses'] += 1
                        elif class_name == 'truck':
                            temp_counts['trucks'] += 1

                        total_vehicles += 1

                        color = (0, 255, 0)
                        if class_name == 'bike':
                            color = (0, 165, 255)
                        elif class_name == 'bus':
                            color = (255, 255, 0)
                        elif class_name == 'truck':
                            color = (0, 0, 255)

                        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                        label = f'{class_name} {conf:.2f}'
                        cv2.putText(frame, label, (x1, max(y1 - 10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

            now_str = datetime.now().strftime("%H:%M:%S")
            density = get_density(total_vehicles)
            history_entry = {
                "timestamp": now_str,
                "vehicle_count": total_vehicles
            }
            traffic_history = update_history(traffic_history, history_entry)
            prediction, confidence = predict_congestion(traffic_history)

            current_counts = {
                "timestamp": now_str,
                "vehicle_count": total_vehicles,
                "cars": temp_counts['cars'],
                "bikes": temp_counts['bikes'],
                "buses": temp_counts['buses'],
                "trucks": temp_counts['trucks'],
                "density": density,
                "prediction": prediction,
                "confidence": confidence
            }

            with open(DATA_FILE, 'a') as f:
                f.write(json.dumps(current_counts) + '\n')

            ret, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = buffer.tobytes()

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
    except Exception as exc:
        app.logger.exception("Video processing failed: %s", exc)
    finally:
        cap.release()

@app.route('/')
def index():
    return send_from_directory(FRONTEND_BUILD_PATH, 'index.html')

@app.route('/<path:path>')
def serve_react_app(path):
    build_path = os.path.join(FRONTEND_BUILD_PATH, path)
    if os.path.exists(build_path):
        return send_from_directory(FRONTEND_BUILD_PATH, path)
    return send_from_directory(FRONTEND_BUILD_PATH, 'index.html')

@app.route('/upload_video', methods=['POST'])
def upload_video():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if file:
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({"video_path": filepath}), 200

@app.route('/video_feed')
def video_feed():
    video_path = request.args.get('video_path', '')
    if video_path == '':
        return "No video path provided", 400

    try:
        get_model()
    except Exception as exc:
        app.logger.exception("YOLO model unavailable for /video_feed")
        return jsonify({"error": "YOLO model unavailable", "details": str(exc)}), 503

    return Response(generate_frames(video_path),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/data')
def get_data():
    return jsonify(current_counts)

@app.route('/test')
def test():
    return "Flask is working"


@app.route('/api/traffic')
def api_traffic():
    try:
        return jsonify({
            "latest": current_counts,
            "history": traffic_history
        })
    except Exception as exc:
        app.logger.exception("Failed to serve /api/traffic")
        return jsonify({"error": str(exc)}), 500

if __name__ == '__main__':
    # Initialize JSONL file with header comment or clear it
    open(DATA_FILE, 'w').close()
    
    print("Starting Flask web server on http://localhost:5001")
    app.run(host=HOST, port=PORT, debug=DEBUG)
