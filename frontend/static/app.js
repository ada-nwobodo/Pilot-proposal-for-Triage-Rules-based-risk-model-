/* ============================================================
   Clinical Risk Stratification — Triage NLP Engine
   Frontend application — vanilla JS, no dependencies
   ============================================================ */

'use strict';

// ---- DOM references --------------------------------------------------------

const form            = document.getElementById('risk-form');
const noteTextarea    = document.getElementById('note-text');
const submitBtn       = document.getElementById('submit-btn');
const loadExampleBtn  = document.getElementById('load-example-btn');
const clearBtn        = document.getElementById('clear-btn');
const resultsSection  = document.getElementById('results-section');
const errorBox        = document.getElementById('error-box');

// Result display elements
const riskBadgeEl       = document.getElementById('risk-badge');
const combinedScoreEl   = document.getElementById('combined-score');
const entityScoreEl     = document.getElementById('entity-score');
const vitalsScoreEl     = document.getElementById('vitals-score');
const processingTimeEl  = document.getElementById('processing-time');
const reasoningTextEl   = document.getElementById('reasoning-text');
const overrideBannerEl  = document.getElementById('override-banner');
const entityTableBody   = document.getElementById('entity-table-body');
const vitalsListEl      = document.getElementById('vitals-flags-list');
const emptyEntitiesEl   = document.getElementById('empty-entities');
const emptyVitalsEl     = document.getElementById('empty-vitals');

// Vital sign input elements
const vitalInputIds = [
  'heart-rate', 'systolic-bp', 'diastolic-bp',
  'respiratory-rate', 'spo2', 'temperature', 'gcs'
];

// Map from HTML ID to schema field name
const VITAL_FIELD_MAP = {
  'heart-rate':        'heart_rate',
  'systolic-bp':       'systolic_bp',
  'diastolic-bp':      'diastolic_bp',
  'respiratory-rate':  'respiratory_rate',
  'spo2':              'spo2',
  'temperature':       'temperature',
  'gcs':               'gcs',
};

// ---- State -----------------------------------------------------------------

let exampleIndex = 0;
let cachedExamples = null;

// ---- Helpers ---------------------------------------------------------------

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

// ---- Risk badge ------------------------------------------------------------

const RISK_BADGE_CLASS = {
  LOW:      'risk-badge--low',
  MEDIUM:   'risk-badge--medium',
  HIGH:     'risk-badge--high',
  CRITICAL: 'risk-badge--critical',
};

const RISK_ICONS = {
  LOW:      '&#10003;',
  MEDIUM:   '&#9888;',
  HIGH:     '&#9888;&#9888;',
  CRITICAL: '&#9888;&#9888;&#9888;',
};

function renderRiskBadge(riskLevel) {
  riskBadgeEl.className = `risk-badge ${RISK_BADGE_CLASS[riskLevel] || ''}`;
  riskBadgeEl.innerHTML = `<span>${RISK_ICONS[riskLevel] || ''}</span> ${riskLevel}`;
}

// ---- Entity contributions table --------------------------------------------

function severityClass(severity) {
  return `severity-${severity.toLowerCase()}`;
}

function labelChipHtml(label) {
  const cls = label === 'DIAGNOSIS' ? 'label-chip--diagnosis' : 'label-chip--symptom';
  return `<span class="label-chip ${cls}">${label}</span>`;
}

function renderEntityContributions(contributions) {
  entityTableBody.innerHTML = '';

  const nonZeroContribs = contributions.filter(c => !c.is_negated || c.is_negated);
  if (nonZeroContribs.length === 0) {
    emptyEntitiesEl.style.display = 'block';
    return;
  }
  emptyEntitiesEl.style.display = 'none';

  // Sort: active first, then by score descending
  const sorted = [...contributions].sort((a, b) => {
    if (a.is_negated !== b.is_negated) return a.is_negated ? 1 : -1;
    return b.score_contribution - a.score_contribution;
  });

  for (const contrib of sorted) {
    const tr = document.createElement('tr');
    if (contrib.is_negated) {
      tr.classList.add('entity-negated');
    }

    const scoreDisplay = contrib.is_negated ? '—' : contrib.score_contribution.toFixed(3);
    const severityCls  = contrib.is_negated ? '' : severityClass(contrib.severity);

    tr.innerHTML = `
      <td class="${severityCls}" style="font-weight:500">${escapeHtml(contrib.text)}</td>
      <td>${labelChipHtml(contrib.label)}</td>
      <td class="${severityCls}">${contrib.severity}</td>
      <td>${contrib.is_negated ? '<em>negated</em>' : scoreDisplay}</td>
    `;
    entityTableBody.appendChild(tr);
  }
}

