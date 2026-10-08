// 2D geometry map: SVG, no tiles, no WebGL. Pan/zoom by viewBox; feature nodes are built once.
// Display only: every measurement label comes from the API; extents are geodesic bbox spans.
import { bboxOf, fmtDistance, fmtMeasurement, featureLabel, haversine, niceStep, projector, toSvg, unproject } from './geo.js'
import { icon, reducedMotion, tween } from './dom.js'

const NS = 'http://www.w3.org/2000/svg'
const PAD = 48
const C = { primary: '#2F6B4F', dark: '#1E4534', error: '#C34A4A', measure: '#B9772A', ink: '#151716', muted: '#6B716C' }

function el(name, attrs = {}, parent) {
  const n = document.createElementNS(NS, name)
  for (const [k, v] of Object.entries(attrs)) if (v != null) n.setAttribute(k, v)
  if (parent) parent.append(n)
  return n
}

function fitView(b, W, H) {
  if (!b || !W || !H) return null
  let [x0, y0, x1, y1] = b
  const span = Math.max(x1 - x0, y1 - y0) || 200 // a lone point still gets a sensible frame
  if (x1 - x0 < span * 0.05) { x0 -= span / 2; x1 += span / 2 }
  if (y1 - y0 < span * 0.05) { y0 -= span / 2; y1 += span / 2 }
  const s = Math.max((x1 - x0) / Math.max(W - PAD * 2, 50), (y1 - y0) / Math.max(H - PAD * 2, 50))
  return [(x0 + x1) / 2 - (W * s) / 2, (y0 + y1) / 2 - (H * s) / 2, W * s, H * s]
}

export class MapViewer {
  constructor(host, { features, geographic, onSelect, onHover }) {
    Object.assign(this, { host, features, geographic, onSelect, onHover })
    this.project = projector(geographic)
    this.selected = null
    this.hovered = null
    this.view = null
    this.nodes = new Map()

    this.root = Object.assign(document.createElement('div'), { className: 'map' })
    this.svg = el('svg', { role: 'img', 'aria-label': `Map of ${features.length} features. Use the feature table to select features by keyboard.`, preserveAspectRatio: 'none' }, this.root)
    this.gridLayer = el('g', {}, this.svg)
    this.featureLayer = el('g', {}, this.svg)
    this.overlay = el('svg', { class: 'overlay', 'aria-hidden': 'true' }, this.root)
    this.tip = Object.assign(document.createElement('div'), { className: 'map-tip', hidden: true })
    this.root.append(this.tip, this.tools())
    if (!geographic) this.root.append(Object.assign(document.createElement('p'), { className: 'map-note label', textContent: 'Source coordinates · CRS unknown' }))
    host.replaceChildren(this.root)

    this.allBox = bboxOf(features.map((f) => f.geometry).filter(Boolean), this.project)
    this.buildFeatures()
    this.bindPointer()
    this.ro = new ResizeObserver(([e]) => {
      this.W = e.contentRect.width
      this.H = e.contentRect.height
      if (this.W) this.setView(fitView(this.allBox, this.W, this.H))
    })
    this.ro.observe(this.root)
  }

  destroy() { this.ro.disconnect(); this.cancel?.() }

  tools() {
    const box = Object.assign(document.createElement('div'), { className: 'map-tools' })
    const add = (name, label, fn) => {
      const b = Object.assign(document.createElement('button'), { type: 'button', title: label, onclick: fn })
      b.setAttribute('aria-label', label)
      b.addEventListener('pointerdown', (e) => e.stopPropagation())
      b.append(icon(name))
      box.append(b)
      return b
    }
    add('plus', 'Zoom in', () => this.zoom(1 / 1.4))
    add('minus', 'Zoom out', () => this.zoom(1.4))
    add('fit', 'Fit all features', () => this.flyTo(fitView(this.allBox, this.W, this.H)))
    this.fitSelectedBtn = add('target', 'Fit selected feature', () => this.selected && this.fitFeature(this.selected))
    this.fitSelectedBtn.disabled = true
    return box
  }

