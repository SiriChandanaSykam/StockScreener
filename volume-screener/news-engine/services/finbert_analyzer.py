"""
FinBERT Sentiment Analyzer - FREE FOREVER Local AI

Uses HuggingFace's ProsusAI/finbert model for financial sentiment analysis.
Runs locally on CPU/GPU with no API limits or costs.

Trained on:
- Reuters 1.8M financial articles
- Financial PhraseBank dataset

Output: POSITIVE / NEGATIVE / NEUTRAL with confidence scores
"""

import os
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    """Result from FinBERT analysis."""
    label: str  # POSITIVE, NEGATIVE, NEUTRAL
    score: float  # Confidence 0.0 - 1.0
    
    def to_dict(self) -> Dict:
        return {
            "label": self.label,
            "score": self.score,
            "sentiment": self._map_to_market_sentiment(),
        }
    
    def _map_to_market_sentiment(self) -> str:
        """Map FinBERT labels to market terminology."""
        mapping = {
            "positive": "Bullish",
            "negative": "Bearish",
            "neutral": "Neutral",
        }
        return mapping.get(self.label.lower(), "Neutral")


class FinBERTAnalyzer:
    """
    Financial sentiment analyzer using FinBERT.
    
    Features:
    - Runs locally (no API costs)
    - Trained specifically on financial text
    - Supports CPU and GPU
    - ~0.1s per headline on GPU, ~2s on CPU
    """
    
    _instance = None
    _model_loaded = False
    
    def __new__(cls):
        """Singleton pattern - only load model once."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Initialize FinBERT (lazy loading)."""
        if not FinBERTAnalyzer._model_loaded:
            self.pipeline = None
            self.device = -1  # -1 for CPU, 0 for GPU
            self._check_gpu()
    
    def _check_gpu(self):
        """Check if GPU is available."""
        try:
            import torch
            if torch.cuda.is_available():
                self.device = 0
                logger.info("🚀 GPU detected - FinBERT will use CUDA")
            else:
                logger.info("💻 No GPU - FinBERT will use CPU")
        except ImportError:
            logger.warning("⚠️ torch not installed, using CPU")
    
    def _load_model(self):
        """Load FinBERT model (first call only)."""
        if self.pipeline is not None:
            return
        
        try:
            from transformers import pipeline
            
            logger.info("📥 Loading FinBERT model (first time may take ~1 min)...")
            
            self.pipeline = pipeline(
                "sentiment-analysis",
                model="ProsusAI/finbert",
                device=self.device,
            )
            
            FinBERTAnalyzer._model_loaded = True
            logger.info("✅ FinBERT loaded successfully!")
            
        except Exception as e:
            logger.error(f"❌ Failed to load FinBERT: {e}")
            raise
    
    def analyze(self, text: str) -> SentimentResult:
        """
        Analyze sentiment of a single text.
        
        Args:
            text: News headline or article text
            
        Returns:
            SentimentResult with label and confidence
        """
        self._load_model()
        
        try:
            # Truncate to model max length
            text = text[:512] if len(text) > 512 else text
            
            result = self.pipeline(text)[0]
            
            return SentimentResult(
                label=result["label"],
                score=result["score"],
            )
            
        except Exception as e:
            logger.error(f"Analysis error: {e}")
            return SentimentResult(label="neutral", score=0.5)
    
    def analyze_batch(self, texts: List[str]) -> List[SentimentResult]:
        """
        Analyze multiple texts efficiently.
        
        Args:
            texts: List of headlines/articles
            
        Returns:
            List of SentimentResults
        """
        self._load_model()
        
        results = []
        
        # Process in batches for efficiency
        batch_size = 8
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            batch = [t[:512] for t in batch]  # Truncate
            
            try:
                batch_results = self.pipeline(batch)
                
                for r in batch_results:
                    results.append(SentimentResult(
                        label=r["label"],
                        score=r["score"],
                    ))
                    
            except Exception as e:
                logger.error(f"Batch analysis error: {e}")
                # Fallback for failed batch
                for _ in batch:
                    results.append(SentimentResult(label="neutral", score=0.5))
        
        return results
    
    def get_relevance_score(self, sentiment_result: SentimentResult) -> int:
        """
        Convert sentiment to relevance score (1-10).
        
        High confidence positive/negative = High relevance
        Low confidence or neutral = Low relevance
        """
        confidence = sentiment_result.score
        label = sentiment_result.label.lower()
        
        if label == "neutral":
            # Neutral news is less actionable
            if confidence > 0.9:
                return 3
            return 2
        
        # Positive or Negative
        if confidence >= 0.95:
            return 10
        elif confidence >= 0.90:
            return 9
        elif confidence >= 0.85:
            return 8
        elif confidence >= 0.80:
            return 7
        elif confidence >= 0.70:
            return 6
        elif confidence >= 0.60:
            return 5
        else:
            return 4


# Quick test when run directly
if __name__ == "__main__":
    print("🧪 Testing FinBERT Analyzer...")
    
    analyzer = FinBERTAnalyzer()
    
    test_headlines = [
        "Reliance Industries posts 45% profit growth in Q3",
        "TCS faces regulatory penalties from SEBI",
        "Infosys announces $2B acquisition of US tech company",
        "Markets remain flat amid global uncertainty",
        "HDFC Bank declares record dividend of ₹19 per share",
    ]
    
    print("\n📊 Analysis Results:\n")
    
    for headline in test_headlines:
        result = analyzer.analyze(headline)
        relevance = analyzer.get_relevance_score(result)
        
        emoji = "🟢" if result.label.lower() == "positive" else "🔴" if result.label.lower() == "negative" else "⚪"
        
        print(f"{emoji} [{result.label}] {result.score:.2%} | Relevance: {relevance}/10")
        print(f"   {headline}\n")
