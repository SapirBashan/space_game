"""Data validation structures and rules for radar measurement matrices.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import numpy as np


@dataclass
class ValidationReport:
    """Report detailing validation status, dimensions, and anomalies found."""
    is_valid: bool
    filename: str
    detected_elements: int
    detected_frequencies: int
    data_type: str
    has_element_column: bool
    is_combined_format: bool
    missing_count: int = 0
    non_finite_count: int = 0
    duplicate_elements: List[int] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    @property
    def summary_message(self) -> str:
        if not self.is_valid:
            return f"Invalid file '{self.filename}': " + "; ".join(self.errors)
        status = f"Valid ({self.detected_elements} elements x {self.detected_frequencies} freqs)"
        if self.warnings:
            status += f" with {len(self.warnings)} warning(s)"
        return status


def validate_matrix(matrix: np.ndarray, filename: str = "matrix") -> ValidationReport:
    """Validate a 2D numpy array of measurements."""
    errors = []
    warnings = []
    
    if matrix.ndim != 2:
        errors.append(f"Expected 2D array, got {matrix.ndim}D with shape {matrix.shape}")
        return ValidationReport(
            is_valid=False,
            filename=filename,
            detected_elements=0,
            detected_frequencies=0,
            data_type="UNKNOWN",
            has_element_column=False,
            is_combined_format=False,
            errors=errors,
        )

    rows, cols = matrix.shape
    nan_count = int(np.isnan(matrix).sum())
    inf_count = int(np.isinf(matrix).sum())
    non_finite_count = nan_count + inf_count

    if non_finite_count > 0:
        warnings.append(f"Contains {non_finite_count} non-finite/missing measurement(s)")

    if rows != 256:
        warnings.append(f"Non-standard element row count: {rows} (expected 256)")
    if cols != 64:
        warnings.append(f"Non-standard frequency column count: {cols} (expected 64)")

    return ValidationReport(
        is_valid=len(errors) == 0,
        filename=filename,
        detected_elements=rows,
        detected_frequencies=cols,
        data_type="UNKNOWN",
        has_element_column=False,
        is_combined_format=False,
        missing_count=nan_count,
        non_finite_count=non_finite_count,
        errors=errors,
        warnings=warnings,
    )
