import '@testing-library/jest-dom/vitest'
import { afterEach } from 'vitest'
import { cleanup, configure } from '@testing-library/react'

// Lazy page chunks can take over a second to load the first time
configure({ asyncUtilTimeout: 5000 })

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
