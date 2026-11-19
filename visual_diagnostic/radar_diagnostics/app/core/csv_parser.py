"""Robust CSV Parser for radar PSP measurement files.

Supports:
- Raw numerical matrix files (256 rows x 64 columns, without headers or element columns)
- Standard element + frequency layout (Element, A, B, ..., BL)
- Matrix-only files without element column
- Combined multi-test CSV format (TestID, Element, A, B, ..., BL)
- ZIP archive unpacking and parsing
- Automatic and override data type detection (AMP, NOISE, PHASE)
- Safe handling of non-finite or missing values
"""

import io
import os
import re
import zipfile
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Union
import numpy as np
import pandas as pd

from app.config import generate_frequency_labels
from app.core.data_validator import ValidationReport
from app.models.radar_frame import RadarFrame


def detect_data_type_from_name(name: str) -> str:
    """Infer data type (AMP, NOISE, PHASE) from filename or string."""
    upper = name.upper()
    if "NOISE" in upper:
        return "NOISE"
    elif "PHASE" in upper:
        return "PHASE"
    elif "AMP" in upper:
        return "AMP"
    return "AMP"  # Default fallback


def _detect_has_header(first_line: str) -> bool:
    """Determine whether the first row is a text header or numeric data row."""
    tokens = [t.strip() for t in first_line.split(",") if t.strip()]
    if not tokens:
        return True
    num_count = 0
    for tok in tokens[:8]:
        try:
            float(tok)
            num_count += 1
        except ValueError:
            pass
    # If majority of first tokens are valid floating-point numbers, it's pure data
    if len(tokens) >= 2 and num_count >= min(len(tokens), 3):
        return False
    return True


def parse_csv_content(
    content_or_path: Union[str, bytes, io.StringIO, io.BytesIO],
    filename: str = "upload.csv",
    explicit_data_type: Optional[str] = None,
    session_id: str = "session_001",
) -> Tuple[List[RadarFrame], ValidationReport]:
    """Parse a CSV file or buffer into one or more RadarFrame objects.
    
    Supports both raw headerless 256x64 matrices and labeled CSV formats.
    """
    errors: List[str] = []
    warnings: List[str] = []
    
    data_type = (explicit_data_type or detect_data_type_from_name(filename)).upper()
    if data_type not in ("AMP", "NOISE", "PHASE"):
        data_type = "AMP"

    unit = "rad" if data_type == "PHASE" else "dB"

    try:
        # Read content to check first line
        if isinstance(content_or_path, (str, os.PathLike)) and os.path.isfile(content_or_path):
            with open(content_or_path, "r", encoding="utf-8", errors="replace") as f:
                first_line = f.readline()
            has_header = _detect_has_header(first_line)
            df = pd.read_csv(content_or_path, header=0 if has_header else None)
        else:
            if isinstance(content_or_path, bytes):
                text_content = content_or_path.decode("utf-8", errors="replace")
            elif isinstance(content_or_path, str):
                text_content = content_or_path
            elif hasattr(content_or_path, "read"):
                raw = content_or_path.read()
                text_content = raw.decode("utf-8", errors="replace") if isinstance(raw, bytes) else raw
            else:
                raise ValueError("Unsupported input format for CSV parsing")

            lines = text_content.strip().splitlines()
            first_line = lines[0] if lines else ""
            has_header = _detect_has_header(first_line)
            df = pd.read_csv(io.StringIO(text_content), header=0 if has_header else None)

    except Exception as e:
        report = ValidationReport(
            is_valid=False,
            filename=filename,
            detected_elements=0,
            detected_frequencies=0,
            data_type=data_type,
            has_element_column=False,
            is_combined_format=False,
            errors=[f"Failed to parse CSV file: {str(e)}"],
        )
        return [], report

    if df.empty:
        report = ValidationReport(
            is_valid=False,
            filename=filename,
            detected_elements=0,
            detected_frequencies=0,
            data_type=data_type,
            has_element_column=False,
            is_combined_format=False,
            errors=["CSV file is empty"],
        )
        return [], report

    # Check for combined format (contains 'TestID' or 'test_id' column)
    combined_cols = [c for c in df.columns if str(c).strip().lower() in ("testid", "test_id", "test")]
    is_combined = len(combined_cols) > 0

    if is_combined:
        test_col = combined_cols[0]
        grouped = df.groupby(test_col)
        frames: List[RadarFrame] = []
        overall_valid = True
        total_rows = 0
        total_cols = 0
        all_warnings: List[str] = []
        
        for seq_idx, (test_name, sub_df) in enumerate(grouped, start=1):
            sub_df_clean = sub_df.drop(columns=[test_col])
            sub_frames, sub_report = _parse_single_test_dataframe(
                sub_df_clean,
                filename=f"{filename}_{test_name}",
                test_id=str(test_name),
                seq_num=seq_idx,
                data_type=data_type,
                unit=unit,
                session_id=session_id,
            )
            frames.extend(sub_frames)
            if not sub_report.is_valid:
                overall_valid = False
                errors.extend(sub_report.errors)
            all_warnings.extend(sub_report.warnings)
            total_rows = sub_report.detected_elements
            total_cols = sub_report.detected_frequencies

        report = ValidationReport(
            is_valid=overall_valid and len(frames) > 0,
            filename=filename,
            detected_elements=total_rows,
            detected_frequencies=total_cols,
            data_type=data_type,
            has_element_column=True,
            is_combined_format=True,
            errors=errors,
            warnings=all_warnings,
        )
        return frames, report

    # Single test CSV
    test_id = os.path.splitext(os.path.basename(filename))[0]

    return _parse_single_test_dataframe(
        df,
        filename=filename,
        test_id=test_id,
        seq_num=1,
        data_type=data_type,
        unit=unit,
        session_id=session_id,
    )


