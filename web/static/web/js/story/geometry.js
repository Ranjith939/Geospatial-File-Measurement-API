// 03 Geometry: vertices, then edges, then a closed, filled ring. The parcel's real vertex order.
import { C, drawable, el, fitter, localMetres, makeStage, paperGrid, ringPath, text } from './stage.js'

export default function geometry({ stage, tl, data }) {
  const s = data.survey
  const svg = makeStage(stage)
  paperGrid(svg, 25, 0.04)
  const pts = s.vertices.map(localMetres(s.centroid)).map(fitter(s.vertices.map(localMetres(s.centroid))))

  const fill = el('path', { d: ringPath(pts), fill: C.primary, 'fill-opacity': 0, stroke: 'none' }, svg)
  const edges = pts.map((p, i) => {
    const q = pts[(i + 1) % pts.length]
    const e = el('path', { d: `M${p[0]} ${p[1]}L${q[0]} ${q[1]}`, stroke: C.dark, 'stroke-width': 2, 'stroke-linecap': 'round' }, svg)
    drawable(e)
    return e
  })
  const cx = pts.reduce((a, p) => a + p[0], 0) / pts.length, cy = pts.reduce((a, p) => a + p[1], 0) / pts.length
  const verts = pts.map(([x, y], i) => {
    const g = el('g', { opacity: 0 }, svg)
    el('circle', { cx: x, cy: y, r: 5, fill: '#fff', stroke: C.ink, 'stroke-width': 1.5 }, g)
    const dx = x - cx, dy = y - cy, k = 22 / Math.hypot(dx, dy)
    text(g, x + dx * k, y + dy * k + 4, `v${i + 1}`, { 'text-anchor': 'middle', fill: C.ink })
    return g
  })
  const captions = ['POINTS', 'EDGES CONNECT THE VERTICES', `POLYGON · ${pts.length} VERTICES · CLOSED RING`]
    .map((t, i) => text(svg, 24, 486, t, { 'font-size': 10.5, opacity: i ? 0 : 1 }))

  tl.to(verts, { opacity: 1, duration: 0.25, stagger: 0.06 }, 0)
    .to(captions[0], { opacity: 0, duration: 0.05 }, 0.5).to(captions[1], { opacity: 1, duration: 0.05 }, 0.5)
    .to(edges, { strokeDashoffset: 0, duration: 0.18, stagger: 0.09 }, 0.5)
    .to(captions[1], { opacity: 0, duration: 0.05 }, 1.25).to(captions[2], { opacity: 1, duration: 0.05 }, 1.25)
    .to(fill, { attr: { 'fill-opacity': 0.16 }, duration: 0.35 }, 1.25)
}