  buildFeatures() {
    for (const f of this.features) {
      if (!f.geometry) continue
      const { d, points } = toSvg(f.geometry, this.project)
      const g = el('g', { 'data-id': f.feature_id, style: 'cursor:pointer' }, this.featureLayer)
      const areal = /Polygon/.test(f.geometry_type || '')
      if (d && !areal) el('path', { d, fill: 'none', stroke: 'transparent', 'stroke-width': 12, 'vector-effect': 'non-scaling-stroke', 'pointer-events': 'stroke' }, g)
      const path = d ? el('path', { d, 'fill-rule': 'evenodd', 'vector-effect': 'non-scaling-stroke' }, g) : null
      const dots = points.map(([x, y]) => el('circle', { cx: x, cy: y, 'vector-effect': 'non-scaling-stroke', 'stroke-width': 1.5 }, g))
      g.addEventListener('click', () => { if (!this.drag?.moved) this.onSelect(f.feature_id) })
      g.addEventListener('pointerenter', () => this.onHover(f.feature_id))
      g.addEventListener('pointerleave', () => this.onHover(null))
      this.nodes.set(f.feature_id, { f, g, path, dots, areal })
      this.style(f.feature_id)
    }
  }

  style(id) {
    const n = this.nodes.get(id)
    if (!n) return
    const failed = n.f.status !== 'success', sel = id === this.selected, hov = id === this.hovered
    const stroke = failed ? C.error : sel ? C.dark : C.primary
    if (n.path) {
      n.path.setAttribute('fill', n.areal ? (failed ? C.error : C.primary) : 'none')
      n.path.setAttribute('fill-opacity', n.areal ? (sel ? 0.26 : hov ? 0.18 : 0.09) : 0)
      n.path.setAttribute('stroke', stroke)
      n.path.setAttribute('stroke-width', sel ? 2.25 : hov ? 1.75 : 1.1)
      if (failed) n.path.setAttribute('stroke-dasharray', '4 3')
    }
    for (const c of n.dots) {
      c.setAttribute('fill', failed ? C.error : sel ? C.dark : '#FFFFFF')
      c.setAttribute('stroke', stroke)
    }
    if (sel) n.g.parentNode.append(n.g) // draw on top
  }

  setSelected(id, { fit = false } = {}) {
    const prev = this.selected
    this.selected = id
    this.style(prev)
    this.style(id)
    this.fitSelectedBtn.disabled = id == null
    if (fit && id != null) this.fitFeature(id)
    this.drawOverlay(true)
  }

  setHovered(id, evt) {
    const prev = this.hovered
    this.hovered = id
    this.style(prev)
    this.style(id)
    const f = this.nodes.get(id)?.f
    this.tip.hidden = !f
    if (f) {
      this.tip.replaceChildren(`#${f.feature_id} ${featureLabel(f)}`)
      const s = document.createElement('span')
      s.textContent = `${f.geometry_type} · ${f.status !== 'success' ? f.status : f.measurement ? fmtMeasurement(f.measurement) : 'no measurement'}`
      this.tip.append(s)
      if (evt) this.moveTip(evt)
    }
  }

  moveTip(e) {
    const r = this.root.getBoundingClientRect()
    this.tip.style.left = `${Math.min(e.clientX - r.left + 14, this.W - 200)}px`
    this.tip.style.top = `${e.clientY - r.top + 14}px`
  }

  fitFeature(id) {
    const n = this.nodes.get(id)
    if (n) this.flyTo(fitView(bboxOf([n.f.geometry], this.project), this.W, this.H))
  }

  flyTo(target) {
    if (!target) return
    const from = this.view
    this.cancel?.()
    if (!from || reducedMotion()) return this.setView(target)
    this.cancel = tween(500, (t) => this.setView(from.map((v, i) => v + (target[i] - v) * t)))
  }

  zoom(factor, cx = this.W / 2, cy = this.H / 2) {
    const v = this.view
    if (!v) return
    const wx = v[0] + cx * (v[2] / this.W), wy = v[1] + cy * (v[3] / this.H)
    this.setView([wx - (wx - v[0]) * factor, wy - (wy - v[1]) * factor, v[2] * factor, v[3] * factor])
  }

