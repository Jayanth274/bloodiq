# BloodIQ — Blood Supply Intelligence

**BloodIQ** is a premium, GPU-accelerated situational awareness dashboard designed to eliminate emergency blood supply blindspots. It combines high-performance GPU data pipelines with interactive mapping and Google Gemini conversational AI to forecast shortages 72 hours in advance and mobilize active donors instantly.

---

## ⚡ Key Highlights & Benchmarks
- **GPU Accelerated Pipeline**: Uses **NVIDIA RAPIDS (cuDF)** to process over **7.1 Million timeseries rows in 0.06 seconds**, achieving a **248.4x speedup** compared to traditional CPU Pandas execution.
- **72-Hour Predictive Alerts**: Proactively flags critical blood depletion states 3 days before supply reaches absolute zero.
- **Conversational Query Assistant**: Integrates **Google Gemini (gemini-1.5-flash)**, enabling non-technical medical personnel to query live national blood stocks in plain English.
- **Smart Donor Mobilization**: Automatically ranks and routes nearby eligible donors by recipient proximity, blood type rarity, and historical donation recency.

---

## 🏗️ Project Architecture & Structure

The repository is organized into three major layers:

```
BloodIQ/
├── backend/                  # Node.js Express API Server
│   ├── routes/
│   │   ├── availability.js   # Current inventory status & GPS coordinates
│   │   ├── forecast.js       # 72-hour predicted stock counts
│   │   ├── donors.js         # Ranked donor contacts matched by proximity
│   │   └── query.js          # Google Gemini AI assistant endpoint
│   ├── server.js             # API entrypoint
│   └── package.json
│
├── frontend/                 # React 18 SPA Client Dashboard
│   ├── public/               # Static assets (Favicons, manifest)
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.jsx   # Filter controls, stats counters & benchmarks
│   │   │   ├── BloodMap.jsx  # Interactive Leaflet.js map visualization
│   │   │   ├── BankPanel.jsx # Side panel displaying live scores & actions
│   │   │   └── ChatBox.jsx   # Interactive Gemini AI Chat input
│   │   ├── App.jsx           # Application state manager
│   │   └── index.js          # Client entrypoint
│
├── pipeline/                 # NVIDIA GPU/CPU Analytics Pipeline
│   └── compute_scores.py     # Aggregations, forecasting, & scoring logic
│
├── data/                     # Ingestion & computed CSV files
│   ├── clean_blood_banks.csv
│   ├── inventory_timeseries.csv
│   ├── clean_donors.csv
│   ├── bloodiq_forecasts.csv # Output of forecasting scoring engine
│   └── mobilized_donors.csv  # Ranked emergency donors output
│
├── ppt.py                    # Presentation slides generator script
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Ingestion and Processing Pipeline
Ensure python dependencies (`pandas`, `numpy`, and optional GPU-supported `cudf` / `cupy`) are installed. Run the scoring pipeline to calculate predictions:
```bash
python pipeline/compute_scores.py
```

### 2. Backend Server
Configure your Google Gemini API Key in `backend/.env`:
```env
PORT=3001
GEMINI_API_KEY=your_gemini_api_key_here
```
Install dependencies and launch the backend API server:
```bash
cd backend
npm install
npm run dev
```

### 3. Frontend Client
Set up the React application:
```bash
cd frontend
npm install
npm start
```
Open [http://localhost:3000](http://localhost:3000) to view the dashboard.

---

## 📊 Presentation Slides Generator
You can recreate the presentation slides summarizing the project by executing the PPT generator script (requires `python-pptx`):
```bash
pip install python-pptx
python ppt.py
```
This generates the widescreen PowerPoint file `BloodIQ_Submission.pptx` in the project root.

---

## 💻 Tech Stack Summary
- **Frontend**: React 18, React-Leaflet, Tailwind CSS, PapaParse, SVG icons
- **Backend**: Node.js, Express, PapaParse, Google Gemini API
- **Pipeline**: Python, NVIDIA RAPIDS (cuDF), Pandas
- **Storage/Cloud**: Google Cloud Storage, Google BigQuery
