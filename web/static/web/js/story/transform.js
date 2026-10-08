// 06 Transform the space, the main scene. PyProj reprojected the grid around the UTM zone on the
// server. Here I just move each point between its degree position and its metre position.
import { C, el, fitter, fmt, fmtLat, fmtLon, makeStage, text } from './stage.js'

export default function transform({ section, stage, tl, data }) {
  const s = data.survey, g = data.graticule
  const svg = makeStage(stage)
  const box = [110, 60, 640, 440]
  const degPts = g.degrees.flat(), mPts = g.metres.flat()
  const fd = fitter(degPts, box), fm = fitter(mPts, box)

  // Where the parcel sits in both spaces. Centroid in degrees, and the average of the projected vertices in metres.
  const cM = s.vertices_m.reduce((a, p) => [a[0] + p[0] / s.vertices_m.length, a[1] + p[1] / s.vertices_m.length], [0, 0])
  const pd = fd(s.centroid), pm = fm(cM)

  const lines = g.degrees.map((line, i) => {
    const meridian = i < g.meridians, lon = meridian ? line[0][0] : null
    const edge = meridian && Math.abs(Math.abs(lon - g.central_meridian) - 3) < 1e-6
    const central = meridian && Math.abs(lon - g.central_meridian) < 1e-6
    return {
      node: el('path', {
        fill: 'none', stroke: central ? C.primary : edge ? C.measure : C.ink,
        'stroke-opacity': central || edge ? 0.9 : 0.25, 'stroke-width': central ? 1.6 : 1, 'stroke-dasharray': edge ? '5 4' : null,
      }, svg),
      a: line.map(fd), b: g.metres[i].map(fm),
    }
  })
  // The UTM zone itself (central meridian ±3°), drawn as a shaded band between its two edge meridians.
  const edgeIdx = lines.map((l, i) => (i < g.meridians && Math.abs(Math.abs(g.degrees[i][0][0] - g.central_meridian) - 3) < 1e-6 ? i : -1)).filter((i) => i >= 0)
  const band = el('path', { fill: C.primary, 'fill-opacity': 0.07, stroke: 'none' }, svg)
  svg.insertBefore(band, svg.firstChild)
  const labels = g.degrees.map((line, i) => {
    const meridian = i < g.meridians, v = meridian ? line[0][0] : line[0][1]
    if (meridian ? (v - g.central_meridian) % 6 : false) return null
    const t = text(svg, 0, 0, `${Math.abs(v)}°${meridian ? (v >= 0 ? 'E' : 'W') : (v >= 0 ? 'N' : 'S')}`, { 'font-size': 9.5, 'text-anchor': meridian ? 'middle' : 'end' })
    return { t, i, meridian }
  }).filter(Boolean)
  const dot = el('circle', { r: 6, fill: C.dark, stroke: '#fff', 'stroke-width': 2 }, svg)
  const halo = el('circle', { r: 14, fill: 'none', stroke: C.dark, 'stroke-opacity': 0.4 }, svg)
  const from = text(svg, 24, 32, `${s.source_crs.code} · GEOGRAPHIC · DEGREES`, { 'font-size': 11, fill: C.ink })
  const to = text(svg, 24, 32, `${s.measurement_crs} · ${s.measurement_crs_name.toUpperCase()} · METRES`, { 'font-size': 11, fill: C.primary, opacity: 0 })
  text(svg, 24, 486, `${s.measurement_crs_name}: central meridian ${g.central_meridian}°, zone edges ±3° (shaded)`, { "font-size": 10 })

  const [lon, lat] = s.vertices[0], [e, n] = s.vertices_m[0]
  section.querySelector('[data-vertex-one]').textContent = `${fmtLon(lon)} ${fmtLat(lat)} → ${fmt(e)} E, ${fmt(n)} N`

  const state = { t: 0 }
  const lerp = (p, q, t) => [p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t]
  const render = () => {
    const t = state.t
    for (const l of lines) l.node.setAttribute('d', 'M' + l.a.map((p, i) => lerp(p, l.b[i], t).map((v) => v.toFixed(1)).join(' ')).join('L'))
    if (edgeIdx.length === 2) {
      const [a, b] = edgeIdx.map((i) => lines[i].a.map((p, j) => lerp(p, lines[i].b[j], t)))
      band.setAttribute('d', 'M' + [...a, ...b.reverse()].map((p) => p.map((v) => v.toFixed(1)).join(' ')).join('L') + 'Z')
    }
    for (const { t: node, i, meridian } of labels) {
      const [lx, ly] = lerp(lines[i].a[0], lines[i].b[0], t)
      node.setAttribute('x', meridian ? lx : lx - 6)
      node.setAttribute('y', meridian ? ly + 16 : ly + 3)
    }
    const [x, y] = lerp(pd, pm, t)
    dot.setAttribute('cx', x); dot.setAttribute('cy', y)
    halo.setAttribute('cx', x); halo.setAttribute('cy', y)
  }
  render()
  tl.to(state, { t: 1, duration: 1, ease: 'power1.inOut', onUpdate: render }, 0.1)
    .to(from, { opacity: 0, duration: 0.2 }, 0.55)
    .to(to, { opacity: 1, duration: 0.2 }, 0.65)
}
