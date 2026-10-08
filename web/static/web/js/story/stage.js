// Shared SVG helpers for the story scenes. Every stage is a 700 x 500 viewBox.
export const W = 700, H = 500
export const C = { ink: '#151716', muted: '#6B716C', line: '#DDE1DC', primary: '#2F6B4F', dark: '#1E4534', measure: '#B9772A', error: '#C34A4A', warning: '#C58A32', paper: '#F7F8F6' }
const NS = 'http://www.w3.org/2000/svg'
export const MONO = 'JetBrains Mono, ui-monospace, monospace'

export function el(name, attrs = {}, parent) {
  const n = document.createElementNS(NS, name)
  for (const [k, v] of Object.entries(attrs)) if (v != null) n.setAttribute(k, v)
  if (parent) parent.append(n)
  return n
}

export function text(parent, x, y, content, attrs = {}) {
  const t = el('text', { x, y, 'font-family': MONO, 'font-size': 11, fill: C.muted, ...attrs }, parent)
  t.textContent = content
  return t
}

export function makeStage(host) {
  const svg = el('svg', { viewBox: `0 0 ${W} ${H}`, preserveAspectRatio: 'xMidYMid meet' })
  host.replaceChildren(svg)
  return svg
}

/** Map points (x right, y up) into the box [x0, y0, x1, y1] of the stage, keeping aspect. */
export function fitter(points, box = [70, 60, 630, 440]) {
  let b = null
  for (const [x, y] of points) b = b ? [Math.min(b[0], x), Math.min(b[1], y), Math.max(b[2], x), Math.max(b[3], y)] : [x, y, x, y]
  const s = Math.min((box[2] - box[0]) / (b[2] - b[0] || 1), (box[3] - box[1]) / (b[3] - b[1] || 1))
  const ox = (box[0] + box[2]) / 2 - ((b[0] + b[2]) / 2) * s, oy = (box[1] + box[3]) / 2 + ((b[1] + b[3]) / 2) * s
  const f = ([x, y]) => [ox + x * s, oy - y * s]
  f.scale = s
  f.inverse = ([px, py]) => [(px - ox) / s, (oy - py) / s]
  return f
}

/** Equirectangular metres around a reference lon/lat: good enough to draw a parcel. */
export function localMetres(ref) {
  const k = Math.cos((ref[1] * Math.PI) / 180)
  return ([lon, lat]) => [(lon - ref[0]) * 111320 * k, (lat - ref[1]) * 110540]
}

export const ringPath = (pts) => 'M' + pts.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join('L') + 'Z'
export const linePath = (pts) => 'M' + pts.map(([x, y]) => `${x.toFixed(2)} ${y.toFixed(2)}`).join('L')

/** Prepare a stroke for a draw-on animation; returns its length. */
export function drawable(node) {
  const len = node.getTotalLength()
  node.style.strokeDasharray = `${len}`
  node.style.strokeDashoffset = `${len}`
  return len
}

export function paperGrid(svg, step = 25, opacity = 0.06) {
  const g = el('g', { stroke: C.ink }, svg)
  const o = (v) => (v % (step * 4) ? opacity * 0.5 : opacity) // every fourth line a little stronger
  for (let x = 0; x <= W; x += step) el('line', { x1: x, y1: 0, x2: x, y2: H, 'stroke-opacity': o(x) }, g)
  for (let y = 0; y <= H; y += step) el('line', { x1: 0, y1: y, x2: W, y2: y, 'stroke-opacity': o(y) }, g)
  return g
}

export const fmtLon = (v) => `${Math.abs(v).toFixed(5)}°${v >= 0 ? 'E' : 'W'}`
export const fmtLat = (v) => `${Math.abs(v).toFixed(5)}°${v >= 0 ? 'N' : 'S'}`
const nf = (d) => new Intl.NumberFormat('en-US', { minimumFractionDigits: d, maximumFractionDigits: d })
export const fmt = (v, d = 2) => nf(d).format(v)
export const fmtM = (m) => (m >= 1000 ? `${fmt(m / 1000, 2)} km` : `${fmt(m, m >= 100 ? 0 : 1)} m`)
