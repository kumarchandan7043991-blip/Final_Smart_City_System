import React, { useState, useEffect } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import "./App.css";

const API_URL = "http://localhost:5001/api/traffic";
const VIDEO_URL_BASE = "http://localhost:5001/video_feed?video_path=";
const UPLOAD_API_URL = "http://localhost:5001/upload_video";

function useTrafficData() {
  const [data, setData] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const res = await fetch(API_URL);
        if (res.ok) {
          const json = await res.json();
          setData(json);
        }
      } catch (err) {
        console.error("Error fetching traffic data", err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 3000); 
    return () => clearInterval(interval);
  }, []);

  return data;
}

function Dashboard({ data }) {
  if (!data || !data.latest) return <p className="loading">Loading Data...</p>;

  const { latest } = data;

  const getDensityColor = (density) => {
    switch (density) {
      case "LOW":
        return "#4caf50";
      case "MEDIUM":
        return "#ff9800";
      case "HIGH":
        return "#f44336";
      default:
        return "#9e9e9e";
    }
  };

  return (
    <div className="dashboard-cards">
      <div className="card">
        <h3>Vehicle Count</h3>
        <h2 className="metric">{latest.vehicle_count}</h2>
        <p className="details">
          Cars: {latest.cars} | Bikes: {latest.bikes} | Buses: {latest.buses} | Trucks: {latest.trucks}
        </p>
      </div>
      <div className="card" style={{ borderTop: `4px solid ${getDensityColor(latest.density)}` }}>
        <h3>Density Indicator</h3>
        <h2 className="metric" style={{ color: getDensityColor(latest.density) }}>
          {latest.density}
        </h2>
      </div>
      <div className="card">
        <h3>Prediction Panel</h3>
        <h2 className="metric">{latest.prediction}</h2>
        <p className="details">Confidence: {(latest.confidence * 100).toFixed(0)}%</p>
      </div>
    </div>
  );
}

function GraphView({ data }) {
  if (!data || !data.history || data.history.length === 0) return <p className="loading">No history available.</p>;

  return (
    <div className="graph-container">
      <h3>Traffic Trend Over Time</h3>
      <div className="chart-wrapper">
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={data.history}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="timestamp" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="vehicle_count" stroke="#2196f3" strokeWidth={3} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

function VideoFeed({ videoPath }) {
  if (!videoPath) return <p className="loading">Please select a video source to start the stream.</p>;
  
  return (
    <div className="video-container">
      <img
        src={`${VIDEO_URL_BASE}${encodeURIComponent(videoPath)}`}
        alt="Live Traffic Feed"
        className="video-stream"
      />
    </div>
  );
}

function App() {
  const data = useTrafficData();
  const [activeVideoPath, setActiveVideoPath] = useState("0");
  const [mode, setMode] = useState("webcam"); 
  const [isUploading, setIsUploading] = useState(false);

  const handleWebcamSelect = () => {
    setMode("webcam");
    setActiveVideoPath("0");
  };

  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setMode("file");
    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(UPLOAD_API_URL, {
        method: "POST",
        body: formData,
      });
      const resData = await response.json();
      if (resData.video_path) {
        setActiveVideoPath(resData.video_path);
      } else {
        alert("Upload failed: " + resData.error);
      }
    } catch (err) {
      console.error(err);
      alert("Error connecting to upload server. Ensure Python API is running on 5001.");
    } finally {
      setIsUploading(false);
    }
  };

  return (
    <div className="App">
      <header className="header">
        <h1>Smart Traffic Dashboard</h1>
      </header>
      
      <div className="container">
        <div className="control-panel">
          <h3>Video Source Selection</h3>
          <div className="toggle-group">
            <button 
              className={mode === "webcam" ? "btn active-btn" : "btn inactive-btn"}
              onClick={handleWebcamSelect}>
               📸 Use Web Camera
            </button>
            <div className="upload-btn-wrapper">
              <button className={mode === "file" ? "btn active-btn" : "btn inactive-btn"}>
                {isUploading ? "Uploading..." : "📂 Upload Custom Video"}
              </button>
              <input 
                type="file" 
                accept="video/*" 
                onChange={handleFileUpload} 
                className="file-input"
              />
            </div>
          </div>
        </div>

        <div className="main-content">
          <VideoFeed videoPath={activeVideoPath} />
          <Dashboard data={data} />
        </div>
        
        <GraphView data={data} />
      </div>
    </div>
  );
}

export default App;
