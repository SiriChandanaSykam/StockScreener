"""
Price Prediction Engine using Weighted Ridge Regression
Implements Z-Score standardization, exponential time decay, and L2 regularization
"""

import numpy as np
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
import sys
sys.path.append('..')


@dataclass
class PredictionResult:
    """Result from the price prediction model"""
    predictedClose: float
    rSquared: float  # Confidence (0-1)
    modelType: str = "Weighted Ridge Regression"
    featureNames: List[str] = field(default_factory=list)
    coefficients: List[float] = field(default_factory=list)


class PricePredictor:
    """
    Weighted Ridge Regression (L2) price predictor.
    
    Features:
    - Z-Score Standardization for numerical stability
    - Exponential Time Decay (WLS) for recency weighting
    - Ridge regularization to prevent overfitting
    - R² confidence scoring
    
    Model Specs:
    - Regularization: α = 0.1 (L2 Penalty)
    - Decay Rate: λ = 0.05
    - Lookback: 60 periods (configurable)
    - Features: 7 (Bias + 6 Engineered)
    """
    
    def __init__(self, alpha: float = 0.5, decay_rate: float = 0.05, lookback: int = 60):
        """
        Initialize the predictor.
        
        Args:
            alpha: Ridge regularization parameter
            decay_rate: Exponential decay rate for time weighting
            lookback: Number of periods to use for training
        """
        self.alpha = alpha
        self.decay_rate = decay_rate
        self.lookback = lookback
        
        self.feature_names = [
            "Bias",
            "Close",
            "Volume", 
            "Range",
            "Close²",
            "Volume×Range",
            "VWAP_Dev"
        ]
        
        # Training statistics for standardization
        self._means: Optional[np.ndarray] = None
        self._stds: Optional[np.ndarray] = None
        self._coefficients: Optional[np.ndarray] = None
    
    def _calculate_vwap(self, highs: np.ndarray, lows: np.ndarray, 
                        closes: np.ndarray, volumes: np.ndarray) -> np.ndarray:
        """Calculate Volume Weighted Average Price"""
        typical_price = (highs + lows + closes) / 3
        cumulative_tp_vol = np.cumsum(typical_price * volumes)
        cumulative_vol = np.cumsum(volumes)
        # Avoid division by zero
        cumulative_vol = np.where(cumulative_vol == 0, 1, cumulative_vol)
        return cumulative_tp_vol / cumulative_vol
    
    def _build_features(self, closes: np.ndarray, volumes: np.ndarray,
                        highs: np.ndarray, lows: np.ndarray) -> np.ndarray:
        """
        Build feature matrix with engineered features.
        
        Features:
        1. Bias (ones)
        2. Close price
        3. Volume
        4. Range (High - Low)
        5. Close² (polynomial)
        6. Volume × Range (interaction term)
        7. VWAP Deviation
        """
        n = len(closes)
        
        # Calculate derived features
        ranges = highs - lows
        close_squared = closes ** 2
        volume_range = volumes * ranges
        vwap = self._calculate_vwap(highs, lows, closes, volumes)
        vwap_deviation = closes - vwap
        
        # Build feature matrix [n x 7]
        X = np.column_stack([
            np.ones(n),          # Bias
            closes,              # Close
            volumes,             # Volume
            ranges,              # Range
            close_squared,       # Close²
            volume_range,        # Volume × Range
            vwap_deviation       # VWAP Deviation
        ])
        
        return X
    
    def _standardize(self, X: np.ndarray, fit: bool = False) -> np.ndarray:
        """
        Z-Score standardization: (x - μ) / σ
        Skip the bias column (first column).
        """
        X_std = X.copy()
        
        if fit:
            # Calculate and store statistics (excluding bias column)
            self._means = np.mean(X[:, 1:], axis=0)
            self._stds = np.std(X[:, 1:], axis=0)
            # Prevent division by zero
            self._stds = np.where(self._stds == 0, 1, self._stds)
        
        if self._means is not None and self._stds is not None:
            X_std[:, 1:] = (X[:, 1:] - self._means) / self._stds
        
        return X_std
    
    def _calculate_weights(self, n: int) -> np.ndarray:
        """
        Calculate exponential time decay weights.
        w(i) = exp(-λ × (n - i))
        More recent data points get higher weights.
        """
        indices = np.arange(n)
        weights = np.exp(-self.decay_rate * (n - 1 - indices))
        return weights
    
    def _ridge_regression(self, X: np.ndarray, y: np.ndarray, 
                          weights: np.ndarray) -> np.ndarray:
        """
        Weighted Ridge Regression using closed-form solution.
        β = (X'WX + αI)^(-1) X'Wy
        """
        n_features = X.shape[1]
        
        # Weight matrix (diagonal)
        W = np.diag(weights)
        
        # Regularization matrix (don't regularize bias)
        I = np.eye(n_features)
        I[0, 0] = 0  # Don't regularize bias term
        
        # Compute X'WX + αI
        XtWX = X.T @ W @ X + self.alpha * I
        
        # Compute X'Wy
        XtWy = X.T @ W @ y
        
        # Solve using matrix inversion
        try:
            beta = np.linalg.solve(XtWX, XtWy)
        except np.linalg.LinAlgError:
            # Fallback to pseudo-inverse if matrix is singular
            beta = np.linalg.pinv(XtWX) @ XtWy
        
        return beta
    
    def _calculate_r_squared(self, y_true: np.ndarray, y_pred: np.ndarray,
                             weights: np.ndarray) -> float:
        """
        Calculate weighted R² (coefficient of determination).
        R² = 1 - SSE/SST
        """
        # Weighted mean
        y_mean = np.average(y_true, weights=weights)
        
        # Sum of Squared Errors (weighted)
        sse = np.sum(weights * (y_true - y_pred) ** 2)
        
        # Total Sum of Squares (weighted)
        sst = np.sum(weights * (y_true - y_mean) ** 2)
        
        if sst == 0:
            return 0.0
        
        r2 = 1 - (sse / sst)
        return max(0, min(1, r2))  # Clamp to [0, 1]
    
    def predict(self, ohlc_data: List[dict]) -> Optional[PredictionResult]:
        """
        Predict the next close price using weighted ridge regression.
        
        Args:
            ohlc_data: List of OHLC dictionaries with keys:
                       'open', 'high', 'low', 'close', 'volume'
        
        Returns:
            PredictionResult with predicted price, confidence, and coefficients
        """
        if len(ohlc_data) < 10:
            return None
        
        # Use lookback period
        data = ohlc_data[-self.lookback:] if len(ohlc_data) > self.lookback else ohlc_data
        n = len(data)
        
        # Extract arrays
        opens = np.array([d.get('open', d.get('Open', 0)) for d in data], dtype=float)
        highs = np.array([d.get('high', d.get('High', 0)) for d in data], dtype=float)
        lows = np.array([d.get('low', d.get('Low', 0)) for d in data], dtype=float)
        closes = np.array([d.get('close', d.get('Close', 0)) for d in data], dtype=float)
        volumes = np.array([d.get('volume', d.get('Volume', 0)) for d in data], dtype=float)
        
        # Build features
        X = self._build_features(closes, volumes, highs, lows)
        
        # Target: next close (shifted by 1)
        y = closes[1:]  # y[i] = close[i+1]
        X_train = X[:-1]  # X[i] predicts y[i]
        
        if len(y) < 5:
            return None
        
        # Standardize
        X_std = self._standardize(X_train, fit=True)
        
        # Calculate weights
        weights = self._calculate_weights(len(y))
        
        # Fit ridge regression
        self._coefficients = self._ridge_regression(X_std, y, weights)
        
        # Predictions on training set
        y_pred_train = X_std @ self._coefficients
        
        # Calculate R²
        r_squared = self._calculate_r_squared(y, y_pred_train, weights)
        
        # Predict next close using latest data point
        X_latest = X[-1:].copy()
        X_latest_std = self._standardize(X_latest, fit=False)
        predicted_close = float(X_latest_std @ self._coefficients)
        
        return PredictionResult(
            predictedClose=predicted_close,
            rSquared=r_squared,
            modelType="Weighted Ridge Regression",
            featureNames=self.feature_names,
            coefficients=self._coefficients.tolist()
        )
    
    def predict_from_ohlc_objects(self, ohlc_list) -> Optional[PredictionResult]:
        """
        Predict using OHLC dataclass objects.
        
        Args:
            ohlc_list: List of OHLC objects
        
        Returns:
            PredictionResult
        """
        data = [
            {
                'open': o.open,
                'high': o.high,
                'low': o.low,
                'close': o.close,
                'volume': o.volume
            }
            for o in ohlc_list
        ]
        return self.predict(data)


