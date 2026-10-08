// 02 File: the archive opens into the components the server actually extracted (names and sizes).
import { C, el, makeStage, paperGrid, text } from './stage.js'

const ROLE = { '.shp': 'geometry', '.shx': 'index', '.dbf': 'attributes', '.prj': 'projection', '.cpg': 'encoding' }

export default function file({ stage, tl, data }) {
  const s = data.survey
  const svg = makeStage(stage)
  paperGrid(svg, 25, 0.04)
  const parts = s.components.slice(0, 6)
  const n = parts.length
  const cx = 350, cy = 250

  const links = el('g', { stroke: C.line, 'stroke-width': 1 }, svg)
  // Members fan out in a shallow arc below where the archive comes to rest (centre y = 100).
  const slots = parts.map((_, i) => {
    const u = n > 1 ? i / (n - 1) : 0.5
    return [90 + u * 520, 330 + Math.sin(u * Math.PI) * 50]
  })
  const cards = parts.map((c, i) => {
    const ext = c.name.slice(c.name.lastIndexOf('.')).toLowerCase()
    const g = el('g', { opacity: 0 }, svg)
    el('rect', { x: -52, y: -30, width: 104, height: 60, fill: '#fff', stroke: C.ink }, g)
    text(g, 0, -4, ext.toUpperCase(), { 'text-anchor': 'middle', 'font-size': 15, fill: C.ink, 'font-weight': 500 })
    text(g, 0, 14, `${ROLE[ext] || 'metadata'} · ${c.size} B`, { 'text-anchor': 'middle', 'font-size': 9.5 })
    g.setAttribute('transform', `translate(${cx} ${cy})`)
    const line = el('line', { x1: cx, y1: cy, x2: cx, y2: cy }, links)
    return { g, line, to: slots[i] }
  })

  const zip = el('g', {}, svg)
  el('rect', { x: cx - 92, y: cy - 62, width: 184, height: 124, fill: '#fff', stroke: C.ink, 'stroke-width': 1.5 }, zip)
  el('path', { d: `M${cx - 92} ${cy - 30}H${cx + 92}`, stroke: C.line }, zip)
  text(zip, cx - 80, cy - 42, 'ZIP ARCHIVE', { 'font-size': 10 })
  text(zip, cx, cy + 6, s.filename, { 'text-anchor': 'middle', 'font-size': 18, fill: C.ink, 'font-weight': 500 })
  text(zip, cx, cy + 30, `${s.size} bytes · ${n} members`, { 'text-anchor': 'middle', 'font-size': 10.5 })

  // Scroll: the archive shrinks and lifts, members slide out to their slots along drawn links.
  tl.to(zip, { scale: 0.62, y: -150, transformOrigin: '50% 50%', duration: 0.6, ease: 'power2.inOut' }, 0)
  cards.forEach(({ g, line, to }, i) => {
    const proxy = { t: 0 }
    tl.to(proxy, {
      t: 1, duration: 0.55, ease: 'power2.out',
      onUpdate: () => {
        const x = cx + (to[0] - cx) * proxy.t, y = 140 + (to[1] - 140) * proxy.t
        g.setAttribute('transform', `translate(${x} ${y})`)
        line.setAttribute('x1', cx); line.setAttribute('y1', 140)
        line.setAttribute('x2', x); line.setAttribute('y2', y - 30)
      },
    }, 0.35 + i * 0.08).to(g, { opacity: 1, duration: 0.2 }, 0.35 + i * 0.08)
  })
}
