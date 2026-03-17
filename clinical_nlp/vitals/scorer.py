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

    for field_name, thresholds in VITAL_THRESHOLDS.items():
        value = vitals_dict.get(field_name)
        if value is None:
            continue
        for predicate, points, reason in thresholds:
            if predicate(value):
                result.total_points += points
                result.flagged_fields.append((field_name, value, points, reason))
                break  # first match wins

    return result
