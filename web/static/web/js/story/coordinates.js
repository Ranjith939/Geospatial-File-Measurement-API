// 04 Coordinates: a lon/lat field; the parcel slides into its true place and every vertex label reads
// its current position in the field, so at rest the labels show the real stored coordinates.
import { C, el, fitter, fmtLat, fmtLon, makeStage, ringPath, text } from './stage.js'

export default function coordinates({ section, stage, tl, data }) {
  const s = data.survey
  const svg = makeStage(stage)
  // Field in degrees, scaled so a degree of longitude is drawn cos(lat) shorter than a degree of latitude.
  const k = Math.cos((s.centroid[1] * Math.PI) / 180)
  const deg = s.vertices.map(([lon, lat]) => [lon * k, lat])
  const fit = fitter(deg, [235, 140, 465, 360])
  const toLonLat = (px) => { const [x, y] = fit.inverse(px); return [x / k, y] }

  // Graticule every 0.001° with labels on the left and top edges.
  const [lon0, lat1] = toLonLat([0, 0]), [lon1, lat0] = toLonLat([700, 500])
  const step = 0.001, grid = el('g', {}, svg)
  for (let v = Math.ceil(lon0 / step) * step; v <= lon1; v += step) {
    const [x] = fit([v * k, 0])
    el('line', { x1: x, y1: 0, x2: x, y2: 500, stroke: C.ink, 'stroke-opacity': 0.08 }, grid)
    text(grid, x + 3, 14, `${v.toFixed(3)}°`, { 'font-size': 9 })
  }
  for (let v = Math.ceil(lat0 / step) * step; v <= lat1; v += step) {
    const [, y] = fit([0, v])
    el('line', { x1: 0, y1: y, x2: 700, y2: y, stroke: C.ink, 'stroke-opacity': 0.08 }, grid)
    text(grid, 4, y - 4, `${v.toFixed(3)}°`, { 'font-size': 9 })
  }

  const pts = deg.map(fit)
  const group = el('g', {}, svg)
  el('path', { d: ringPath(pts), fill: C.primary, 'fill-opacity': 0.12, stroke: C.dark, 'stroke-width': 2 }, group)
  const labels = pts.map(([x, y], i) => {
    el('circle', { cx: x, cy: y, r: 4, fill: '#fff', stroke: C.ink, 'stroke-width': 1.5 }, group)
    const right = x > 350
    return text(group, x + (right ? 10 : -10), y + (i % 2 ? 14 : -8), '', { 'font-size': 9.5, fill: C.ink, 'text-anchor': right ? 'start' : 'end' })
  })

  const facts = section.querySelector('[data-coord-facts]')
  facts.replaceChildren(...s.vertices.slice(0, 3).map(([lon, lat], i) => {
    const d = document.createElement('div')
    d.innerHTML = `<dt>v${i + 1}</dt><dd>${fmtLon(lon)} ${fmtLat(lat)}</dd>`
    return d
  }))

  const offset = { x: -260, y: 90 }
  const render = () => {
    group.setAttribute('transform', `translate(${offset.x} ${offset.y})`)
    pts.forEach(([x, y], i) => {
      const [lon, lat] = toLonLat([x + offset.x, y + offset.y])
      labels[i].textContent = `${lon.toFixed(5)}, ${lat.toFixed(5)}`
    })
  }
  render()
  tl.to(offset, { x: 0, y: 0, duration: 1, ease: 'power2.inOut', onUpdate: render })
}
