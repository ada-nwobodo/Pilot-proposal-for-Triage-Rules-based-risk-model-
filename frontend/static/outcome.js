/* ============================================================
   PE Triage NLP Engine — Outcome recording page
   frontend/static/outcome.js
   ============================================================ */

'use strict';

// ── Runtime config ─────────────────────────────────────────────────────────────
const BACKEND_URL = 'https://pilot-backend-zeta.vercel.app';
const API_BASE = window.location.hostname === 'pilot-frontend.vercel.app'
  ? BACKEND_URL
  : '';

// ── DOM references ─────────────────────────────────────────────────────────────
const lookupRefInput          = document.getElementById('lookup-ref');
const btnLookup               = document.getElementById('btn-lookup');
const lookupError             = document.getElementById('lookup-error');

const assessmentSummaryCard   = document.getElementById('assessment-summary-card');
const summaryAlreadyRecorded  = document.getElementById('summary-already-recorded');
const existingOutcomeBox      = document.getElementById('existing-outcome-box');

const sumPatientRef           = document.getElementById('sum-patient-ref');
const sumCreatedAt            = document.getElementById('sum-created-at');
const sumClinician            = document.getElementById('sum-clinician');
const sumRiskLevel            = document.getElementById('sum-risk-level');
const sumScore                = document.getElementById('sum-score');
const sumDecision             = document.getElementById('sum-decision');
const sumSuggestedDiagnosis   = document.getElementById('sum-suggested-diagnosis');
const sumOutcome              = document.getElementById('sum-outcome');
const sumConfirmingTest       = document.getElementById('sum-confirming-test');
const sumOutcomeDate          = document.getElementById('sum-outcome-date');
const sumOutcomeRecordedAt    = document.getElementById('sum-outcome-recorded-at');

const outcomeFormCard         = document.getElementById('outcome-form-card');
const outcomeDiagnosisSelect  = document.getElementById('outcome-diagnosis');
const outcomeTestSelect       = document.getElementById('outcome-test');
const outcomeDateInput        = document.getElementById('outcome-date');
const outcomeNotesInput       = document.getElementById('outcome-notes');
const outcomeSubmitError      = document.getElementById('outcome-submit-error');
const btnSubmitOutcome        = document.getElementById('btn-submit-outcome');
const outcomeSavedMsg         = document.getElementById('outcome-saved-msg');

// Clinician feedback buttons
const btnTierAgreedYes  = document.getElementById('btn-tier-agreed-yes');
const btnTierAgreedNo   = document.getElementById('btn-tier-agreed-no');
const btnStepsAgreedYes = document.getElementById('btn-steps-agreed-yes');
const btnStepsAgreedNo  = document.getElementById('btn-steps-agreed-no');

// ── State ──────────────────────────────────────────────────────────────────────
let _assessmentId    = null;   // ID of the fetched assessment row
let _tierAgreed      = null;   // true | false | null — priority tier feedback
let _stepsAgreed     = null;   // true | false | null — next steps feedback

// ── Display helpers ────────────────────────────────────────────────────────────

function showLookupError(msg) {
  lookupError.textContent = msg;
  lookupError.style.display = msg ? 'block' : 'none';
}

