const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

export async function searchStudies(query, page = 1, limit = 10, zip = null) {
  const response = await fetch(`${API_BASE}/search`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      query_text: query,
      conditions_include: [],
      conditions_exclude: [],
      zip: zip,
      page: page,
      limit: limit
    }),
  });

  if (!response.ok) {
    throw new Error(`Search failed: ${response.statusText}`);
  }

  return response.json();
}

export async function getStudyById(studyId) {
  const response = await fetch(`${API_BASE}/studies/${studyId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch study: ${response.statusText}`);
  }

  return response.json();
}

export async function generateEligibilityQuiz(studyId, eligibilityCriteria) {
  const response = await fetch(`${API_BASE}/ai/eligibility-quiz`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      study_id: studyId,
      eligibility_criteria: eligibilityCriteria
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `AI generation failed: ${response.statusText}`);
  }

  return response.json();
}

export async function generateStudySummary(study) {
  const response = await fetch(`${API_BASE}/ai/study-summary`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      study_id: study.id,
      title: study.title,
      brief_summary: study.brief_summary,
      detailed_description: study.detailed_description,
      interventions: study.interventions?.map(i => i.intervention_name) || [],
      conditions: study.conditions || []
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `AI generation failed: ${response.statusText}`);
  }

  return response.json();
}

export async function generatePlainTitle(study) {
  const response = await fetch(`${API_BASE}/ai/plain-title`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      study_id: study.id,
      title: study.title,
      brief_summary: study.brief_summary,
      interventions: study.interventions?.map(i => i.intervention_name) || [],
      conditions: study.conditions || []
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `AI generation failed: ${response.statusText}`);
  }

  return response.json();
}
