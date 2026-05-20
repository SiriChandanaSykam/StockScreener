# 🚀 Gamma Screener & News Intelligence Engine

A comprehensive **Real-Time Stock Analysis Platform** for the Indian Market (NSE/BSE).
It combines **Volume/Momentum Screening** with **AI-Powered News Intelligence** to give you a complete market edge.

---

## ✨ What This Application Can Do

### 1. 📊 Real-Time Stock Screening
- **Momentum Scanner**: Identifies stocks with sudden volume spikes or price surges.
- **Technical Analysis**: Automatically calculates RSI, MACD, Moving Averages.
- **Smart Ranking**: Ranks Nifty 50 and FNO stocks by a composite "Gamma Score".
- **Charts**: Interactive TradingView-style charts.

### 2. 📰 AI News Intelligence (New!)
- **Live Aggregation**: Scrapes real-time news from **Economic Times** and **Moneycontrol** (RSS Feeds).
- **AI Analysis**: Uses **Google Gemini 2.0 Flash** (or a smart Offline Mock mode) to:
  - **Score Relevance** (1-10): Filters out junk/noise.
  - **Analyze Sentiment**: Bullish 🟢 / Bearish 🔴 detection.
  - **Extract Tickers**: Automatically links news to specific stocks (e.g., "TCS").
- **Smart Filtering**: Show only "High Impact" news, ignore the noise.

---

## 🛠️ Technology Stack (What It Uses)

This is a modern **Full-Stack Application** built with industry-standard tools:

### Frontend (The UI)
- **Framework**: [React](https://react.dev/) with [Vite](https://vitejs.dev/) (Fast & Modern).
- **Language**: [TypeScript](https://www.typescriptlang.org/) (Safe & Robust).
- **Styling**: [Tailwind CSS](https://tailwindcss.com/) (Beautiful dark-mode UI).
- **Charts**: TradingView Lightweight Charts.

### Backend (The Brains)
- **API Server**: [FastAPI](https://fastapi.tiangolo.com/) (High-performance Python API).
- **Database**: [SQLite](https://www.sqlite.org/) (Zero-config, fast file-based DB).
- **Task Queue**: [Celery](https://docs.celeryq.dev/) + [Redis](https://redis.io/) (For background scraping).
- **ORM**: [SQLAlchemy](https://www.sqlalchemy.org/) (Async database interaction).

### AI & Intelligence
- **LLM**: **Google Gemini 2.0 Flash** (Free Tier) via `google-generativeai`.
- **Extraction**: `feedparser` for RSS, `BeautifulSoup` for web scraping.
- **Offline Mode**: Custom keyword-weighted sentiment analyzer (works without API keys).

---

## 💸 "Free Forever" Architecture

You asked about running this **without limits or costs**:

1.  **Data Sources**: We use **RSS Feeds** (Public & Free) instead of expensive APIs (Bloomberg/Reuters).
2.  **Database**: **SQLite** is free, local, and requires no server.
3.  **AI Analysis**:
    *   **Option A (Best)**: **Google Gemini Free Tier** (15 requests/min). Zero cost, huge intelligence.
    *   **Option B (Offline)**: Our built-in **Mock Analyzer** uses keyword logic ("Profit UP" = Bullish). It costs $0 and runs offline forever.
    *   **Option C (Future)**: You can swap Gemini for **FinBERT** (HuggingFace). It's an open-source model you can run locally on your GPU for free.

---

## 🚀 How to Run It

You need to run **3 commands** in separate terminals to start the full system:

### 1. Main Backend (Calculations & Charts)
```bash
cd "d:\STOCK SCREENER\volume-screener"
uvicorn api.main:app --reload --port 8000
```

### 2. News Engine (News Scraping & AI)
```bash
cd "d:\STOCK SCREENER\volume-screener"
uvicorn news_engine.main:app --reload --port 8001
```

### 3. Frontend (User Interface)
```bash
cd "d:\STOCK SCREENER\volume-screener\gamma-frontend"
npm run dev
```

👉 **Open in Browser:** [http://localhost:5173](http://localhost:5173)

---

## 📁 Project Structure

- `gamma-frontend/` → React User Interface code.
- `news_engine/` → The AI News sub-system.
- `api/` → Main backend API.
- `strategies/` → Python files defining trading strategies.
- `utils/` → Mathematical helper functions.
