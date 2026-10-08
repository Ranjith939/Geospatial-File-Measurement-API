// 01 Hero: a generated coordinate field; the surveyed parcel's outline draws as you begin to scroll.
import { C, drawable, el, fitter, localMetres, makeStage, paperGrid, ringPath, text } from './stage.js'

export default function hero({ stage, tl, data }) {
  const svg = makeStage(stage)
  const grid = paperGrid(svg, 25, 0.07)
  const s = data.survey
  const local = s.vertices.map(localMetres(s.centroid))
  const fit = fitter(local, [190, 120, 510, 380])
  const pts = local.map(fit)

  // Survey crosshairs at the four corners of the field, labelled with real coordinates of the parcel.
  const corners = [[60, 60], [640, 60], [60, 440], [640, 440]]
  const marks = el('g', { fill: C.muted }, svg)
  corners.forEach(([x, y], i) => {
    el('path', { d: `M${x - 7} ${y}H${x + 7}M${x} ${y - 7}V${y + 7}`, stroke: C.muted }, marks)
    const [lon, lat] = s.vertices[i % s.vertices.length]
    text(marks, x + (x < 350 ? 10 : -10), y - 8, `${lat.toFixed(4)}°, ${lon.toFixed(4)}°`, { 'font-size': 10, 'text-anchor': x < 350 ? 'start' : 'end' })
  })

  const ring = el('path', { d: ringPath(pts), fill: C.primary, 'fill-opacity': 0, stroke: C.dark, 'stroke-width': 2, 'stroke-linejoin': 'round' }, svg)
  const len = drawable(ring)
  const dots = pts.map(([x, y]) => el('circle', { cx: x, cy: y, r: 3.5, fill: '#fff', stroke: C.dark, 'stroke-width': 1.5, opacity: 0 }, svg))
  const cap = text(svg, 24, 486, `${s.filename} · ${s.properties.parcel_id || 'feature 1'}`, { 'font-size': 10.5 })

  // Initial state is already legible; scrolling completes the outline and lifts the field slightly.
  tl.set(ring, { strokeDashoffset: len * 0.62 })
    .to(ring, { strokeDashoffset: 0, duration: 1 }, 0)
    .to(ring, { attr: { 'fill-opacity': 0.12 }, duration: 0.4 }, 0.6)
    .to(dots, { opacity: 1, duration: 0.3, stagger: 0.05 }, 0.3)
    .to(grid, { y: -18, duration: 1 }, 0)
    .to(marks, { opacity: 0.4, duration: 1 }, 0)
    .to(cap, { opacity: 1, duration: 0.2 }, 0)
}
