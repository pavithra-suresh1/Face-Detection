import { useRef, useState, useEffect, useCallback } from 'react'
import Webcam from 'react-webcam'
import { liveDetect } from '../api/faceApi'

const CAPTURE_W = 640
const CAPTURE_H = 480
const FRAME_SKIP = 3
const BOX_SMOOTH = 0.45
const CORNER_LEN = 16
const CORNER_THICK = 3

export default function RealtimeDetection() {
  const webcamRef = useRef(null)
  const overlayRef = useRef(null)
  const hiddenRef = useRef(null)
  const frameRef = useRef(0)
  const busyRef = useRef(false)
  const rafRef = useRef(null)
  const smoothRef = useRef({})
  const startedRef = useRef(false)
  const scanRef = useRef(0)
  const fadeRef = useRef({})
  const tsRef = useRef(0)
  const fpsRef = useRef({ frames: 0, lastTime: performance.now(), value: 0 })
  const fpsDisplayRef = useRef(0)

  const [ready, setReady] = useState(false)
  const [faces, setFaces] = useState([])
  const facesRef = useRef([])
  const [latency, setLatency] = useState(null)
  const [error, setError] = useState('')
  const [registeredCount, setRegisteredCount] = useState(0)
  const [fps, setFps] = useState(0)
  const latBuf = useRef([])

  const drawCornerBox = useCallback((ctx, x, y, w, h, color, len, thick) => {
    ctx.strokeStyle = color
    ctx.lineWidth = thick
    ctx.lineCap = 'round'
    const dirs = [
      [x, y, x + len, y, x, y + len],
      [x + w, y, x + w - len, y, x + w, y + len],
      [x, y + h, x + len, y + h, x, y + h - len],
      [x + w, y + h, x + w - len, y + h, x + w, y + h - len],
    ]
    for (const [cx, cy, hx, hy, vx, vy] of dirs) {
      ctx.beginPath()
      ctx.moveTo(hx, hy)
      ctx.lineTo(cx, cy)
      ctx.lineTo(vx, vy)
      ctx.stroke()
    }
  }, [])

  const drawBoxes = useCallback((detected, vw, vh) => {
    const canvas = overlayRef.current
    if (!canvas) return
    canvas.width = vw
    canvas.height = vh
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, vw, vh)
    const sm = smoothRef.current
    const fd = fadeRef.current
    const a = BOX_SMOOTH
    const now = performance.now()

    const activeIds = new Set(detected.map(f => String(f.track_id)))

    for (const tid of Object.keys(fd)) {
      if (!activeIds.has(tid) && (now - fd[tid].t) > 300) {
        delete fd[tid]
        delete sm[tid]
      }
    }

    for (const face of detected) {
      const r = face.region
      const k = face.track_id != null ? String(face.track_id) : null
      let s
      if (k && sm[k]) {
        const p = sm[k]
        s = {
          x: Math.round(p.x * (1 - a) + r.x * a),
          y: Math.round(p.y * (1 - a) + r.y * a),
          w: Math.round(p.w * (1 - a) + r.w * a),
          h: Math.round(p.h * (1 - a) + r.h * a),
        }
        sm[k] = s
      } else {
        s = { ...r }
        if (k) sm[k] = { ...s }
      }

      if (k && !fd[k]) {
        fd[k] = { t: now, opacity: 0 }
      }
      const fade = fd[k]
      if (fade) {
        fade.opacity = Math.min(1, fade.opacity + 0.15)
        fade.t = now
      }
      const opacity = fade ? fade.opacity : 1

      const known = face.is_known
      const checking = face.status === 'checking'
      const color = checking ? '#f59e0b' : known ? '#22c55e' : '#ef4444'
      const colorDim = checking
        ? `rgba(245,158,11,${0.08 * opacity})`
        : known
          ? `rgba(34,197,94,${0.08 * opacity})`
          : `rgba(239,68,68,${0.08 * opacity})`

      ctx.globalAlpha = opacity

      ctx.fillStyle = colorDim
      ctx.fillRect(s.x, s.y, s.w, s.h)

      if (known) {
        ctx.shadowColor = 'rgba(34,197,94,0.4)'
        ctx.shadowBlur = 16
      } else if (!checking) {
        ctx.shadowColor = 'rgba(239,68,68,0.3)'
        ctx.shadowBlur = 10
      }

      const cornerLen = Math.min(CORNER_LEN, Math.floor(Math.min(s.w, s.h) * 0.25))
      drawCornerBox(ctx, s.x, s.y, s.w, s.h, color, cornerLen, CORNER_THICK)

      ctx.shadowColor = 'transparent'
      ctx.shadowBlur = 0

      const label = face.is_known ? (face.label || 'Known') : (checking ? 'Identifying...' : 'Unknown')

      ctx.font = 'bold 13px system-ui, -apple-system, sans-serif'
      const tw = ctx.measureText(label).width
      const padX = 10
      const lx = s.x
      const ly = s.y - 32 < 0 ? s.y + 8 : s.y - 32

      const bgColor = checking ? 'rgba(245,158,11,0.94)' : known ? 'rgba(34,197,94,0.94)' : 'rgba(239,68,68,0.94)'
      ctx.fillStyle = bgColor
      ctx.beginPath()
      ctx.roundRect(lx, ly, tw + padX * 2, 24, 4)
      ctx.fill()

      ctx.fillStyle = '#fff'
      ctx.textBaseline = 'middle'
      ctx.fillText(label, lx + padX, ly + 12)
      ctx.textBaseline = 'alphabetic'

      ctx.globalAlpha = 1
    }

    for (const tid of Object.keys(fd)) {
      if (!activeIds.has(tid)) {
        const fade = fd[tid]
        const remaining = 1 - (now - fade.t) / 300
        if (remaining > 0 && sm[tid]) {
          fade.opacity = remaining
          const s = sm[tid]
          ctx.globalAlpha = remaining
          ctx.strokeStyle = 'rgba(255,255,255,0.3)'
          ctx.lineWidth = 1
          ctx.setLineDash([4, 4])
          ctx.strokeRect(s.x, s.y, s.w, s.h)
          ctx.setLineDash([])
          ctx.globalAlpha = 1
        }
      }
    }
  }, [drawCornerBox])

  const drawScanOverlay = useCallback((vw, vh) => {
    const canvas = overlayRef.current
    if (!canvas) return
    if (canvas.width !== vw) canvas.width = vw
    if (canvas.height !== vh) canvas.height = vh
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, vw, vh)

    scanRef.current = (scanRef.current + 2.5) % vh
    const sy = scanRef.current

    const grad = ctx.createLinearGradient(0, sy - 40, 0, sy + 40)
    grad.addColorStop(0, 'rgba(59,130,246,0)')
    grad.addColorStop(0.5, 'rgba(59,130,246,0.12)')
    grad.addColorStop(1, 'rgba(59,130,246,0)')
    ctx.fillStyle = grad
    ctx.fillRect(0, sy - 40, vw, 80)

    ctx.strokeStyle = 'rgba(59,130,246,0.35)'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(0, sy)
    ctx.lineTo(vw, sy)
    ctx.stroke()
  }, [])

  useEffect(() => {
    if (!ready || startedRef.current) return
    startedRef.current = true

    const tick = async () => {
      if (busyRef.current) return
      const wc = webcamRef.current
      if (!wc?.video?.videoWidth) return
      const v = wc.video
      const c = hiddenRef.current
      if (!c) return
      c.width = CAPTURE_W
      c.height = CAPTURE_H
      c.getContext('2d').drawImage(v, 0, 0, CAPTURE_W, CAPTURE_H)

      busyRef.current = true
      c.toBlob(async (blob) => {
        if (!blob) { busyRef.current = false; return }
        try {
          const f = new File([blob], 'frame.jpg', { type: 'image/jpeg' })
          const t0 = performance.now()
          const res = await liveDetect(f)
          const ms = performance.now() - t0
          latBuf.current.push(ms)
          if (latBuf.current.length > 10) latBuf.current.shift()
          setLatency(Math.round(latBuf.current.reduce((a, b) => a + b, 0) / latBuf.current.length))

          if (res.success) {
            setRegisteredCount(res.registered_faces || 0)
            const scaleX = v.videoWidth / CAPTURE_W
            const scaleY = v.videoHeight / CAPTURE_H
            const detected = (res.faces || []).map(f => ({
              ...f,
              region: {
                x: Math.round((CAPTURE_W - f.region.x - f.region.w) * scaleX),
                y: Math.round(f.region.y * scaleY),
                w: Math.round(f.region.w * scaleX),
                h: Math.round(f.region.h * scaleY),
              },
            }))
            tsRef.current = Date.now()
            facesRef.current = detected
            setFaces(detected)
            setError('')
          } else if (res.message) {
            setError(res.message)
          }
        } catch (err) {
          setError(err?.response?.data?.message || err.message || 'Connection error')
        } finally {
          busyRef.current = false
        }
      }, 'image/jpeg', 0.6)
    }

    const loop = () => {
      frameRef.current++
      if (frameRef.current % FRAME_SKIP === 0) tick()

      const fpsData = fpsRef.current
      fpsData.frames++
      const now = performance.now()
      if (now - fpsData.lastTime >= 1000) {
        fpsData.value = fpsData.frames
        fpsData.frames = 0
        fpsData.lastTime = now
        fpsDisplayRef.current = fpsData.value
        setFps(fpsData.value)
      }

      const vw = webcamRef.current?.video?.videoWidth || CAPTURE_W
      const vh = webcamRef.current?.video?.videoHeight || CAPTURE_H

      drawBoxes(facesRef.current, vw, vh)

      if (facesRef.current.length === 0) {
        drawScanOverlay(vw, vh)
      }

      rafRef.current = requestAnimationFrame(loop)
    }
    rafRef.current = requestAnimationFrame(loop)
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current) }
  }, [ready, drawBoxes, drawScanOverlay])

  const knownCount = faces.filter(f => f.is_known).length
  const unknownCount = faces.filter(f => !f.is_known && f.status !== 'checking' && f.status !== 'no_registered').length
  const checkingCount = faces.filter(f => f.status === 'checking').length

  return (
    <div className="min-h-screen bg-slate-950">
      <div className="bg-slate-900/80 backdrop-blur border-b border-slate-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-5">
          <div className="flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse shadow-[0_0_6px_rgba(34,197,94,0.6)]" />
            <span className="text-green-400 text-xs font-bold tracking-[0.15em] uppercase">Live</span>
          </div>
          <div className="flex items-center gap-3 text-xs transition-all duration-200">
            {faces.length > 0 && (
              <>
                <span className="text-slate-500">|</span>
                <span className="text-slate-300 font-medium">{faces.length} face{faces.length > 1 ? 's' : ''}</span>
              </>
            )}
            {knownCount > 0 && (
              <span className="flex items-center gap-1 text-emerald-400">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                {knownCount} known
              </span>
            )}
            {unknownCount > 0 && (
              <span className="flex items-center gap-1 text-red-400">
                <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                {unknownCount} unknown
              </span>
            )}
            {checkingCount > 0 && (
              <span className="flex items-center gap-1 text-amber-400">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                {checkingCount} checking
              </span>
            )}
          </div>
          {registeredCount > 0 && (
            <span className="text-[10px] text-slate-600 font-mono">
              {registeredCount} registered
            </span>
          )}
        </div>
        <div className="flex items-center gap-4 text-[11px] font-mono">
          {fps > 0 && (
            <span className={`px-2 py-0.5 rounded transition-colors duration-300 ${fps >= 25 ? 'bg-emerald-500/15 text-emerald-400' : fps >= 15 ? 'bg-amber-500/15 text-amber-400' : 'bg-red-500/15 text-red-400'}`}>
              {fps} FPS
            </span>
          )}
          {latency !== null && (
            <span className={`px-2 py-0.5 rounded transition-colors duration-300 ${latency < 200 ? 'bg-emerald-500/15 text-emerald-400' : latency < 400 ? 'bg-amber-500/15 text-amber-400' : 'bg-red-500/15 text-red-400'}`}>
              {latency}ms
            </span>
          )}
          <span className="text-slate-600">640x480</span>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-5">
        <div className="relative bg-black rounded-xl overflow-hidden shadow-2xl ring-1 ring-white/5">
          <Webcam
            ref={webcamRef}
            screenshotFormat="image/jpeg"
            className="w-full object-contain max-h-[70vh]"
            mirrored
            onUserMedia={() => setReady(true)}
            videoConstraints={{ width: 640, height: 480, facingMode: 'user' }}
          />
          <canvas ref={overlayRef} className="absolute inset-0 w-full h-full pointer-events-none" style={{ imageRendering: 'auto' }} />
          <canvas ref={hiddenRef} style={{ display: 'none' }} />

          {!ready && (
            <div className="absolute inset-0 bg-slate-950/95 flex items-center justify-center">
              <div className="text-center">
                <div className="w-10 h-10 border-2 border-white/10 border-t-blue-500 rounded-full animate-spin mx-auto mb-3" />
                <p className="text-white/40 text-xs tracking-wider uppercase">Initializing camera</p>
              </div>
            </div>
          )}

          {ready && faces.length === 0 && !error && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 pointer-events-none transition-opacity duration-200">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-black/50 backdrop-blur-sm border border-white/5">
                <div className="w-1 h-1 rounded-full bg-blue-400 animate-pulse" />
                <span className="text-[11px] text-white/30 tracking-wide">SCANNING</span>
              </div>
            </div>
          )}

          {ready && registeredCount === 0 && !error && (
            <div className="absolute top-12 left-1/2 -translate-x-1/2 pointer-events-none">
              <div className="px-3 py-1.5 rounded-md bg-amber-500/10 backdrop-blur-sm border border-amber-500/20">
                <span className="text-[11px] text-amber-400/80 tracking-wide">No registered faces found</span>
              </div>
            </div>
          )}

          {ready && error && (
            <div className="absolute bottom-4 left-1/2 -translate-x-1/2 pointer-events-none">
              <div className="px-4 py-2 rounded-lg border backdrop-blur-sm text-xs bg-red-500/15 border-red-500/20 text-red-400">
                {error}
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-4 pb-8">
        {faces.length > 0 ? (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-white/50 text-[11px] font-bold tracking-[0.2em] uppercase">Detected Faces</h3>
              <div className="flex items-center gap-3 text-[11px]">
                {knownCount > 0 && (
                  <span className="flex items-center gap-1.5 text-emerald-400/70">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    {knownCount} recognized
                  </span>
                )}
                {unknownCount > 0 && (
                  <span className="flex items-center gap-1.5 text-red-400/70">
                    <span className="w-1.5 h-1.5 rounded-full bg-red-400" />
                    {unknownCount} unrecognized
                  </span>
                )}
                {checkingCount > 0 && (
                  <span className="flex items-center gap-1.5 text-amber-400/70">
                    <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
                    {checkingCount} checking
                  </span>
                )}
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
              {faces.map((f) => {
                const known = f.is_known
                const checking = f.status === 'checking'
                return (
                  <div
                    key={f.track_id}
                    className={`relative flex items-center gap-3 px-4 py-3 rounded-lg border transition-all duration-300 ease-out ${
                      checking
                        ? 'bg-amber-500/[0.06] border-amber-500/20'
                        : known
                          ? 'bg-emerald-500/[0.06] border-emerald-500/20'
                          : 'bg-red-500/[0.06] border-red-500/20'
                    }`}
                  >
                    <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-white text-xs font-bold transition-colors duration-300 ${
                      checking
                        ? 'bg-amber-500/20 text-amber-400'
                        : known
                          ? 'bg-emerald-500/20 text-emerald-400'
                          : 'bg-red-500/20 text-red-400'
                    }`}>
                      {checking ? (
                        <div className="w-3 h-3 border-2 border-amber-400/40 border-t-amber-400 rounded-full animate-spin" />
                      ) : known ? (
                        f.label?.[0]?.toUpperCase() ?? '?'
                      ) : '?'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={`text-sm font-semibold truncate transition-colors duration-300 ${
                        checking ? 'text-amber-400' : known ? 'text-emerald-400' : 'text-red-400'
                      }`}>
                        {checking ? 'Identifying...' : known ? (f.label || 'Known') : 'Unknown'}
                      </p>

                    </div>
                    <span className={`text-[9px] font-bold tracking-wider uppercase px-1.5 py-0.5 rounded transition-colors duration-300 ${
                      checking
                        ? 'bg-amber-500/15 text-amber-500/70'
                        : known
                          ? 'bg-emerald-500/15 text-emerald-500/70'
                          : 'bg-red-500/15 text-red-500/70'
                    }`}>
                      {checking ? 'CHECK' : known ? 'KNOWN' : 'UNKN'}
                    </span>
                  </div>
                )
              })}
            </div>
          </div>
        ) : ready && (
          <div className="bg-slate-900/50 rounded-lg border border-slate-800/50 px-6 py-10 text-center">
            <div className="w-8 h-8 rounded-full bg-slate-800 flex items-center justify-center mx-auto mb-3">
              <div className="w-2 h-2 rounded-full bg-slate-600 animate-pulse" />
            </div>
            <p className="text-slate-600 text-xs tracking-wide">Waiting for faces in camera view</p>
          </div>
        )}
      </div>
    </div>
  )
}
