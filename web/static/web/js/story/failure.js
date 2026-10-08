// 09 Failure isolation. The measuring pass walks over the real features around the first failure. The
// bad one gets put aside with its saved error while we keep measuring the rest.
import { C, el, makeStage, paperGrid, text } from './stage.js'

export default function failure({ stage, tl, data }) {
  const p = data.parcels
  const svg = makeStage(stage)
  paperGrid(svg, 25, 0.035)
  const bad = p.failures[0]
  if (!bad) return
  const ids = [-2, -1, 0, 1, 2].map((d) => bad.feature_id + d).filter((id) => id >= 1 && id <= p.feature_count)
  const rowH = 62, top = 250 - (ids.length * rowH) / 2

  const rows = ids.map((id, i) => {
    const ok = p.statuses[id - 1] === 'success'
    const g = el('g', { opacity: 0 }, svg)
    const y = top + i * rowH
    el('rect', { x: 90, y, width: 520, height: rowH - 12, fill: '#fff', stroke: C.line }, g)
    text(g, 110, y + 30, String(id).padStart(3, '0'), { 'font-size': 14, fill: C.ink })
    text(g, 170, y + 30, 'Polygon', { 'font-size': 12 })
    const mark = text(g, 588, y + 31, ok ? '✓' : '✕', { 'font-size': 16, 'text-anchor': 'end', fill: ok ? C.primary : C.error, opacity: 0 })
    const where = (bad.error.match(/-?\d+\.\d+/g) || []).map((v) => Number(v).toFixed(5)).join(', ')
    const err = ok ? null : text(g, 170, y + 44, `${bad.error.split('[')[0]}${where ? ` at ${where}` : ''}`, { 'font-size': 9.5, fill: C.error, opacity: 0 })
    return { g, ok, mark, err, frame: g.firstChild, y }
  })
  const sweep = el('rect', { x: 86, y: top - 4, width: 528, height: rowH - 4, fill: 'none', stroke: C.measure, 'stroke-width': 1.5 }, svg)
  const verdict = text(svg, 350, top + ids.length * rowH + 30, 'COMPLETED WITH ERRORS · OTHER FEATURES UNAFFECTED', { 'text-anchor': 'middle', 'font-size': 11, fill: C.warning, opacity: 0 })

  tl.to(rows.map((r) => r.g), { opacity: 1, duration: 0.2, stagger: 0.05 }, 0)
  rows.forEach((r, i) => {
    const at = 0.3 + i * 0.16
    tl.to(sweep, { attr: { y: r.y - 4 }, duration: 0.12, ease: 'power1.inOut' }, at)
      .to(r.mark, { opacity: 1, duration: 0.04 }, at + 0.12)
    if (!r.ok) {
      tl.to(r.frame, { attr: { stroke: C.error }, duration: 0.05 }, at + 0.12)
        .to(r.err, { opacity: 1, duration: 0.1 }, at + 0.14)
        .to(r.g, { x: 46, duration: 0.25, ease: 'power2.out' }, at + 0.2)
    }
  })
  tl.to(sweep, { opacity: 0, duration: 0.1 }, 0.3 + rows.length * 0.16)
    .to(verdict, { opacity: 1, duration: 0.15 }, 0.35 + rows.length * 0.16)
}
