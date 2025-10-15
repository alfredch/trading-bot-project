"""
Support and Resistance Level Detection
"""
import numpy as np
from typing import List, Tuple
from sklearn.cluster import AgglomerativeClustering
import logging

logger = logging.getLogger(__name__)


class SupportResistanceLevels:
    """
    Detect support and resistance levels using clustering
    """

    def __init__(self, lookback: int = 100, n_clusters: int = 5, tolerance: float = 0.02):
        """
        Initialize S/R detector

        Args:
            lookback: Lookback period for pivot detection
            n_clusters: Number of S/R levels to find
            tolerance: Tolerance for level proximity
        """
        self.lookback = lookback
        self.n_clusters = n_clusters
        self.tolerance = tolerance

    def detect(self, highs: List[float], lows: List[float]) -> Tuple[List[float], List[float]]:
        """
        Detect support and resistance levels

        Args:
            highs: High prices
            lows: Low prices

        Returns:
            Tuple of (support_levels, resistance_levels)
        """
        # Find pivot points
        pivot_highs, pivot_lows = self._find_pivots(highs, lows)

        if not pivot_highs and not pivot_lows:
            return [], []

        # Cluster pivots
        all_pivots = pivot_highs + pivot_lows
        levels = self._cluster_levels(all_pivots)

        # Separate into support and resistance
        current_price = (highs[-1] + lows[-1]) / 2
        support = [l for l in levels if l < current_price]
        resistance = [l for l in levels if l > current_price]

        return sorted(support), sorted(resistance)

    def _find_pivots(self, highs: List[float], lows: List[float], window: int = 5) -> Tuple[List[float], List[float]]:
        """Find local maxima and minima"""
        pivot_highs = []
        pivot_lows = []

        for i in range(window, len(highs) - window):
            # Check for pivot high
            if highs[i] == max(highs[i - window:i + window + 1]):
                pivot_highs.append(highs[i])

            # Check for pivot low
            if lows[i] == min(lows[i - window:i + window + 1]):
                pivot_lows.append(lows[i])

        return pivot_highs, pivot_lows

    def _cluster_levels(self, prices: List[float]) -> List[float]:
        """Cluster pivot points into S/R levels"""
        if len(prices) < self.n_clusters:
            return prices

        prices_array = np.array(prices).reshape(-1, 1)

        # Cluster using Agglomerative Clustering
        clustering = AgglomerativeClustering(
            n_clusters=self.n_clusters,
            linkage='ward'
        )
        clustering.fit(prices_array)

        # Calculate cluster centers
        levels = []
        for i in range(self.n_clusters):
            cluster_prices = prices_array[clustering.labels_ == i]
            if len(cluster_prices) > 0:
                levels.append(np.mean(cluster_prices))

        return sorted(levels)