// ---- Vitals flags ----------------------------------------------------------

const VITAL_DISPLAY_NAMES = {
  heart_rate:        'Heart Rate',
  systolic_bp:       'Systolic BP',
  diastolic_bp:      'Diastolic BP',
  respiratory_rate:  'Resp. Rate',
  spo2:              'SpO2',
  temperature:       'Temperature',
  gcs:               'GCS',
};

const VITAL_UNITS = {
  heart_rate:        'bpm',
  systolic_bp:       'mmHg',
  diastolic_bp:      'mmHg',
  respiratory_rate:  '/min',
  spo2:              '%',
  temperature:       '°C',
  gcs:               '',
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
    const unit = VITAL_UNITS[flag.field] || '';
    const ptsCls = flag.points >= 3 ? 'flag-points flag-points--3' : 'flag-points';

    li.innerHTML = `
      <span class="flag-field">${escapeHtml(displayName)}</span>
      <span class="flag-value">${flag.value}${unit}</span>
      <span class="flag-reason">${escapeHtml(flag.reason)}</span>
      <span class="${ptsCls}">+${flag.points} pts</span>
    `;
    vitalsListEl.appendChild(li);
  }
}

// ---- Main result renderer --------------------------------------------------

function renderResult(data) {
  resultsSection.classList.remove('results-hidden');

  renderRiskBadge(data.risk_level);

  combinedScoreEl.textContent  = data.combined_score.toFixed(3);
  entityScoreEl.textContent    = data.entity_score.toFixed(3);
  vitalsScoreEl.textContent    = data.vitals_score;
  processingTimeEl.textContent = `${data.processing_time_ms.toFixed(1)} ms`;

  reasoningTextEl.textContent = data.reasoning_text;

  if (data.override_triggered && data.override_reason) {
    overrideBannerEl.style.display = 'flex';
    overrideBannerEl.innerHTML = `&#9888; Override rule triggered: <strong>${escapeHtml(data.override_reason)}</strong>`;
  } else {
    overrideBannerEl.style.display = 'none';
  }

  renderEntityContributions(data.entity_contributions || []);
  renderVitalsFlags(data.vitals_flags || []);
}

// ---- Escape HTML utility ---------------------------------------------------

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ---- Populate form from a ClinicalInput object ----------------------------

function populateForm(caseObj) {
  noteTextarea.value = caseObj.note_text || '';

  // Clear all vitals first
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

  // Show case label hint if available
  if (caseObj.case_label) {
    noteTextarea.setAttribute('data-case-label', caseObj.case_label);
    noteTextarea.title = `Ground-truth label: ${caseObj.case_label}`;
  } else {
    noteTextarea.removeAttribute('data-case-label');
    noteTextarea.title = '';
  }
}

// ---- Event: form submit ----------------------------------------------------

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
  } catch (err) {
    showError(`Request failed: ${err.message}`);
  } finally {
    setLoading(false);
  }
});

// ---- Event: load example ---------------------------------------------------

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

    // Reset results
    resultsSection.classList.add('results-hidden');
  } catch (err) {
    showError(`Could not load examples: ${err.message}`);
  } finally {
    loadExampleBtn.disabled = false;
    loadExampleBtn.textContent = 'Load Next Example';
  }
});

// ---- Event: clear ----------------------------------------------------------

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
  exampleIndex = 0;
  cachedExamples = null;
});
