"""Single source of truth for all vital signs thresholds.

Each entry is (predicate, points, reason_string).
Thresholds are evaluated in order — first match wins per vital.
"""
from __future__ import annotations
from typing import Callable

ThresholdEntry = tuple[Callable[[float], bool], int, str]

VITAL_THRESHOLDS: dict[str, list[ThresholdEntry]] = {
    "heart_rate": [
        (lambda v: v < 40 or v > 130, 3, "HR severely abnormal"),
        (lambda v: v < 50 or v > 110, 2, "HR moderately abnormal"),
        (lambda v: v < 60 or v > 100, 1, "HR mildly abnormal"),
    ],
    "systolic_bp": [
        (lambda v: v < 70, 3, "BP critically low"),
        (lambda v: v < 80, 2, "BP severely low"),
        (lambda v: v < 90 or v > 180, 1, "BP abnormal"),
    ],
    "respiratory_rate": [
        (lambda v: v < 8 or v > 25, 3, "RR severely abnormal"),
        (lambda v: v < 10 or v > 20, 2, "RR moderately abnormal"),
    ],
    "spo2": [
        (lambda v: v < 85, 3, "SpO2 critically low"),
        (lambda v: v < 90, 2, "SpO2 severely low"),
        (lambda v: v < 94, 1, "SpO2 low"),
    ],
    "temperature": [
        (lambda v: v < 35 or v > 39.5, 2, "Temperature severely abnormal"),
        (lambda v: v < 36 or v > 38.5, 1, "Temperature mildly abnormal"),
    ],
    "gcs": [
        (lambda v: v < 9, 3, "GCS severely reduced"),
        (lambda v: v < 12, 2, "GCS moderately reduced"),
        (lambda v: v < 14, 1, "GCS mildly reduced"),
    ],
}