def perform_regression_analysis(history: List) -> Optional[PredictionResult]:
    """
    Convenience function matching React's performRegressionAnalysis.
    
    Args:
        history: List of OHLC data (dicts or objects)
    
    Returns:
        PredictionResult with predicted close, R², and model details
    """
    predictor = PricePredictor()
    
    # Handle both dict and object formats
    if history and hasattr(history[0], 'close'):
        return predictor.predict_from_ohlc_objects(history)
    else:
        return predictor.predict(history)


# Main test
if __name__ == "__main__":
    # Test with sample data
    import random
    
    # Generate sample OHLC data
    sample_data = []
    base_price = 2500
    
    for i in range(100):
        open_price = base_price + random.uniform(-5, 5)
        high = open_price + random.uniform(0, 10)
        low = open_price - random.uniform(0, 10)
        close = random.uniform(low, high)
        volume = random.uniform(100000, 500000)
        
        sample_data.append({
            'open': open_price,
            'high': high,
            'low': low,
            'close': close,
            'volume': volume
        })
        base_price = close
    
    # Run prediction
    result = perform_regression_analysis(sample_data)
    
    if result:
        print("=" * 50)
        print("Price Prediction Result")
        print("=" * 50)
        print(f"Predicted Close: {result.predictedClose:.2f}")
        print(f"R² Confidence: {result.rSquared:.2%}")
        print(f"Model Type: {result.modelType}")
        print("\nFeature Coefficients:")
        for name, coef in zip(result.featureNames, result.coefficients):
            print(f"  {name}: {coef:.4f}")
    else:
        print("Prediction failed - insufficient data")
