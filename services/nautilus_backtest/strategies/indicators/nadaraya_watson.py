"""
Nadaraya-Watson Kernel Regression Bands
"""
import numpy as np
import logging

logger = logging.getLogger(__name__)


class NadarayaWatsonBands:
    """
    Nadaraya-Watson kernel regression with bands

    Uses Gaussian kernel for smooth price estimation
    """

    def __init__(self, bandwidth: float = 20.0, num_std: float = 2.0):
        """
        Initialize NW bands

        Args:
            bandwidth: Kernel bandwidth (higher = smoother)
            num_std: Number of standard deviations for bands
        """
        self.bandwidth = bandwidth
        self.num_std = num_std

    def calculate(self, x: np.ndarray, y: np.ndarray):
        """
        Calculate Nadaraya-Watson estimator and bands

        Args:
            x: Time indices
            y: Price values

        Returns:
            Tuple of (center, upper_band, lower_band)
        """
        n = len(x)
        y_hat = np.zeros(n)

        # Gaussian kernel
        def gaussian_kernel(u):
            return np.exp(-0.5 * u ** 2) / np.sqrt(2 * np.pi)

        # Calculate kernel regression
        for i in range(n):
            # Calculate kernel weights
            u = (x - x[i]) / self.bandwidth
            weights = gaussian_kernel(u)
            weight_sum = np.sum(weights)

            if weight_sum > 0:
                y_hat[i] = np.sum(weights * y) / weight_sum
            else:
                y_hat[i] = y[i]

        # Calculate residuals and standard deviation
        residuals = y - y_hat
        std_dev = np.std(residuals)

        # Calculate bands
        upper_band = y_hat + self.num_std * std_dev
        lower_band = y_hat - self.num_std * std_dev

        return y_hat, upper_band, lower_band