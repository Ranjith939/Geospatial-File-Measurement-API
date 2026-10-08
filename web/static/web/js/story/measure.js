// 07 Measure. The parcel in projected metres (real UTM vertices), dimension lines with their real
// lengths, and the area counting up to the value the backend saved.
import { C, drawable, el, fitter, fmt, fmtM, makeStage, paperGrid, ringPath, text } from './stage.js'

export default function measure({ section, stage, tl, data }) {
  const s = data.survey
  const svg = makeStage(stage)
  paperGrid(svg, 25, 0.05)
  const fit = fitter(s.vertices_m, [140, 90, 560, 390])
  const pts = s.vertices_m.map(fit)
  const xs = s.vertices_m.map((p) => p[0]), ys = s.vertices_m.map((p) => p[1])
  const width = Math.max(...xs) - Math.min(...xs), height = Math.max(...ys) - Math.min(...ys)
  const px = pts.map((p) => p[0]), py = pts.map((p) => p[1])
  const [x0, x1, y0, y1] = [Math.min(...px), Math.max(...px), Math.min(...py), Math.max(...py)]

  el('path', { d: ringPath(pts), fill: C.primary, 'fill-opacity': 0.14, stroke: C.dark, 'stroke-width': 2 }, svg)
  const dims = [
    el('path', { d: `M${x0} ${y1 + 26}H${x1}M${x0} ${y1 + 20}v12M${x1} ${y1 + 20}v12`, stroke: C.measure, fill: 'none' }, svg),
    el('path', { d: `M${x1 + 26} ${y0}V${y1}M${x1 + 20} ${y0}h12M${x1 + 20} ${y1}h12`, stroke: C.measure, fill: 'none' }, svg),
  ]
  dims.forEach(drawable)
  const dimText = el('g', { opacity: 0, 'font-size': 11, fill: C.measure }, svg)
  text(dimText, (x0 + x1) / 2, y1 + 44, `← ${fmtM(width)} →`, { 'text-anchor': 'middle', fill: C.measure })
  text(dimText, 0, 0, `← ${fmtM(height)} →`, { 'text-anchor': 'middle', fill: C.measure, transform: `translate(${x1 + 44} ${(y0 + y1) / 2}) rotate(90)` })

  const badge = el('g', { opacity: 0 }, svg)
  const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2
  el('rect', { x: cx - 70, y: cy - 18, width: 140, height: 34, fill: '#fff', stroke: C.dark }, badge)
  const value = text(badge, cx, cy + 5, '0 ha', { 'text-anchor': 'middle', 'font-size': 16, fill: C.dark, 'font-weight': 600 })
  text(svg, 24, 486, `${s.measurement_crs} · E/N in metres · planar`, { 'font-size': 10.5 })

  const area = section.querySelector('[data-area]'), m2 = section.querySelector('[data-area-m2]')
  const length = section.querySelector('[data-length]'), geo = section.querySelector('[data-geodesic]')
  const delta = ((s.area_m2 - s.geodesic_m2) / s.geodesic_m2) * 100
  geo.textContent = `Geodesic check (WGS 84 ellipsoid): ${fmt(s.geodesic_m2)} m² · Δ ${delta >= 0 ? '+' : ''}${fmt(delta, 3)}%`
  const count = { p: 0 }
  const render = () => {
    const ha = (s.area_m2 / 10000) * count.p
    value.textContent = area.textContent = `${fmt(ha)} ha`
    m2.textContent = ` ${fmt(s.area_m2 * count.p)} m²`
    if (length && data.line) length.textContent = fmtM(data.line.length_m * count.p)
  }
  render()
  tl.to(dims, { strokeDashoffset: 0, duration: 0.4, stagger: 0.1 }, 0)
    .to(dimText, { opacity: 1, duration: 0.2 }, 0.4)
    .to(badge, { opacity: 1, duration: 0.2 }, 0.45)
    .to(count, { p: 1, duration: 0.6, ease: 'power2.out', onUpdate: render }, 0.45)
}
