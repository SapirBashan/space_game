"""Phase processing algorithms including conversions, wrapping, unwrapping,
and circular statistics.
"""

from typing import Union
import numpy as np


def rad_to_deg(radians: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Convert radians to degrees."""
    return np.asarray(radians) * (180.0 / np.pi)


def deg_to_rad(degrees: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Convert degrees to radians."""
    return np.asarray(degrees) * (np.pi / 180.0)


def wrap_deg_180(degrees: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Wrap degrees into the half-open interval [-180, 180)."""
    deg = np.asarray(degrees)
    return (deg + 180.0) % 360.0 - 180.0


def wrap_rad_pi(radians: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Wrap radians into the half-open interval [-pi, pi)."""
    rad = np.asarray(radians)
    return (rad + np.pi) % (2.0 * np.pi) - np.pi


def unwrap_phase_deg(degrees: np.ndarray, axis: int = 1) -> np.ndarray:
    """Unwrap phase in degrees along the specified axis (default: axis 1 = frequencies)."""
    rad = deg_to_rad(degrees)
    unwrapped_rad = np.unwrap(rad, axis=axis)
    return rad_to_deg(unwrapped_rad)


def circular_diff_deg(a: Union[float, np.ndarray], b: Union[float, np.ndarray]) -> Union[float, np.ndarray]:
    """Compute the shortest signed circular angular difference: a - b in [-180, 180).
    
    Example: 179° - (-179°) = -2° (shortest path), not +358°.
    """
    diff = np.asarray(a) - np.asarray(b)
    return (diff + 180.0) % 360.0 - 180.0


def circular_mean_deg(degrees: np.ndarray, axis: int = None) -> Union[float, np.ndarray]:
    """Compute the circular mean of an array of angles in degrees."""
    rad = deg_to_rad(degrees)
    sin_sum = np.nanmean(np.sin(rad), axis=axis)
    cos_sum = np.nanmean(np.cos(rad), axis=axis)
    mean_rad = np.arctan2(sin_sum, cos_sum)
    return rad_to_deg(mean_rad)


def circular_std_deg(degrees: np.ndarray, axis: int = None) -> Union[float, np.ndarray]:
    """Compute the circular standard deviation of an array of angles in degrees.
    
    Uses the angular deviation metric: sqrt(2 * (1 - R)) * 180 / pi,
    where R is the mean resultant length.
    """
    rad = deg_to_rad(degrees)
    sin_mean = np.nanmean(np.sin(rad), axis=axis)
    cos_mean = np.nanmean(np.cos(rad), axis=axis)
    R = np.sqrt(sin_mean**2 + cos_mean**2)
    R = np.clip(R, 0.0, 1.0)
    
    # Angular deviation formula
    circ_disp = np.sqrt(np.maximum(0.0, 2.0 * (1.0 - R)))
    return rad_to_deg(circ_disp)
