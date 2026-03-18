/* ============================================================
   Pulmonary Embolism Risk Assessment — Triage NLP Engine
   Frontend application — vanilla JS, no dependencies
   ============================================================ */

'use strict';

// ── DOM references ────────────────────────────────────────────────────────────

const form           = document.getElementById('risk-form');
const noteTextarea   = document.getElementById('note-text');
const submitBtn      = document.getElementById('submit-btn');
const loadExampleBtn = document.getElementById('load-example-btn');
const clearBtn       = document.getElementById('clear-btn');
const resultsSection = document.getElementById('results-section');
const errorBox       = document.getElementById('error-box');

// Result display elements
const riskBadgeEl         = document.getElementById('risk-badge');
const combinedScoreEl     = document.getElementById('combined-score');
const processingTimeEl    = document.getElementById('processing-time');
const reasoningTextEl     = document.getElementById('reasoning-text');
const entityTableBody     = document.getElementById('entity-table-body');
const vitalsListEl        = document.getElementById('vitals-flags-list');
const emptyEntitiesEl     = document.getElementById('empty-entities');
const emptyVitalsEl       = document.getElementById('empty-vitals');
const suggestedDiagnosisEl = document.getElementById('suggested-diagnosis');
const nextStepsSection    = document.getElementById('next-steps-section');
const nextStepsList       = document.getElementById('next-steps-list');

// Vital sign input elements
const vitalInputIds = [
  'heart-rate', 'systolic-bp', 'diastolic-bp',
  'respiratory-rate', 'spo2', 'temperature', 'gcs',
];

// Map from HTML ID to schema field name
const VITAL_FIELD_MAP = {
  'heart-rate':       'heart_rate',
  'systolic-bp':      'systolic_bp',
  'diastolic-bp':     'diastolic_bp',
  'respiratory-rate': 'respiratory_rate',
  'spo2':             'spo2',
  'temperature':      'temperature',
  'gcs':              'gcs',
};

// ── State ─────────────────────────────────────────────────────────────────────

let exampleIndex    = 0;
let cachedExamples  = null;

// ── Helpers ───────────────────────────────────────────────────────────────────

function setLoading(loading) {
  if (loading) {
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Analysing...';
  } else {
    submitBtn.disabled = false;
    submitBtn.innerHTML = 'Analyse Risk';
  }
}

function showError(message) {
  errorBox.textContent = message;
  errorBox.classList.add('visible');
  resultsSection.classList.add('results-hidden');
}

function clearError() {
  errorBox.classList.remove('visible');
  errorBox.textContent = '';
}

function buildPayload() {
  const noteText = noteTextarea.value.trim();
  if (!noteText) {
    throw new Error('Please enter a clinical note before submitting.');
  }

  const vitals = {};
  for (const htmlId of vitalInputIds) {
    const el = document.getElementById(htmlId);
    if (el && el.value !== '') {
      const raw = parseFloat(el.value);
      if (!isNaN(raw)) {
        vitals[VITAL_FIELD_MAP[htmlId]] = raw;
      }
    }
  }

  return {
    note_text: noteText,
    vitals: Object.keys(vitals).length > 0 ? vitals : null,
  };
}

// ── Risk badge ────────────────────────────────────────────────────────────────

const RISK_BADGE_CLASS = {
  LOW:      'risk-badge--low',
  MEDIUM:   'risk-badge--medium',
  HIGH:     'risk-badge--high',
  CRITICAL: 'risk-badge--critical',
};

const RISK_LABEL = {
  LOW:      'Low PE Risk',
  MEDIUM:   'Medium PE Risk',
  HIGH:     'High PE Risk',
  CRITICAL: 'Critical PE Risk',
};

function renderRiskBadge(riskLevel) {
  riskBadgeEl.className = `risk-badge ${RISK_BADGE_CLASS[riskLevel] || ''}`;
  riskBadgeEl.textContent = RISK_LABEL[riskLevel] || riskLevel;
}

// ── Section 1: Entity contributions table ────────────────────────────────────

function severityClass(severity) {
  return `severity-${severity.toLowerCase()}`;
}

function labelChipHtml(label) {
  if (label === 'PE_RISK_FACTOR') {
    return '<span class="label-chip label-chip--risk-factor">Risk Factor</span>';
  }
  return '<span class="label-chip label-chip--symptom">PE Symptom</span>';
}

