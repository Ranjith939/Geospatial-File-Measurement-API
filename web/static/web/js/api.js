// Thin fetch wrapper over the GeoMeasure REST API. Errors arrive as {error: {code, message, details}}.

export class ApiError extends Error {
  constructor(status, body) {
    const err = body?.error || {}
    super(err.message || `Request failed (${status})`)
    this.status = status
    this.code = err.code || 'HTTP_ERROR'
    this.details = err.details || {}
  }
}

export async function request(path, options) {
  let res
  try {
    res = await fetch(path, { headers: { Accept: 'application/json' }, ...options })
  } catch {
    throw new ApiError(0, { error: { code: 'NETWORK_ERROR', message: 'The API could not be reached.' } })
  }
  if (res.status === 204) return null
  const body = await res.json().catch(() => null)
  if (!res.ok) throw new ApiError(res.status, body)
  return body
}

export const api = {
  upload(file) {
    const form = new FormData()
    form.append('file', file)
    return request('/api/files/', { method: 'POST', body: form })
  },
  getFile: (id) => request(`/api/files/${id}/`),
  getMeasurements: (id) => request(`/api/files/${id}/measurements/`),
}
