import { describe, it, expect } from 'vitest'
import { AxiosError, type AxiosResponse, type InternalAxiosRequestConfig } from 'axios'
import { ApiError, toApiError } from './apiClient'

function axiosErrorWith(status: number, data: unknown): AxiosError {
  const response = {
    status,
    data,
    statusText: '',
    headers: {},
    config: {} as InternalAxiosRequestConfig,
  } as AxiosResponse
  return new AxiosError('Request failed', 'ERR_BAD_REQUEST', undefined, undefined, response)
}

describe('toApiError', () => {
  it('returns an existing ApiError unchanged', () => {
    const original = new ApiError('boom', 500, 'X')
    expect(toApiError(original)).toBe(original)
  })

  it('reports a network error when there is no response', () => {
    const err = toApiError(new AxiosError('Network Error', 'ERR_NETWORK'))
    expect(err.code).toBe('NETWORK_ERROR')
    expect(err.status).toBeNull()
    expect(err.message).toMatch(/backend is running/i)
  })

  it('reads code and message from the domain error body', () => {
    const err = toApiError(
      axiosErrorWith(404, { error: { code: 'SCAN_NOT_FOUND', message: 'Scan không tồn tại' } }),
    )
    expect(err.status).toBe(404)
    expect(err.code).toBe('SCAN_NOT_FOUND')
    expect(err.message).toBe('Scan không tồn tại')
  })

  it('prefers the first validation detail over the generic message', () => {
    const err = toApiError(
      axiosErrorWith(422, {
        error: {
          code: 'VALIDATION_ERROR',
          message: 'Dữ liệu gửi lên không hợp lệ.',
          details: [{ message: 'Value error, localhost is not allowed' }],
        },
      }),
    )
    expect(err.message).toBe('localhost is not allowed')
    expect(err.code).toBe('VALIDATION_ERROR')
  })

  it('falls back to a FastAPI string detail', () => {
    const err = toApiError(axiosErrorWith(400, { detail: 'Cannot cancel this scan' }))
    expect(err.message).toBe('Cannot cancel this scan')
    expect(err.code).toBe('HTTP_ERROR')
  })

  it('wraps unknown values', () => {
    expect(toApiError(new Error('oops')).message).toBe('oops')
    expect(toApiError('weird').code).toBe('UNKNOWN')
  })
})

describe('toApiError — message cleanup', () => {
  it('strips the "Value error, " prefix Pydantic adds to custom validator messages', () => {
    const err = toApiError(
      axiosErrorWith(422, { error: { details: [{ message: 'Value error, Không được phép quét localhost' }] } }),
    )
    expect(err.message).toBe('Không được phép quét localhost')
  })

  it('leaves other messages untouched', () => {
    expect(toApiError(axiosErrorWith(404, { error: { message: 'Scan not found' } })).message).toBe('Scan not found')
  })
})
