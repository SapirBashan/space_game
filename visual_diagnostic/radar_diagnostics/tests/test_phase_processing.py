"""Automated unit tests for phase conversion, wrapping, and circular statistics.
"""

import numpy as np
import pytest

from app.core.phase_processing import (
    circular_diff_deg,
    circular_mean_deg,
    circular_std_deg,
    deg_to_rad,
    rad_to_deg,
    unwrap_phase_deg,
    wrap_deg_180,
    wrap_rad_pi,
)


def test_radians_to_degrees_conversion():
    """Verify correct conversion of standard radian values to degrees."""
    assert np.isclose(rad_to_deg(0.0), 0.0)
    assert np.isclose(rad_to_deg(np.pi / 2.0), 90.0)
    assert np.isclose(rad_to_deg(np.pi), 180.0)
    assert np.isclose(rad_to_deg(-np.pi / 2.0), -90.0)
    assert np.isclose(rad_to_deg(-np.pi), -180.0)


def test_degree_wrapping():
    """Verify wrapping to [-180, 180) degrees."""
    assert np.isclose(wrap_deg_180(180.0), -180.0)
    assert np.isclose(wrap_deg_180(190.0), -170.0)
    assert np.isclose(wrap_deg_180(-190.0), 170.0)
    assert np.isclose(wrap_deg_180(360.0), 0.0)
    assert np.isclose(wrap_deg_180(-360.0), 0.0)
    assert np.isclose(wrap_deg_180(0.0), 0.0)


def test_circular_phase_difference():
    """Verify circular difference around boundary: 179 deg and -179 deg are 2 deg apart."""
    # 179 - (-179) = 358 -> shortest signed is -2 deg
    diff1 = circular_diff_deg(179.0, -179.0)
    assert np.isclose(diff1, -2.0)

    # -179 - 179 = -358 -> shortest signed is +2 deg
    diff2 = circular_diff_deg(-179.0, 179.0)
    assert np.isclose(diff2, 2.0)

    # 10 - 20 = -10
    assert np.isclose(circular_diff_deg(10.0, 20.0), -10.0)


def test_circular_mean():
    """Verify circular mean near wrapping boundary."""
    # The arithmetic mean of [179, -179] would be 0, which is completely wrong!
    # The circular mean of [179, -179] must be 180 (or -180).
    angles = np.array([179.0, -179.0])
    c_mean = circular_mean_deg(angles)
    assert np.isclose(np.abs(c_mean), 180.0)

    # Angles clustered around 45 deg
    angles2 = np.array([44.0, 46.0, 45.0])
    assert np.isclose(circular_mean_deg(angles2), 45.0)


def test_circular_std():
    """Verify circular standard deviation does not artificially blow up across wrapping boundary."""
    # Cluster near 180 deg
    angles = np.array([178.0, 179.0, -179.0, -178.0])
    c_std = circular_std_deg(angles)
    # Circular std should be small (~2-3 degrees)
    assert c_std < 5.0


def test_phase_unwrapping():
    """Verify phase unwrapping removes artificial 2*pi / 360 deg jumps."""
    # A smooth phase slope that wrapped: 160, 175, -170, -155
    wrapped_deg = np.array([[160.0, 175.0, -170.0, -155.0]])
    unwrapped = unwrap_phase_deg(wrapped_deg, axis=1)
    
    # After unwrapping, consecutive steps should be ~ +15 degrees monotonically increasing
    diffs = np.diff(unwrapped[0, :])
    assert np.all(np.isclose(diffs, 15.0, atol=1e-3))