function renderEntityContributions(contributions) {
  entityTableBody.innerHTML = '';

  if (contributions.length === 0) {
    emptyEntitiesEl.style.display = 'block';
    return;
  }
  emptyEntitiesEl.style.display = 'none';

  // Active first, then negated; within each group sort by score descending
  const sorted = [...contributions].sort((a, b) => {
    if (a.is_negated !== b.is_negated) return a.is_negated ? 1 : -1;
    return b.score_contribution - a.score_contribution;
  });

  for (const contrib of sorted) {
    const tr = document.createElement('tr');
    if (contrib.is_negated) tr.classList.add('entity-negated');

    const scoreDisplay = contrib.is_negated
      ? '<em>negated</em>'
      : contrib.score_contribution === 0
        ? '<em>duplicate</em>'
        : '+1';
    const sevCls = contrib.is_negated ? '' : severityClass(contrib.severity);

    tr.innerHTML = `
      <td class="${sevCls}" style="font-weight:500">${escapeHtml(contrib.text)}</td>
      <td>${labelChipHtml(contrib.label)}</td>
      <td class="${sevCls}">${contrib.severity}</td>
      <td>${scoreDisplay}</td>
    `;
    entityTableBody.appendChild(tr);
  }
}

// ── Section 2: Vitals flags ───────────────────────────────────────────────────

const VITAL_DISPLAY_NAMES = {
  heart_rate:       'Heart Rate',
  systolic_bp:      'Systolic BP',
  diastolic_bp:     'Diastolic BP',
  respiratory_rate: 'Resp. Rate',
  spo2:             'SpO2',
  bp:               'Blood Pressure',
};

const VITAL_UNITS = {
  heart_rate:       'bpm',
  systolic_bp:      'mmHg',
  diastolic_bp:     'mmHg',
  respiratory_rate: '/min',
  spo2:             '%',
  bp:               '',   // full info already in reason string
};

function renderVitalsFlags(flags) {
  vitalsListEl.innerHTML = '';

  if (!flags || flags.length === 0) {
    emptyVitalsEl.style.display = 'block';
    return;
  }
  emptyVitalsEl.style.display = 'none';

  for (const flag of flags) {
    const li = document.createElement('li');
    li.className = 'vitals-flag-item';
    const displayName = VITAL_DISPLAY_NAMES[flag.field] || flag.field;
    const unit = VITAL_UNITS[flag.field] !== undefined ? VITAL_UNITS[flag.field] : '';
    // For combined BP flag, suppress raw value (reason string has full context)
    const valueStr = flag.field === 'bp' ? '' : `${flag.value}${unit}`;

    li.innerHTML = `
      <span class="flag-field">${escapeHtml(displayName)}</span>
      ${valueStr ? `<span class="flag-value">${valueStr}</span>` : ''}
      <span class="flag-reason">${escapeHtml(flag.reason)}</span>
      <span class="flag-points">+${flag.points} pts</span>
    `;
    vitalsListEl.appendChild(li);
  }
}

// ── Section 4: Suggested diagnosis ───────────────────────────────────────────

function renderSuggestedDiagnosis(diagnosis, riskLevel) {
  if (!diagnosis) {
    suggestedDiagnosisEl.className = 'diagnosis-box diagnosis-box--none';
    suggestedDiagnosisEl.textContent = 'Not suggestive of PE.';
    return;
  }
  const cls = riskLevel === 'CRITICAL'
    ? 'diagnosis-box diagnosis-box--critical'
    : 'diagnosis-box diagnosis-box--positive';
  suggestedDiagnosisEl.className = cls;
  suggestedDiagnosisEl.textContent = diagnosis;
}

// ── Section 5: Recommended next steps ────────────────────────────────────────

// Blood-test items are grouped visually under a "Blood tests:" parent entry.
const BLOOD_TESTS = new Set(['FBC', 'U&E', 'Clotting', 'D-dimer']);

function renderNextSteps(steps) {
  nextStepsList.innerHTML = '';
  if (!steps || steps.length === 0) {
    nextStepsSection.style.display = 'none';
    return;
  }
  nextStepsSection.style.display = '';

  const topLevel  = steps.filter(s => !BLOOD_TESTS.has(s));
  const bloodTests = steps.filter(s => BLOOD_TESTS.has(s));

  for (const step of topLevel) {
    const li = document.createElement('li');
    li.className = 'next-step-item';
    li.innerHTML = `<span class="next-step-icon">&#10003;</span> ${escapeHtml(step)}`;
    nextStepsList.appendChild(li);
  }

  if (bloodTests.length > 0) {
    const li = document.createElement('li');
    li.className = 'next-step-item';
    // Build the label node first, then append a sub-list beneath it
    const label = document.createElement('span');
    label.innerHTML = `<span class="next-step-icon">&#10003;</span> Blood tests:`;
    li.appendChild(label);

    const subUl = document.createElement('ul');
    subUl.className = 'next-steps-sublist';
    for (const test of bloodTests) {
      const subLi = document.createElement('li');
      subLi.className = 'next-step-subitem';
      subLi.textContent = test;
      subUl.appendChild(subLi);
    }
    li.appendChild(subUl);
    nextStepsList.appendChild(li);
  }
}

