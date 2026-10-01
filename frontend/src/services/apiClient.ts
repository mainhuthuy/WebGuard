/* ============================================================
   Axios client — shared instance + normalised error type
   Backend errors follow: { error: { code, message, status_code } }
   ============================================================ */

import axios, { AxiosError } from 'axios'
import { API_BASE_URL } from '../config'

export class ApiError extends Error {
  readonly status: number | null
  readonly code: string

  constructor(message: string, status: number | null, code: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

interface ErrorBody {
  error?: { code?: string; message?: string; details?: { message?: string }[] }
  detail?: string | { msg?: string }[]
}

/** Convert any thrown value from axios into an ApiError */
export function toApiError(err: unknown): ApiError {
  if (err instanceof ApiError) return err
  if (err instanceof AxiosError) {
    if (!err.response) {
      return new ApiError(
        'Cannot reach the WebGuard server. Please check that the backend is running.',
        null,
        'NETWORK_ERROR',
      )
    }
    const body = err.response.data as ErrorBody | undefined
    const detail = typeof body?.detail === 'string' ? body.detail : undefined
    // Validation errors carry the useful text in details[0].message
    const firstDetail = Array.isArray(body?.error?.details) ? body.error.details[0]?.message : undefined
    return new ApiError(
      // Pydantic prefixes custom validator messages with "Value error, " — not useful to users
      (firstDetail ?? body?.error?.message ?? detail ?? err.message).replace(/^Value error,\s*/i, ''),
      err.response.status,
      body?.error?.code ?? 'HTTP_ERROR',
    )
  }
  return new ApiError(err instanceof Error ? err.message : 'Unknown error', null, 'UNKNOWN')
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30_000,
  headers: { Accept: 'application/json' },
})

apiClient.interceptors.response.use(
  (res) => res,
  (err) => Promise.reject(toApiError(err)),
)
