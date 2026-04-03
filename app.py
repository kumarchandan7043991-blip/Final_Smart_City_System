import os
import cv2
import json
from datetime import datetime
import requests
import threading
from flask import Flask, render_template, request, Response, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
from ultralytics import YOLO

app = Flask(__name__, static_folder='traffic-dashboard/build/static', static_url_path='/static')
CORS(app)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs('uploads', exist_ok=True)

# Load YOLOv8 model (downloads 'yolov8n.pt' on first run)
model = YOLO('yolov8n.pt')

# COCO Class IDs for vehicles: 2=car, 3=motorcycle(bike), 5=bus, 7=truck
VEHICLE_CLASSES = {
    2: 'car',
    3: 'bike',
    5: 'bus',
    7: 'truck'
}

DATA_FILE = 'detections.jsonl'

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
    if len(history) > 10:
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
    
    # Check if string is just digits (like '0' for webcam)
    if isinstance(video_path, str) and video_path.isdigit():
        video_path = int(video_path)
    
    cap = cv2.VideoCapture(video_path)
    
    if not cap.isOpened():
        print(f"Error opening video stream or file: {video_path}")
        return

    while True:
        success, frame = cap.read()
        if not success:
            break

        # Run YOLOv8 inference on the frame
        results = model(frame, classes=list(VEHICLE_CLASSES.keys()), conf=0.3, stream=True)
        
        # Reset current vehicle counts
        temp_counts = {
            "cars": 0,
            "bikes": 0,
            "buses": 0,
            "trucks": 0
        }
        total_vehicles = 0

        # Annotate frame and count
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Get coordinates
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

                    # Draw bounding box
                    color = (0, 255, 0)
                    if class_name == 'bike':
                        color = (0, 165, 255) # Orange
                    elif class_name == 'bus':
                        color = (255, 255, 0) # Cyan
                    elif class_name == 'truck':
                        color = (0, 0, 255) # Red

                    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                    label = f'{class_name} {conf:.2f}'
                    cv2.putText(frame, label, (x1, max(y1-10, 0)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)

        # Update global state for API access
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

        # Send data to Node.js backend running on 5000 asynchronously
        def post_data():
            try:
                requests.post("http://localhost:5000/api/traffic", json=current_counts, timeout=1)
            except requests.exceptions.RequestException:
                pass
        
        threading.Thread(target=post_data).start()

        # Save to local file continuously (append mode)
        # We save this to disk to ensure data is retained despite any software disturbances
        with open(DATA_FILE, 'a') as f:
            f.write(json.dumps(current_counts) + '\n')

        # Encode the frame in JPEG format
        ret, buffer = cv2.imencode('.jpg', frame)
        frame_bytes = buffer.tobytes()

        # Yield the frame in byte format for HTTP chunked stream
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')

    cap.release()

@app.route('/')
def index():
    return send_from_directory('traffic-dashboard/build', 'index.html')

@app.route('/<path:path>')
def serve_react_app(path):
    build_path = os.path.join('traffic-dashboard', 'build', path)
    if os.path.exists(build_path):
        return send_from_directory('traffic-dashboard/build', path)
    return send_from_directory('traffic-dashboard/build', 'index.html')

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
    
    return Response(generate_frames(video_path),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/data')
def get_data():
    return jsonify(current_counts)

@app.route('/api/traffic')
def api_traffic():
    return jsonify({
        "latest": current_counts,
        "history": traffic_history
    })

if __name__ == '__main__':
    # Initialize JSONL file with header comment or clear it
    open(DATA_FILE, 'w').close()
    
    print("Starting Flask web server on http://localhost:5001")
    app.run(host='0.0.0.0', port=5001, debug=False)
