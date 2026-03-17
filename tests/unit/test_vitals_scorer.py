from clinical_nlp.schemas.input import VitalSigns
from clinical_nlp.vitals.scorer import score_vitals


def test_normal_vitals_score_zero():
    vitals = VitalSigns(
        heart_rate=75, systolic_bp=120, diastolic_bp=80,
        respiratory_rate=16, spo2=98, temperature=37.0, gcs=15
    )
    score = score_vitals(vitals)
    assert score.total_points == 0
    assert score.flagged_fields == []


def test_critically_low_spo2():
    vitals = VitalSigns(spo2=82)
    score = score_vitals(vitals)
    assert score.total_points == 3
    assert any("SpO2 critically low" in r for _, _, _, r in score.flagged_fields)


def test_multiple_abnormal_vitals():
    vitals = VitalSigns(heart_rate=135, systolic_bp=78, spo2=88)
    score = score_vitals(vitals)
    assert score.total_points >= 5


def test_none_vitals():
    score = score_vitals(None)
    assert score.total_points == 0


def test_partial_vitals():
    vitals = VitalSigns(heart_rate=50)
    score = score_vitals(vitals)
    assert score.total_points >= 1
