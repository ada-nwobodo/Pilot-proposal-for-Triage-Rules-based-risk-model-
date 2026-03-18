from clinical_nlp.schemas.input import VitalSigns
from clinical_nlp.vitals.scorer import score_vitals


def test_normal_vitals_score_zero():
    vitals = VitalSigns(
        heart_rate=75, systolic_bp=120, diastolic_bp=80,
        respiratory_rate=16, spo2=98, temperature=37.0, gcs=15,
    )
    score = score_vitals(vitals)
    assert score.total_points == 0
    assert score.flagged_fields == []


def test_tachycardia_flagged():
    vitals = VitalSigns(heart_rate=105)
    score = score_vitals(vitals)
    assert score.total_points == 1
    assert any("Tachycardia" in r for _, _, _, r in score.flagged_fields)


def test_heart_rate_exactly_100_not_flagged():
    # Threshold is > 100, so HR=100 should NOT be flagged
    vitals = VitalSigns(heart_rate=100)
    score = score_vitals(vitals)
    assert score.total_points == 0


def test_hypoxia_flagged():
    vitals = VitalSigns(spo2=93)
    score = score_vitals(vitals)
    assert score.total_points == 1
    assert any("Hypoxia" in r for _, _, _, r in score.flagged_fields)


def test_spo2_94_not_flagged():
    # Threshold is <= 93, so SpO2=94 should NOT be flagged
    vitals = VitalSigns(spo2=94)
    score = score_vitals(vitals)
    assert score.total_points == 0


def test_tachypnoea_flagged():
    vitals = VitalSigns(respiratory_rate=22)
    score = score_vitals(vitals)
    assert score.total_points == 1
    assert any("Tachypnoea" in r for _, _, _, r in score.flagged_fields)


def test_hypotension_systolic_only():
    vitals = VitalSigns(systolic_bp=88)
    score = score_vitals(vitals)
    assert score.total_points == 1
    assert any("Hypotension" in r for _, _, _, r in score.flagged_fields)


def test_hypotension_diastolic_only():
    vitals = VitalSigns(diastolic_bp=58)
    score = score_vitals(vitals)
    assert score.total_points == 1
    assert any("Hypotension" in r for _, _, _, r in score.flagged_fields)


def test_hypotension_both_counted_once():
    # Systolic ≤ 90 AND diastolic ≤ 60 — must only flag once
    vitals = VitalSigns(systolic_bp=85, diastolic_bp=55)
    score = score_vitals(vitals)
    bp_flags = [f for f in score.flagged_fields if f[0] == "bp"]
    assert len(bp_flags) == 1, "Hypotension must only be counted once"
    assert score.total_points == 1


def test_multiple_pe_vitals_abnormal():
    vitals = VitalSigns(heart_rate=115, systolic_bp=85, spo2=90, respiratory_rate=24)
    score = score_vitals(vitals)
    # Tachycardia (1) + Hypotension (1) + Hypoxia (1) + Tachypnoea (1) = 4
    assert score.total_points == 4


def test_temperature_and_gcs_not_scored():
    # Temperature and GCS are in the model but must not contribute to PE score
    vitals = VitalSigns(temperature=39.5, gcs=8)
    score = score_vitals(vitals)
    assert score.total_points == 0
    assert score.flagged_fields == []


def test_none_vitals():
    score = score_vitals(None)
    assert score.total_points == 0
