# Gamma Screener & News Intelligence Engine - Project Guide

## 🗺️ System Architecture

The project consists of three main pillars:
1.  **News Intelligence Engine** (`/news-engine`): Backend for scraping, AI analysis, and serving news data.
2.  **Gamma Frontend** (`/gamma-frontend`): Modern React/Vite user interface.
3.  **Core Screener Logic** (`/root` & `/utils`): Underlying Python logic for stock data and technical analysis.

---

## 📂 File Structure Breakdown

### 1. News Intelligence Engine (`/news-engine`)
*The brain of the operation. Handles data ingestion, storage, and API.*

| File/Folder | Functionality |
|-------------|---------------|
| `main.py` | **Entry Point**. Sets up the FastAPI app, CORS, and database lifecycle. |
| `worker.py` | **Celery Tasks**. Background workers for fetching news (`fetch_market_updates`) and running AI analysis (`analyze_news_item`). |
| `api/routes.py` | **API Endpoints**. Defines URLs like `/news/feed`, `/news/latest`, and `/news/stats`. |
| `api/schemas.py` | **Data Models**. Pydantic models ensuring API responses are structured (e.g., matching frontend types). |
| `services/ai_service.py` | **Intelligence**. Contains `MarketAnalyst` class that prompts the LLM to analyze impact/sentiment. |
| `services/ingest_service.py`| **Ingestion**. Smart logic to fetch news, deduplicate (URL/Title checks), and trigger analysis. |
| `ingestors/bse_scraper.py` | **Scraper**. Specialized scraper for BSE India Corporate Announcements. |
| `storage/models.py` | **Database**. SQLAlchemy definitions for `NewsItem` table. |

### 2. Gamma Frontend (`/gamma-frontend`)
*The face of the application. Built with React, TypeScript, and Tailwind CSS.*

| File/Folder | Functionality |
|-------------|---------------|
| `src/App.tsx` | **Router**. Maps URLs (e.g., `/`, `/news`, `/stock/:id`) to page components. |
| `src/components/NewsFeed.tsx`| **News Page**. The main dashboard for news. Handles filtering, live polling, and infinite scroll. |
| `src/components/NewsCard.tsx`| **Smart Component**. Displays individual news with color-coded badges, AI summaries, and expandable details. |
| `src/hooks/useNewsStream.ts` | **Custom Hook**. Manages the complex state of fetching data and polling for updates every 30s. |
| `src/components/Dashboard.tsx` | **Main Dashboard**. The landing page showing Nifty 50, Sectors, and navigation to News. |
| `src/services/` | **API Calls**. Functions to fetch stock data (legacy) and news data. |

### 3. Core/Legacy Logic (`/root`)
*The foundation. Likely used by older interfaces or shared utilities.*

| File/Folder | Functionality |
|-------------|---------------|
| `utils/` | Shared utilities for fetching stock data (`data_fetcher.py`) and calculations. |
| `strategies/` | Quant strategies for stock screening. |
| `app.py` | Likely the legacy entry point (Streamlit or basic Flask). |

---

## 🚀 How to Run Everything (The "3-Terminal" Setup)

To have the full system running similar to a production environment, you need **3 separate terminals**.

### Terminal 1: Backend API (News Engine)
*Hosts the data and logic.*
```powershell
cd "d:\STOCK SCREENER\volume-screener\news-engine"
uvicorn main:app --reload --port 8001
```
✅ **Verifiction**: Open [http://localhost:8001/docs](http://localhost:8001/docs) to see Swagger UI.

### Terminal 2: Frontend (React App)
*Hosts the website you interact with.*
```powershell
cd "d:\STOCK SCREENER\volume-screener\gamma-frontend"
npm run dev
```
✅ **Verification**: Open [http://localhost:5173](http://localhost:5173). You should see the Dashboard. Click "News" to see the feed.

### Terminal 3: Background Worker (Celery)
*Does the heavy lifting (scraping & AI) in the background.*
```powershell
cd "d:\STOCK SCREENER\volume-screener\news-engine"
celery -A worker worker --loglevel=info
```
*(Note: Requires Redis server to be running locally)*

---

## 🔄 Data Flow Summary

1.  **Ingestion**: `worker.py` (Terminal 3) wakes up periodically, calls `bse_scraper.py` to get raw data.
2.  **Processing**: `ingest_service.py` saves it to DB. Triggers `ai_service.py` to analyze it.
3.  **Serving**: `gamma-frontend` (Terminal 2) requests data via `useNewsStream.ts`.
4.  **Delivery**: `main.py` (Terminal 1) receives request, queries DB, returns JSON.
5.  **Display**: `NewsCard.tsx` renders the green/red badges based on the JSON data.