  setView(v) {
    if (!v) return
    this.view = v
    this.k = v[2] / this.W // world units per pixel
    this.svg.setAttribute('viewBox', v.join(' '))
    for (const n of this.nodes.values()) {
      const sel = n.f.feature_id === this.selected
      for (const c of n.dots) c.setAttribute('r', (sel ? 6 : 4.5) * this.k)
    }
    this.drawGrid()
    this.drawOverlay(false)
  }

  bindPointer() {
    this.root.addEventListener('wheel', (e) => {
      e.preventDefault()
      const r = this.root.getBoundingClientRect()
      this.zoom(e.deltaY > 0 ? 1.15 : 1 / 1.15, e.clientX - r.left, e.clientY - r.top)
    }, { passive: false })
    this.root.addEventListener('pointerdown', (e) => { this.drag = { x: e.clientX, y: e.clientY, v: this.view, moved: false } })
    this.root.addEventListener('pointermove', (e) => {
      if (this.hovered != null) this.moveTip(e)
      const d = this.drag
      if (!d) return
      const dx = e.clientX - d.x, dy = e.clientY - d.y
      if (!d.moved && Math.abs(dx) + Math.abs(dy) > 3) {
        d.moved = true
        this.root.setPointerCapture?.(e.pointerId) // only once dragging, so clicks still reach features
      }
      if (d.moved) this.setView([d.v[0] - dx * this.k, d.v[1] - dy * this.k, d.v[2], d.v[3]])
    })
    const end = () => setTimeout(() => { this.drag = null }, 0)
    this.root.addEventListener('pointerup', end)
    this.root.addEventListener('pointercancel', end)
    this.root.addEventListener('pointerleave', () => { this.tip.hidden = true })
  }

  /** Lon/lat graticule (or source units when the CRS is unknown) at a "nice" spacing, plus edge labels. */
  drawGrid() {
    const v = this.view
    const inv = this.geographic ? unproject : ([x, y]) => [x, -y]
    const [a0, b1] = inv([v[0], v[1]]), [a1, b0] = inv([v[0] + v[2], v[1] + v[3]])
    const step = niceStep(Math.max(a1 - a0, 1e-9) / 4)
    const digits = Math.max(0, -Math.floor(Math.log10(step)))
    this.lines = []
    this.gridLayer.replaceChildren()
    const line = (x1, y1, x2, y2) => el('line', { x1, y1, x2, y2, stroke: C.ink, 'stroke-opacity': 0.07, 'vector-effect': 'non-scaling-stroke' }, this.gridLayer)
    for (let i = Math.ceil(a0 / step); i * step <= a1; i++) {
      const x = this.project([i * step, (b0 + b1) / 2])[0]
      line(x, v[1], x, v[1] + v[3])
      this.lines.push({ axis: 'x', p: x, t: (i * step).toFixed(digits) })
    }
    for (let i = Math.ceil(b0 / step); i * step <= b1; i++) {
      const y = this.project([(a0 + a1) / 2, i * step])[1]
      line(v[0], y, v[0] + v[2], y)
      this.lines.push({ axis: 'y', p: y, t: (i * step).toFixed(digits) })
    }
    this.midLat = (b0 + b1) / 2
  }

  toPx([x, y]) { return [(x - this.view[0]) / this.k, (y - this.view[1]) / this.k] }

