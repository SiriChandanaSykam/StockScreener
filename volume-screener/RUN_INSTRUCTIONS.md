# 🚀 How to Run Stock Screener & News Engine

You need to open **3 separate terminals** (Command Prompt or PowerShell) to run the full system.

## Terminal 1: News Engine API (The Backend)
This serves the news data to your frontend.
```powershell
cd "d:\STOCK SCREENER\volume-screener"
uvicorn news-engine.main:app --reload --port 8001
```
*Wait until you see: `Application startup complete`*

## Terminal 2: Background Scheduler (The Worker)
This fetches news every 2 minutes and runs AI analysis.
```powershell
cd "d:\STOCK SCREENER\volume-screener\news-engine"
python scheduler.py
```
*You will see logs like: `📰 CYCLE #1... 📡 Fetching...`*

## Terminal 3: Frontend (The UI)
This runs the website you interact with.
```powershell
cd "d:\STOCK SCREENER\volume-screener\gamma-frontend"
npm run dev
```
*Once running, open your browser to: http://localhost:5173/news*

---

## 🛠️ Useful Scripts

### 📋 Generate Daily News Digest
Get a summary of the last 24h news.
```powershell
cd "d:\STOCK SCREENER\volume-screener\news-engine"
python generate_digest.py
```

### 🏷️ Fix/Update Tickers
If you feel tickers aren't matching correctly, run this to re-scan old news.
```powershell
cd "d:\STOCK SCREENER\volume-screener\news-engine"
python backfill_tickers.py
```