function showSubmitError(msg) {
  outcomeSubmitError.textContent = msg;
  outcomeSubmitError.style.display = msg ? 'block' : 'none';
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Label maps ─────────────────────────────────────────────────────────────────

const RISK_LABELS = {
  LOW:      'Low PE Risk',
  MEDIUM:   'Medium PE Risk',
  HIGH:     'High PE Risk',
  CRITICAL: 'Critical PE Risk',
};

const RISK_BADGE_CLASS = {
  LOW:      'risk-badge--low',
  MEDIUM:   'risk-badge--medium',
  HIGH:     'risk-badge--high',
  CRITICAL: 'risk-badge--critical',
};

const DECISION_LABELS = {
  accept: 'Accepted recommendation',
  reject: 'Rejected recommendation',
};

const OUTCOME_LABELS = {
  pe_confirmed:          'PE confirmed',
  pe_excluded:           'PE excluded',
  alternative_diagnosis: 'Alternative diagnosis identified',
  inconclusive:          'Inconclusive / investigations ongoing',
};

const TEST_LABELS = {
  ctpa:               'CTPA',
  vq_scan:            'V/Q scan',
  d_dimer_negative:   'D-dimer (negative)',
  echo:               'Echocardiogram',
  clinical_judgement: 'Clinical judgement',
  other:              'Other',
};

// ── Date formatting ────────────────────────────────────────────────────────────

function formatDatetime(isoString) {
  if (!isoString) return '—';
  try {
    const d = new Date(isoString);
    return d.toLocaleString('en-GB', {
      day: '2-digit', month: 'short', year: 'numeric',
      hour: '2-digit', minute: '2-digit',
    });
  } catch (_) {
    return isoString;
  }
}

function formatDate(isoDate) {
  if (!isoDate) return '—';
  try {
    const [y, m, d] = isoDate.split('-');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${parseInt(d, 10)} ${months[parseInt(m, 10) - 1]} ${y}`;
  } catch (_) {
    return isoDate;
  }
}

// ── Render summary card ────────────────────────────────────────────────────────

function renderSummary(row) {
  sumPatientRef.textContent       = row.patient_ref || '—';
  sumCreatedAt.textContent        = formatDatetime(row.created_at);
  sumClinician.textContent        = row.clinician_name || '—';

  // Risk level as a mini badge
  const riskText = RISK_LABELS[row.risk_level] || row.risk_level || '—';
  const riskCls  = RISK_BADGE_CLASS[row.risk_level] || '';
  sumRiskLevel.innerHTML = `<span class="risk-badge risk-badge--sm ${escapeHtml(riskCls)}">${escapeHtml(riskText)}</span>`;

  sumScore.textContent            = row.score != null ? Number(row.score).toFixed(0) : '—';
  sumDecision.textContent         = DECISION_LABELS[row.decision] || row.decision || '—';
  sumSuggestedDiagnosis.textContent = row.suggested_diagnosis || 'Not suggestive of PE';

  // If an outcome was already recorded, show it
  if (row.outcome) {
    summaryAlreadyRecorded.style.display = 'inline-block';
    existingOutcomeBox.style.display     = 'block';
    sumOutcome.textContent          = OUTCOME_LABELS[row.outcome] || row.outcome;
    sumConfirmingTest.textContent   = TEST_LABELS[row.confirming_test] || row.confirming_test || '—';
    sumOutcomeDate.textContent      = formatDate(row.outcome_date);
    sumOutcomeRecordedAt.textContent = formatDatetime(row.outcome_recorded_at);
  } else {
    summaryAlreadyRecorded.style.display = 'none';
    existingOutcomeBox.style.display     = 'none';
  }

  assessmentSummaryCard.style.display = 'block';
  outcomeFormCard.style.display       = 'block';

  // Reset clinician feedback buttons for fresh lookup
  _tierAgreed  = null;
  _stepsAgreed = null;
  [btnTierAgreedYes, btnTierAgreedNo, btnStepsAgreedYes, btnStepsAgreedNo].forEach(
    btn => { if (btn) btn.className = 'btn btn-feedback'; }
  );
}

// ── Lookup handler ─────────────────────────────────────────────────────────────

btnLookup.addEventListener('click', async () => {
  const ref = lookupRefInput.value.trim();
  showLookupError('');

  if (!ref) {
    showLookupError('Please enter a patient reference number.');
    lookupRefInput.focus();
    return;
  }

  btnLookup.disabled     = true;
  btnLookup.textContent  = 'Looking up…';
  assessmentSummaryCard.style.display = 'none';
  outcomeFormCard.style.display       = 'none';
  outcomeSavedMsg.style.display       = 'none';
  _assessmentId = null;

  try {
    const resp = await fetch(
      `${API_BASE}/decisions/lookup?patient_ref=${encodeURIComponent(ref)}`,
      { headers: { 'Accept': 'application/json' } }
    );

    if (resp.status === 404) {
      showLookupError(`No assessment found for reference "${ref}". Check the reference and try again.`);
      return;
    }
    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    const row = await resp.json();
    _assessmentId = row.id;
    renderSummary(row);

    // Scroll to summary
    assessmentSummaryCard.scrollIntoView({ behavior: 'smooth', block: 'start' });

  } catch (err) {
    showLookupError(`Lookup failed: ${err.message}`);
  } finally {
    btnLookup.disabled    = false;
    btnLookup.textContent = 'Look Up';
  }
});

// Allow Enter key to trigger lookup
lookupRefInput.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') btnLookup.click();
});

// ── Clinician feedback button handlers ────────────────────────────────────────

function selectTierFeedback(agreed) {
  _tierAgreed = agreed;
  if (btnTierAgreedYes) btnTierAgreedYes.className = `btn btn-feedback${agreed  ? ' btn-feedback--active-yes' : ''}`;
  if (btnTierAgreedNo)  btnTierAgreedNo.className  = `btn btn-feedback${!agreed ? ' btn-feedback--active-no'  : ''}`;
}

function selectStepsFeedback(agreed) {
  _stepsAgreed = agreed;
  if (btnStepsAgreedYes) btnStepsAgreedYes.className = `btn btn-feedback${agreed  ? ' btn-feedback--active-yes' : ''}`;
  if (btnStepsAgreedNo)  btnStepsAgreedNo.className  = `btn btn-feedback${!agreed ? ' btn-feedback--active-no'  : ''}`;
}

if (btnTierAgreedYes)  btnTierAgreedYes.addEventListener('click',  () => selectTierFeedback(true));
if (btnTierAgreedNo)   btnTierAgreedNo.addEventListener('click',   () => selectTierFeedback(false));
if (btnStepsAgreedYes) btnStepsAgreedYes.addEventListener('click', () => selectStepsFeedback(true));
if (btnStepsAgreedNo)  btnStepsAgreedNo.addEventListener('click',  () => selectStepsFeedback(false));

// ── Outcome submit handler ─────────────────────────────────────────────────────

btnSubmitOutcome.addEventListener('click', async () => {
  showSubmitError('');
  outcomeSavedMsg.style.display = 'none';

  // Validate
  const outcome = outcomeDiagnosisSelect.value;
  if (!outcome) {
    showSubmitError('Please select a final diagnosis before saving.');
    outcomeDiagnosisSelect.focus();
    return;
  }

  if (!_assessmentId) {
    showSubmitError('No assessment selected. Please look up a patient reference first.');
    return;
  }

  const payload = { outcome };

  const test = outcomeTestSelect.value;
  if (test) payload.confirming_test = test;

  const date = outcomeDateInput.value;
  if (date) payload.outcome_date = date;

  const notes = outcomeNotesInput.value.trim();
  if (notes) payload.outcome_notes = notes;

  // Include clinician feedback only if answered (optional fields)
  if (_tierAgreed  !== null) payload.priority_tier_agreed = _tierAgreed;
  if (_stepsAgreed !== null) payload.next_steps_agreed    = _stepsAgreed;

  btnSubmitOutcome.disabled    = true;
  btnSubmitOutcome.textContent = 'Saving…';

  try {
    const resp = await fetch(
      `${API_BASE}/decisions/${encodeURIComponent(_assessmentId)}/outcome`,
      {
        method:  'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify(payload),
      }
    );

    if (!resp.ok) {
      const err = await resp.json().catch(() => ({}));
      throw new Error(err.detail || `HTTP ${resp.status}`);
    }

    // Success
    outcomeSavedMsg.style.display    = 'block';
    btnSubmitOutcome.textContent     = 'Saved';
    summaryAlreadyRecorded.style.display = 'inline-block';

    // Scroll to confirmation
    outcomeSavedMsg.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

  } catch (err) {
    showSubmitError(`Save failed: ${err.message}`);
    btnSubmitOutcome.disabled    = false;
    btnSubmitOutcome.textContent = 'Save Outcome';
  }
});
