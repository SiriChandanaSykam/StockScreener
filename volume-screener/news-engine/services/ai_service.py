"""
AI Service for Market News Analysis.

Provides structured analysis of news using LLM (with mock implementation for testing).
Uses prompt engineering optimized for Indian market corporate filings.
"""

import os
import json
import random
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class Sentiment(str, Enum):
    """Market sentiment classification."""
    BULLISH = "Bullish"
    BEARISH = "Bearish"
    NEUTRAL = "Neutral"


@dataclass
class AnalysisResult:
    """
    Structured output from AI analysis.
    
    This is the exact format returned by analyze_text().
    All fields are designed for downstream processing.
    """
    relevance_score: int  # 1-10: How relevant/impactful for traders
    sentiment: str  # Bullish/Bearish/Neutral
    affected_tickers: List[str]  # Tickers mentioned or impacted
    summary: str  # Max 15 words, extremely direct
    
    # Additional fields for advanced processing
    category: Optional[str] = None  # financial_results, acquisition, etc.
    confidence: float = 0.0  # Model's confidence in analysis (0-1)
    key_metrics: Optional[Dict[str, Any]] = None  # Extracted numbers (revenue, %, etc.)
    reasoning: Optional[str] = None  # Brief explanation of score
    model_version: str = "mock-v1"
    processed_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return asdict(self)


# =============================================================================
# PROMPT ENGINEERING - System Prompt for LLM
# =============================================================================

SYSTEM_PROMPT = """You are "Gamma", a Senior Quantitative Analyst for the Indian Stock Market (NSE/BSE). 
Your job is to filter noise and extract signal from high-frequency news flow.

CONTEXT:
- You are processing raw updates (Exchange filings, Reuters wires, Corporate Announcements).
- Most news is "Noise" (Routine disclosures, generic statements).
- Rare news is "Alpha" (Capex, strategic shifts, unexpected earnings, SEBI orders).

YOUR OUTPUT MUST BE STRICT JSON:
{
  "relevance_score": (int 1-10) -> 10 is Market Moving (Upper Circuit), 1 is Noise.
  "sentiment": (str) -> "Bullish", "Bearish", or "Neutral".
  "affected_tickers": (list) -> NSE Ticker symbols ONLY (e.g., ["RELIANCE", "TCS"]).
  "summary": (str) -> Max 15 words. Brutally direct. No filler.
  "reasoning": (str) -> Why you gave this score.
}

SCORING RULES:
- SCORE 8-10: Earnings beat >20%, New Orders >5% of Market Cap, SEBI Ban/Clearance, M&A.
- SCORE 5-7: Moderate order wins, Management changes, Sector policy shifts.
- SCORE 1-4: routine AGM notices, "trading window closure", duplicate news, loss of share certificates.

INDIAN MARKET NUANCES:
- Convert "Crores" contextually. A 5Cr order for TCS is Noise (Score 1). A 500Cr order for a Smallcap is Alpha (Score 9).
- Impact Direction: "Custom Duty Hike" = Bearish for Importers, Bullish for Domestic Manufacturers.
- If the news mentions a parent group (e.g., "Adani Group"), identify the specific listed entities (e.g., ADANIENT, ADANIPORTS).

INPUT TEXT:
{text}
"""

USER_PROMPT_TEMPLATE = """Analyze this corporate filing:

**Company/Ticker:** {ticker}
**Headline:** {headline}
**Full Text (if available):** {text}

Provide your structured analysis in JSON format."""


