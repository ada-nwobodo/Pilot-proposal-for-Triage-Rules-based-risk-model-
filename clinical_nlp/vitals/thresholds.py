"""PE-specific vital sign thresholds.

Only the four PE-relevant vital parameters are scored here.
Heart rate, SpO2, and respiratory rate each have a single threshold.
Blood pressure (hypotension) is handled as a single combined feature
in scorer.py to avoid double-counting systolic and diastolic.

Temperature and GCS are retained in the VitalSigns data model but
are intentionally excluded from PE risk scoring.
"""
from __future__ import annotations
from typing import Callable

ThresholdEntry = tuple[Callable[[float], bool], int, str]

VITAL_THRESHOLDS: dict[str, list[ThresholdEntry]] = {
    "heart_rate": [
        (lambda v: v > 100, 1, "Tachycardia (HR > 100 — PE risk marker)"),
    ],
    "spo2": [
        (lambda v: v <= 93, 1, "Hypoxia (SpO2 ≤ 93% — PE risk marker)"),
    ],
    "respiratory_rate": [
        (lambda v: v >= 22, 1, "Tachypnoea (RR ≥ 22 — PE risk marker)"),
    ],
    # systolic_bp and diastolic_bp are handled together in scorer.py
    # temperature and gcs are not scored for PE
}
