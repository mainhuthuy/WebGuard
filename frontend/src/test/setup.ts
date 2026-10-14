import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup, configure } from '@testing-library/react'

// Lazy page chunks can take over a second to load the first time, and several times that
// on a busy machine/CI runner. Must stay below `testTimeout` (vite.config.ts) so a missing
// element fails with a readable "Unable to find..." instead of a bare test timeout.
configure({ asyncUtilTimeout: 15000 })

// jsdom has no ResizeObserver (Recharts' ResponsiveContainer needs it)
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverStub

// jsdom does not implement scrollIntoView (used by the live log)
Element.prototype.scrollIntoView ??= () => {}

afterEach(() => {
  cleanup()
})
