import api from './axios'

export function requestTaskAssist(prompt, projectId) {
  return api
    .post('/ai/task-assist/', { prompt, project: projectId ?? undefined })
    .then(({ data }) => data)
}

export function requestProjectSummary(projectId) {
  return api.get(`/ai/projects/${projectId}/summary/`).then(({ data }) => data.summary)
}
