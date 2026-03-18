from __future__ import annotations
from dataclasses import dataclass, field
from clinical_nlp.schemas.input import VitalSigns
from .thresholds import VITAL_THRESHOLDS


@dataclass
class VitalsScore:
    total_points: int = 0
    flagged_fields: list[tuple[str, float, int, str]] = field(default_factory=list)
    # (field_name, value, points, reason)


def score_vitals(vitals: VitalSigns | None) -> VitalsScore:
    result = VitalsScore()
    if vitals is None:
        return result

    vitals_dict = vitals.model_dump()

    # Score HR, SpO2, RR via the PE thresholds table (first match wins)
    for field_name, thresholds in VITAL_THRESHOLDS.items():
        value = vitals_dict.get(field_name)
        if value is None:
            continue
        for predicate, points, reason in thresholds:
            if predicate(value):
                result.total_points += points
                result.flagged_fields.append((field_name, value, points, reason))
                break

    # Hypotension — treated as a single PE feature.
    # Flag once if systolic ≤ 90 OR diastolic ≤ 60; never count both.
    systolic = vitals_dict.get("systolic_bp")
    diastolic = vitals_dict.get("diastolic_bp")
    hypotensive = (
        (systolic is not None and systolic <= 90)
        or (diastolic is not None and diastolic <= 60)
    )
    if hypotensive:
        if systolic is not None and diastolic is not None:
            display_val = float(systolic)
            reason = (
                f"Hypotension (BP {int(systolic)}/{int(diastolic)} mmHg"
                f" ≤ 90/60 — PE risk marker)"
            )
        elif systolic is not None:
            display_val = float(systolic)
            reason = (
                f"Hypotension (systolic {int(systolic)} mmHg"
                f" ≤ 90 — PE risk marker)"
            )
        else:
            display_val = float(diastolic)  # type: ignore[arg-type]
            reason = (
                f"Hypotension (diastolic {int(diastolic)} mmHg"  # type: ignore[arg-type]
                f" ≤ 60 — PE risk marker)"
            )
        result.total_points += 1
        result.flagged_fields.append(("bp", display_val, 1, reason))

    # temperature and gcs: present in the data model, not scored for PE.
    return result
