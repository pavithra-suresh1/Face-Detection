export function createHiddenCanvas() {
  const canvas = document.createElement('canvas')
  canvas.style.display = 'none'
  document.body.appendChild(canvas)
  return canvas
}
