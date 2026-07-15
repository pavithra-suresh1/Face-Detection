import { describe, expect, it } from 'vitest'
import { createHiddenCanvas } from './liveDetection'

describe('createHiddenCanvas', () => {
  it('creates a hidden canvas appended to document body', () => {
    const canvas = createHiddenCanvas()
    expect(canvas).toBeInstanceOf(HTMLCanvasElement)
    expect(canvas.style.display).toBe('none')
    expect(document.body.contains(canvas)).toBe(true)
    canvas.remove()
  })

  it('returns a fresh canvas each call', () => {
    const c1 = createHiddenCanvas()
    const c2 = createHiddenCanvas()
    expect(c1).not.toBe(c2)
    c1.remove()
    c2.remove()
  })
})