  /** Pixel-space layer: grid labels, scale bar, and the selected feature's measurement overlay. */
  drawOverlay(animate) {
    if (!this.view) return
    const o = this.overlay
    o.replaceChildren()
    const unit = this.geographic ? '°' : ''
    for (const l of this.lines || []) {
      const p = (l.p - (l.axis === 'x' ? this.view[0] : this.view[1])) / this.k
      if (p < 30) continue
      const t = el('text', { x: l.axis === 'x' ? p + 3 : 4, y: l.axis === 'x' ? 12 : p - 3, 'font-size': 9.5, fill: C.muted, 'font-family': 'JetBrains Mono, monospace' }, o)
      t.textContent = l.t + unit
    }
    if (this.geographic) {
      const mPerPx = this.k * Math.cos((this.midLat * Math.PI) / 180)
      const m = niceStep(110 * mPerPx), px = m / mPerPx
      const g = el('g', { transform: `translate(${this.W - px - 20} ${this.H - 22})` }, o)
      el('rect', { width: px, height: 4, fill: C.ink }, g)
      el('rect', { width: px / 2, height: 4, fill: '#fff', stroke: C.ink, 'stroke-width': 1 }, g)
      const t = el('text', { x: px, y: -6, 'text-anchor': 'end', 'font-size': 10, 'font-family': 'JetBrains Mono, monospace', fill: C.ink }, g)
      t.textContent = fmtDistance(m)
    }
    const n = this.nodes.get(this.selected)
    if (n) this.drawDimensions(n.f, animate)
  }

  drawDimensions(f, animate) {
    const o = this.overlay
    const b = bboxOf([f.geometry], this.project)
    const [x0, y0] = this.toPx([b[0], b[1]]), [x1, y1] = this.toPx([b[2], b[3]])
    const { d } = toSvg(f.geometry, (p) => this.toPx(this.project(p)))
    const areal = /Polygon/.test(f.geometry_type || ''), linear = /LineString|LinearRing/.test(f.geometry_type || '')
    const draw = (node, delay) => {
      if (!animate || reducedMotion()) return node
      const len = node.getTotalLength?.() || 1
      node.style.strokeDasharray = len
      node.animate([{ strokeDashoffset: len }, { strokeDashoffset: 0 }], { duration: 450, delay, easing: 'ease-out', fill: 'backwards' })
      return node
    }
    const fade = (node, delay) => {
      if (animate && !reducedMotion()) node.animate([{ opacity: 0 }, { opacity: 1 }], { duration: 250, delay, fill: 'backwards' })
      return node
    }
    if (d) draw(el('path', { d, fill: 'none', stroke: f.status !== 'success' ? C.error : C.dark, 'stroke-width': 2.5, 'stroke-linejoin': 'round' }, o), 0)
    const big = x1 - x0 > 40 && y1 - y0 > 24, off = 14
    if (areal && f.status === 'success' && big && this.geographic) {
      const midY = (b[1] + b[3]) / 2, midX = (b[0] + b[2]) / 2
      const w = haversine(unproject([b[0], midY]), unproject([b[2], midY]))
      const hgt = haversine(unproject([midX, b[1]]), unproject([midX, b[3]]))
      const attrs = { stroke: C.measure, 'stroke-width': 1, fill: 'none' }
      draw(el('path', { d: `M${x0} ${y1 + off}H${x1}M${x0} ${y1 + off - 5}v10M${x1} ${y1 + off - 5}v10`, ...attrs }, o), 350)
      draw(el('path', { d: `M${x1 + off} ${y0}V${y1}M${x1 + off - 5} ${y0}h10M${x1 + off - 5} ${y1}h10`, ...attrs }, o), 350)
      const g = fade(el('g', { 'font-family': 'JetBrains Mono, monospace', 'font-size': 10.5, fill: C.measure }, o), 600)
      el('text', { x: (x0 + x1) / 2, y: y1 + off + 14, 'text-anchor': 'middle' }, g).textContent = `← ${fmtDistance(w)} →`
      el('text', { transform: `translate(${x1 + off + 13} ${(y0 + y1) / 2}) rotate(90)`, 'text-anchor': 'middle' }, g).textContent = `← ${fmtDistance(hgt)} →`
    }
    if ((areal || linear) && f.measurement) {
      const g = fade(el('g', {}, o), 550), cx = (x0 + x1) / 2, cy = (y0 + y1) / 2
      el('rect', { x: cx - 48, y: cy - 12, width: 96, height: 22, fill: '#fff', stroke: C.dark, 'stroke-width': 1 }, g)
      el('text', { x: cx, y: cy + 3.5, 'text-anchor': 'middle', 'font-size': 11.5, 'font-weight': 600, 'font-family': 'JetBrains Mono, monospace', fill: C.dark }, g).textContent = fmtMeasurement(f.measurement)
    }
  }
}