class MarketAnalyst:
    """
    AI-powered market analyst for news/filing analysis.
    
    Features:
    - FinBERT (Primary): Free, unlimited, local sentiment analysis
    - Gemini (Backup): Cloud-based for enhanced summaries
    - Mock (Fallback): Keyword-based for testing
    """
    
    def __init__(
        self,
        mock_mode: bool = True,
        api_key: Optional[str] = None,
        model: str = "gemini-2.0-flash",
        ai_mode: Optional[str] = None,  # NEW: finbert, gemini, mock
    ):
        """
        Initialize the MarketAnalyst.
        
        Args:
            mock_mode: If True, return dummy data (for testing)
            api_key: Gemini API key (from env GEMINI_API_KEY if not provided)
            model: LLM model to use (default: gemini-2.0-flash)
            ai_mode: Override mode - 'finbert', 'gemini', or 'mock'
        """
        self.mock_mode = mock_mode
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model = model
        
        # Determine AI mode
        self.ai_mode = ai_mode or os.getenv("AI_MODE", "finbert")
        
        # Initialize FinBERT (primary, free, local)
        self.finbert = None
        if self.ai_mode == "finbert" or (not self.mock_mode and self.ai_mode != "gemini"):
            try:
                from .finbert_analyzer import FinBERTAnalyzer
                self.finbert = FinBERTAnalyzer()
                print("✅ FinBERT initialized (FREE, unlimited)")
            except ImportError as e:
                print(f"⚠️ FinBERT not available: {e}. Install: pip install transformers torch")
        
        # Configure Gemini (backup for enhanced summaries)
        self.genai = None
        if self.api_key and self.ai_mode == "gemini":
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                self.genai = genai
                print("✅ Gemini configured (quota-limited)")
            except ImportError:
                print("⚠️ google-generativeai not installed.")
        
        # Track usage
        self._request_count = 0
        self._last_request_time: Optional[datetime] = None
    
    def _mock_analyze(self, headline: str, text: Optional[str] = None) -> AnalysisResult:
        """
        Generate mock analysis for testing.
        Uses keyword matching for semi-realistic results.
        """
        headline_lower = headline.lower()
        
        # Keyword-based mock logic for realistic testing
        if any(kw in headline_lower for kw in ["result", "profit", "revenue", "earnings"]):
            return AnalysisResult(
                relevance_score=random.randint(7, 9),
                sentiment=random.choice([Sentiment.BULLISH.value, Sentiment.BEARISH.value]),
                affected_tickers=["MOCK"],
                summary="Quarterly results announced, check detailed numbers",
                category="financial_results",
                confidence=0.85,
                key_metrics={"type": "quarterly_results"},
                reasoning="Financial results are always market-moving",
                model_version="mock-v1",
            )
        
        elif any(kw in headline_lower for kw in ["acquisition", "merger", "takeover"]):
            return AnalysisResult(
                relevance_score=random.randint(8, 10),
                sentiment=Sentiment.BULLISH.value,
                affected_tickers=["MOCK", "TARGET"],
                summary="Major M&A activity, potential sector impact",
                category="acquisition",
                confidence=0.90,
                key_metrics={"type": "m_and_a"},
                reasoning="Acquisitions signal growth strategy",
                model_version="mock-v1",
            )
        
        elif any(kw in headline_lower for kw in ["dividend", "bonus"]):
            return AnalysisResult(
                relevance_score=6,
                sentiment=Sentiment.BULLISH.value,
                affected_tickers=["MOCK"],
                summary="Dividend/Bonus announced, positive for shareholders",
                category="dividend",
                confidence=0.88,
                key_metrics={"type": "dividend"},
                reasoning="Shows company has healthy cash flows",
                model_version="mock-v1",
            )
        
        elif any(kw in headline_lower for kw in ["board meeting", "meeting of board"]):
            return AnalysisResult(
                relevance_score=5,
                sentiment=Sentiment.NEUTRAL.value,
                affected_tickers=["MOCK"],
                summary="Board meeting scheduled, await outcome",
                category="board_meeting",
                confidence=0.70,
                key_metrics=None,
                reasoning="Routine unless specific agenda disclosed",
                model_version="mock-v1",
            )
        
        elif any(kw in headline_lower for kw in ["order", "contract", "deal", "win"]):
            return AnalysisResult(
                relevance_score=random.randint(7, 9),
                sentiment=Sentiment.BULLISH.value,
                affected_tickers=["MOCK"],
                summary="New order/contract won, revenue visibility improves",
                category="order_win",
                confidence=0.82,
                key_metrics={"type": "order_win"},
                reasoning="Order wins indicate strong demand",
                model_version="mock-v1",
            )
        
        else:
            # Default: routine filing
            return AnalysisResult(
                relevance_score=random.randint(2, 4),
                sentiment=Sentiment.NEUTRAL.value,
                affected_tickers=["MOCK"],
                summary="Routine filing, no immediate action required",
                category="general",
                confidence=0.60,
                key_metrics=None,
                reasoning="No specific market-moving information detected",
                model_version="mock-v1",
            )
    
    def _call_llm(self, headline: str, text: Optional[str] = None, ticker: str = "UNKNOWN") -> AnalysisResult:
        """
        Call Google Gemini 1.5 Flash for analysis.
        """
        if self.mock_mode or not self.api_key:
            print(f"⚠️ Mock mode or No API Key. Using mock analysis for: {headline[:50]}...")
            return self._mock_analyze(headline, text)

        try:
            model = self.genai.GenerativeModel(
                model_name=self.model,
                generation_config={"response_mime_type": "application/json"}
            )
            
            prompt = USER_PROMPT_TEMPLATE.format(
                ticker=ticker,
                headline=headline,
                text=text or "Not available"
            )
            
            # Combine System + User prompt for Gemini
            full_prompt = f"{SYSTEM_PROMPT}\n\n{prompt}"
            
            response = model.generate_content(full_prompt)
            
            # Parse JSON
            result_json = json.loads(response.text)
            
            # Ensure safe extraction
            return AnalysisResult(
                relevance_score=int(result_json.get("relevance_score", 5)),
                sentiment=result_json.get("sentiment", "Neutral"),
                affected_tickers=result_json.get("affected_tickers", []) or [ticker],
                summary=result_json.get("summary", headline[:50]),
                reasoning=result_json.get("reasoning", "AI Analysis"),
                confidence=0.95,
                model_version=self.model,
                category="ai_analyzed"
            )
            
        except Exception as e:
            print(f"❌ Gemini API Error: {e}")
            print(f"⚠️ Falling back to mock analysis.")
            return self._mock_analyze(headline, text)
    
    def analyze_text(
        self,
        headline: str,
        text: Optional[str] = None,
        ticker: str = "UNKNOWN",
    ) -> AnalysisResult:
        """
        Analyze a news headline/text and return structured analysis.
        
        Priority:
        1. FinBERT (free, unlimited, local)
        2. Gemini (cloud, quota-limited)
        3. Mock (keyword-based fallback)
        """
        self._request_count += 1
        self._last_request_time = datetime.utcnow()
        
        # If explicitly in mock mode, skip all AI
        if self.mock_mode:
            result = self._mock_analyze(headline, text)
            result.affected_tickers = [ticker] if ticker != "UNKNOWN" else result.affected_tickers
            return result
        
        # Try FinBERT first (PRIMARY - Free, Unlimited)
        if self.finbert is not None:
            try:
                sentiment_result = self.finbert.analyze(headline)
                relevance = self.finbert.get_relevance_score(sentiment_result)
                
                return AnalysisResult(
                    relevance_score=relevance,
                    sentiment=sentiment_result.to_dict()["sentiment"],
                    affected_tickers=[ticker] if ticker != "UNKNOWN" else ["MARKET"],
                    summary=headline[:50] if len(headline) > 50 else headline,
                    category="finbert_analyzed",
                    confidence=sentiment_result.score,
                    reasoning=f"FinBERT: {sentiment_result.label} with {sentiment_result.score:.1%} confidence",
                    model_version="finbert-prosus",
                )
            except Exception as e:
                print(f"⚠️ FinBERT error: {e}, trying Gemini...")
        
        # Try Gemini (BACKUP - Cloud, Quota-Limited)
        if self.genai is not None:
            return self._call_llm(headline, text, ticker)
        
        # Final fallback: Mock analysis
        return self._mock_analyze(headline, text)
    
    def analyze_batch(
        self,
        items: List[Dict[str, Any]],
    ) -> List[AnalysisResult]:
        """Analyze multiple items in batch."""
        results = []
        for item in items:
            result = self.analyze_text(
                headline=item.get("headline", ""),
                text=item.get("text"),
                ticker=item.get("ticker", "UNKNOWN"),
            )
            results.append(result)
        return results
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Return usage statistics."""
        return {
            "request_count": self._request_count,
            "last_request": self._last_request_time.isoformat() if self._last_request_time else None,
            "mock_mode": self.mock_mode,
            "model": self.model,
        }


# Convenience function for quick analysis
def analyze_news(
    headline: str,
    text: Optional[str] = None,
    ticker: str = "UNKNOWN",
    mock_mode: bool = True,
) -> Dict[str, Any]:
    """
    Quick function to analyze a single news item.
    
    Returns dictionary (not AnalysisResult) for easy JSON serialization.
    
    Example:
        result = analyze_news("TCS bags $500M deal", ticker="TCS")
        print(result['relevance_score'])  # 8
    """
    analyst = MarketAnalyst(mock_mode=mock_mode)
    result = analyst.analyze_text(headline, text, ticker)
    return result.to_dict()


# Test
if __name__ == "__main__":
    print("=" * 60)
    print("MarketAnalyst - AI Service Test")
    print("=" * 60)
    
    analyst = MarketAnalyst(mock_mode=True)
    
    test_cases = [
        ("Quarterly Results - Q3 FY2026", "TCS"),
        ("Acquisition of XYZ Limited for ₹500 Cr", "INFY"),
        ("Board Meeting to consider Dividend", "HDFC"),
        ("ISIN Code Update", "RELIANCE"),
        ("Major Order Win - $200M Contract", "LT"),
    ]
    
    for headline, ticker in test_cases:
        result = analyst.analyze_text(headline, ticker=ticker)
        print(f"\n📢 {headline}")
        print(f"   Score: {result.relevance_score}/10 | Sentiment: {result.sentiment}")
        print(f"   Summary: {result.summary}")
        print(f"   Category: {result.category}")
    
    print(f"\n📊 Stats: {analyst.stats}")