def _parse_single_test_dataframe(
    df: pd.DataFrame,
    filename: str,
    test_id: str,
    seq_num: int,
    data_type: str,
    unit: str,
    session_id: str,
) -> Tuple[List[RadarFrame], ValidationReport]:
    errors: List[str] = []
    warnings: List[str] = []

    # Check if df has numeric column names (indicating raw headerless CSV)
    cols_are_numeric = all(isinstance(c, int) for c in df.columns) or all(str(c).isdigit() for c in df.columns)

    if cols_are_numeric:
        num_cols = len(df.columns)
        if num_cols == 65:
            # 65 columns: first column is element index
            try:
                element_ids = df.iloc[:, 0].astype(int).tolist()
            except Exception:
                element_ids = list(range(1, len(df) + 1))
            freq_df = df.iloc[:, 1:]
            freq_labels = generate_frequency_labels(64)
            freq_df.columns = freq_labels
            has_element_col = True
            duplicates = []
        else:
            # Pure 64 frequency matrix without element column
            element_ids = list(range(1, len(df) + 1))
            freq_df = df
            freq_labels = generate_frequency_labels(num_cols)
            freq_df.columns = freq_labels
            has_element_col = False
            duplicates = []
    else:
        # Check for explicit Element index column
        element_cols = [c for c in df.columns if str(c).strip().lower() in ("element", "elem", "element_id", "el")]
        has_element_col = len(element_cols) > 0

        if has_element_col:
            elem_col = element_cols[0]
            try:
                element_ids = df[elem_col].astype(int).tolist()
            except Exception:
                element_ids = list(range(1, len(df) + 1))
                warnings.append(f"Could not parse '{elem_col}' as integers; sequential indices 1..{len(df)} used.")
            
            duplicates = [x for x in set(element_ids) if element_ids.count(x) > 1]
            if duplicates:
                warnings.append(f"Found {len(duplicates)} duplicate element identifier(s): {duplicates[:5]}...")
                
            freq_df = df.drop(columns=[elem_col])
        else:
            element_ids = list(range(1, len(df) + 1))
            duplicates = []
            freq_df = df

        freq_labels = [str(c).strip() for c in freq_df.columns]

    # Convert values to numeric matrix
    try:
        matrix = freq_df.apply(pd.to_numeric, errors="coerce").to_numpy(dtype=np.float64)
    except Exception as e:
        errors.append(f"Failed to convert matrix data to numeric values: {str(e)}")
        report = ValidationReport(
            is_valid=False,
            filename=filename,
            detected_elements=len(df),
            detected_frequencies=len(freq_labels),
            data_type=data_type,
            has_element_column=has_element_col,
            is_combined_format=False,
            errors=errors,
        )
        return [], report

    nan_count = int(np.isnan(matrix).sum())
    inf_count = int(np.isinf(matrix).sum())
    non_finite = nan_count + inf_count

    if non_finite > 0:
        warnings.append(f"Matrix contains {non_finite} non-finite/missing value(s). Replaced with NaN.")

    rows, cols = matrix.shape
    if rows != 256:
        warnings.append(f"Non-standard elements count: {rows} (standard is 256)")
    if cols != 64:
        warnings.append(f"Non-standard frequencies count: {cols} (standard is 64)")

    # Construct RadarFrame
    frame = RadarFrame(
        timestamp=datetime.now(timezone.utc).isoformat(),
        sequence_number=seq_num,
        session_id=session_id,
        test_id=test_id,
        data_type=data_type,
        unit=unit,
        element_ids=element_ids,
        frequency_labels=freq_labels,
        matrix=matrix,
        metadata={"filename": filename, "source": "csv_import"},
    )

    report = ValidationReport(
        is_valid=len(errors) == 0,
        filename=filename,
        detected_elements=rows,
        detected_frequencies=cols,
        data_type=data_type,
        has_element_column=has_element_col,
        is_combined_format=False,
        missing_count=nan_count,
        non_finite_count=non_finite,
        duplicate_elements=duplicates,
        errors=errors,
        warnings=warnings,
    )
    return [frame], report


