// 10 Into the workspace. The pieces from the story settle into the real workspace layout (file/status/CRS
// header, map, measurement panel, feature explorer), and then the upload area comes in.
import { C, el, makeStage, paperGrid, text } from './stage.js'

const BLOCKS = [
  { label: 'FILE · STATUS · CRS', box: [40, 40, 620, 46], from: [-200, -120] },
  { label: 'MAP', box: [40, 98, 410, 250], from: [-260, 60] },
  { label: 'MEASUREMENT', box: [462, 98, 198, 120], from: [260, -40] },
  { label: 'CRS', box: [462, 228, 198, 120], from: [280, 90] },
  { label: 'FEATURE EXPLORER', box: [40, 360, 620, 100], from: [0, 220] },
]

export default function workspace({ stage, tl, data }) {
  const svg = makeStage(stage)
  paperGrid(svg, 25, 0.035)
  const s = data.survey, p = data.parcels
  const detail = {
    'FILE · STATUS · CRS': `${p.filename} · ${p.failed ? 'completed with errors' : 'completed'} · ${s.source_crs.code} → ${s.measurement_crs}`,
    MAP: `${p.feature_count} features`,
    MEASUREMENT: `${(s.area_m2 / 10000).toFixed(2)} ha`,
    CRS: s.measurement_crs,
    'FEATURE EXPLORER': `${p.successful} success · ${p.failed} failed`,
  }
  const groups = BLOCKS.map(({ label, box: [x, y, w, h], from }) => {
    const g = el('g', { opacity: 0, transform: `translate(${from[0]} ${from[1]})` }, svg)
    el('rect', { x, y, width: w, height: h, fill: '#fff', stroke: '#BFC5BE' }, g)
    text(g, x + 12, y + 20, label, { 'font-size': 10.5, fill: C.muted })
    text(g, x + 12, y + 40, detail[label], { 'font-size': 11.5, fill: C.ink })
    if (label === 'MAP') {
      for (let i = 0; i < 18; i++) {
        const cx = x + 30 + (i % 6) * 60, cy = y + 70 + Math.floor(i / 6) * 55
        el('rect', { x: cx, y: cy, width: 34 + (i * 7) % 16, height: 34 + (i * 7) % 16, fill: C.primary, 'fill-opacity': 0.12, stroke: C.dark, 'stroke-width': 0.8 }, g)
      }
    }
    return g
  })
  tl.to(groups, { opacity: 1, x: 0, y: 0, duration: 0.5, stagger: 0.08, ease: 'power3.out' })
}
