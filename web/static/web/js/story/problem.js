// 05 The CRS problem: one degree of longitude is not a fixed length. Real values from cos(latitude).
import { C, el, fmt, makeStage, paperGrid, text } from './stage.js'

export default function problem({ section, stage, tl, data }) {
  const s = data.survey
  const svg = makeStage(stage)
  paperGrid(svg, 25, 0.035)
  section.querySelector('[data-deg-area]').textContent = `${s.area_deg2.toExponential(3)} deg² ← not an area`

  const entries = Object.entries(s.deg_lon_m).map(([lat, m]) => [Number(lat), m]).sort((a, b) => a[0] - b[0])
  const max = entries[0][1]
  text(svg, 60, 70, 'LENGTH OF 1° OF LONGITUDE', { 'font-size': 11, fill: C.ink })
  const bars = entries.map(([lat, m], i) => {
    const y = 120 + i * 92, here = Math.abs(lat - s.centroid[1]) < 0.01
    text(svg, 60, y - 10, here ? `at ${lat.toFixed(2)}° — this parcel` : `at ${lat}°`, { 'font-size': 11, fill: here ? C.primary : C.muted })
    el('rect', { x: 60, y, width: 580, height: 26, fill: C.paper, stroke: C.line }, svg)
    const bar = el('rect', { x: 60, y, width: 0, height: 26, fill: here ? C.primary : C.ink, 'fill-opacity': here ? 0.85 : 0.75 }, svg)
    const label = text(svg, 640, y + 46, `${fmt(m / 1000, 2)} km`, { 'text-anchor': 'end', 'font-size': 12, fill: C.ink, opacity: 0 })
    return { bar, label, w: (580 * m) / max }
  })
  const warn = el('g', { opacity: 0 }, svg)
  el('rect', { x: 60, y: 410, width: 580, height: 50, fill: '#fff', stroke: C.error, 'stroke-opacity': 0.6 }, warn)
  text(warn, 76, 440, `planar area in degrees = ${s.area_deg2.toExponential(3)} deg²  →  meaningless`, { 'font-size': 12, fill: C.error })

  bars.forEach(({ bar, label, w }, i) => {
    tl.to(bar, { attr: { width: w }, duration: 0.5, ease: 'power2.out' }, i * 0.2).to(label, { opacity: 1, duration: 0.2 }, i * 0.2 + 0.3)
  })
  tl.to(warn, { opacity: 1, duration: 0.3 }, 0.9)
}
