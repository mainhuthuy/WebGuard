/* ============================================================
   Runtime configuration (Vite env)
   ============================================================ */

/** Base path of the backend API (proxied to :8000 by Vite in dev) */
export const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

/** Use the local mock scan simulation instead of the real backend */
export const USE_MOCK: boolean = import.meta.env.VITE_USE_MOCK === 'true'