def parse_zip_archive(
    zip_bytes_or_path: Union[bytes, io.BytesIO, str],
    explicit_data_type: Optional[str] = None,
    session_id: str = "session_001",
) -> Tuple[List[RadarFrame], List[ValidationReport]]:
    """Safely unpack and parse all CSV files contained within a ZIP archive."""
    frames: List[RadarFrame] = []
    reports: List[ValidationReport] = []

    if isinstance(zip_bytes_or_path, (str, os.PathLike)):
        zf = zipfile.ZipFile(zip_bytes_or_path, "r")
    elif isinstance(zip_bytes_or_path, bytes):
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes_or_path), "r")
    else:
        zf = zipfile.ZipFile(zip_bytes_or_path, "r")

    with zf:
        csv_members = [
            m for m in zf.infolist()
            if not m.is_dir()
            and m.filename.lower().endswith(".csv")
            and not os.path.basename(m.filename).startswith(".")
            and not "MACOSX" in m.filename
        ]
        csv_members.sort(key=lambda m: m.filename)

        for member in csv_members:
            clean_name = os.path.basename(member.filename)
            with zf.open(member) as f:
                content = f.read()
                sub_frames, report = parse_csv_content(
                    content,
                    filename=clean_name,
                    explicit_data_type=explicit_data_type,
                    session_id=session_id,
                )
                frames.extend(sub_frames)
                reports.append(report)

    return frames, reports


def export_frame_to_csv(
    frame: RadarFrame,
    filepath_or_buffer: Union[str, io.StringIO],
    include_element_col: bool = False,
    include_header: bool = False,
) -> None:
    """Save a RadarFrame to CSV.
    
    By default, writes a pure 256x64 numerical matrix (no header row, no element column),
    matching raw laboratory radar test exports.
    """
    df_data = {}
    if include_element_col:
        df_data["Element"] = frame.element_ids

    for j, col_label in enumerate(frame.frequency_labels):
        col_key = col_label if include_header else j
        df_data[col_key] = np.round(frame.matrix[:, j], 2)

    df = pd.DataFrame(df_data)
    df.to_csv(filepath_or_buffer, index=False, header=include_header)