// ── Main result renderer ──────────────────────────────────────────────────────

function renderResult(data) {
  resultsSection.classList.remove('results-hidden');

  // Section 1
  renderEntityContributions(data.entity_contributions || []);

  // Section 2
  renderVitalsFlags(data.vitals_flags || []);

  // Section 3
  renderRiskBadge(data.risk_level);
  combinedScoreEl.textContent = data.combined_score.toFixed(0);
  reasoningTextEl.textContent = data.reasoning_text;
  processingTimeEl.textContent = `${data.processing_time_ms.toFixed(1)} ms`;

  // Section 4
  renderSuggestedDiagnosis(data.suggested_diagnosis || null, data.risk_level);

  // Section 5
  renderNextSteps(data.next_steps || []);
}

// ── Escape HTML utility ───────────────────────────────────────────────────────

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ── Populate form from a ClinicalInput object ─────────────────────────────────

function populateForm(caseObj) {
  noteTextarea.value = caseObj.note_text || '';

  for (const htmlId of vitalInputIds) {
    const el = document.getElementById(htmlId);
    if (el) el.value = '';
  }

  if (caseObj.vitals) {
    for (const [htmlId, fieldName] of Object.entries(VITAL_FIELD_MAP)) {
      const val = caseObj.vitals[fieldName];
      const el  = document.getElementById(htmlId);
      if (el && val !== null && val !== undefined) {
        el.value = val;
      }
    }
  }

  if (caseObj.case_label) {
    noteTextarea.setAttribute('data-case-label', caseObj.case_label);
    noteTextarea.title = `Ground-truth label: ${caseObj.case_label}`;
  } else {
    noteTextarea.removeAttribute('data-case-label');
    noteTextarea.title = '';
  }
}

// ── Event: form submit ────────────────────────────────────────────────────────

form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearError();

  let payload;
  try {
    payload = buildPayload();
  } catch (err) {
    showError(err.message);
    return;
  }

  setLoading(true);

  try {
    const response = await fetch('/assess', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      const detail  = errData.detail || `HTTP ${response.status}: ${response.statusText}`;
      throw new Error(Array.isArray(detail)
        ? detail.map(d => d.msg || JSON.stringify(d)).join('; ')
        : String(detail));
    }

    const data = await response.json();
    renderResult(data);
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (err) {
    showError(`Request failed: ${err.message}`);
  } finally {
    setLoading(false);
  }
});

// ── Event: load example ───────────────────────────────────────────────────────

loadExampleBtn.addEventListener('click', async () => {
  loadExampleBtn.disabled = true;
  loadExampleBtn.textContent = 'Loading...';

  try {
    if (!cachedExamples) {
      const resp = await fetch('/examples');
      if (!resp.ok) throw new Error(`Failed to fetch examples (${resp.status})`);
      cachedExamples = await resp.json();
    }

    if (!cachedExamples || cachedExamples.length === 0) {
      showError('No examples available.');
      return;
    }

    const caseObj = cachedExamples[exampleIndex % cachedExamples.length];
    exampleIndex++;

    populateForm(caseObj);
    clearError();
    resultsSection.classList.add('results-hidden');
  } catch (err) {
    showError(`Could not load examples: ${err.message}`);
  } finally {
    loadExampleBtn.disabled = false;
    loadExampleBtn.textContent = 'Load Next Example';
  }
});

// ── Event: clear ──────────────────────────────────────────────────────────────

clearBtn.addEventListener('click', () => {
  noteTextarea.value = '';
  for (const htmlId of vitalInputIds) {
    const el = document.getElementById(htmlId);
    if (el) el.value = '';
  }
  resultsSection.classList.add('results-hidden');
  clearError();
  noteTextarea.removeAttribute('data-case-label');
  noteTextarea.title = '';
  exampleIndex   = 0;
  cachedExamples = null;
});
