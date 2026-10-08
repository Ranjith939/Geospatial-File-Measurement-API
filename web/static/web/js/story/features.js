// 08 Many features: the 198 real parcel outlines appear in file order with a running count; the
// two that failed are drawn dashed red. The tally beside it is the stored result.
import { C, el, fitter, localMetres, makeStage, ringPath, text } from './stage.js'

export default function features({ section, stage, tl, data }) {
  const p = data.parcels
  const svg = makeStage(stage)
  const ref = [(p.bounds[0] + p.bounds[2]) / 2, (p.bounds[1] + p.bounds[3]) / 2]
  const local = localMetres(ref)
  const rings = p.outlines.map((r) => (r ? r.map(local) : null))
  const fit = fitter(rings.filter(Boolean).flat(), [40, 50, 660, 450])
  const shapes = rings.map((r, i) => {
    if (!r) return null
    const bad = p.statuses[i] !== 'success'
    return el('path', {
      d: ringPath(r.map(fit)), opacity: 0, fill: bad ? C.error : C.primary, 'fill-opacity': bad ? 0.2 : 0.12,
      stroke: bad ? C.error : C.dark, 'stroke-width': bad ? 1.5 : 0.8, 'stroke-dasharray': bad ? '4 3' : null,
    }, svg)
  }).filter(Boolean)
  const counter = text(svg, 24, 32, '', { 'font-size': 12, fill: C.ink })
  const tally = section.querySelector('[data-tally]')
  const n = shapes.length
  const state = { k: 0 }
  const render = () => {
    const k = Math.round(state.k)
    counter.textContent = `FEATURE ${String(k).padStart(3, '0')} / ${p.feature_count}`
    shapes.forEach((s, i) => s.setAttribute('opacity', i < k ? 1 : 0))
  }
  render()
  tl.to(state, { k: n, duration: 1, ease: 'none', onUpdate: render })
    .fromTo(tally, { opacity: 0, y: 12 }, { opacity: 1, y: 0, duration: 0.2 }, 0.95)
}
