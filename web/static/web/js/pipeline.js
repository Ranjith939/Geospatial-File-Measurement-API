// Replays the stages the backend recorded for this upload, with their real durations.
// Processing already happened server-side; this only paces the reveal so each step is readable.
import { h, icon, reducedMotion, svg } from './dom.js'

const LABELS = {
  validating: 'Validating', extracting: 'Extracting', parsing: 'Reading features', detecting_crs: 'Detecting CRS',
  validating_geometry: 'Validating geometry', selecting_crs: 'Selecting measurement CRS', transforming: 'Transforming',
  measuring: 'Measuring', storing: 'Storing results',
}
const STEP_MS = 220

export function replayPipeline(host, file) {
  return new Promise((resolve) => {
    const stages = file.stages || []
    const items = stages.map((s) => h('li', { 'data-state': 'pending' }, h('span.tick'), LABELS[s.stage] || s.stage, h('span.ms')))
    const done = h('li', { 'data-state': 'pending' }, 'Complete', h('span.ms'))
    const glyph = pipelineGlyph()
    host.replaceChildren(h('div.pipeline', {},
      h('p.label', { text: `Processing · ${file.filename}` }),
      h('div.pipeline__grid', {}, h('ol.panel', { 'aria-live': 'polite' }, items, done), glyph.el),
      h('p.muted', { style: 'margin-top:14px;font-size:12px', text: 'Replay of the stage timings recorded by the server for this upload.' })))

    const reprojected = (file.measurement_crs || []).length > 0 // nothing is drawn as metric unless the server measured
    const show = (i) => {
      items.forEach((li, j) => {
        const s = stages[j]
        const state = j < i ? s.status : j === i ? 'running' : 'pending'
        li.dataset.state = state
        const tick = li.querySelector('.tick')
        tick.replaceChildren(...(state === 'done' ? [icon('check')] : state === 'failed' ? [icon('x')] : state === 'skipped' ? ['–'] : []))
        li.querySelector('.ms').textContent = j < i ? (s.status === 'skipped' ? 'skipped' : `${s.duration_ms?.toFixed(1)} ms`) : ''
      })
      const reached = (name) => i > stages.findIndex((s) => s.stage === name)
      glyph.set({
        parsed: reached('parsing'), crs: reached('detecting_crs'),
        projected: reprojected && reached('transforming'), measured: reprojected && reached('measuring'),
        caption: reprojected && reached('measuring') ? 'MEASURED · METRES' : reprojected && reached('transforming') ? 'PROJECTED · METRES'
          : reached('detecting_crs') ? (file.source_crs ? `${file.source_crs.type.toUpperCase()} · ${file.source_crs.code}` : 'CRS UNKNOWN · NOT MEASURED')
            : reached('parsing') ? 'FEATURES' : 'UPLOAD',
      })
      if (i >= stages.length) {
        const failed = file.status === 'failed'
        done.dataset.state = failed ? 'failed' : 'done'
        done.firstChild.textContent = failed ? '✕ Failed' : file.status === 'completed_with_errors' ? '✓ Complete · with errors' : '✓ Complete'
        done.querySelector('.ms').textContent = `${file.duration_ms?.toFixed(0)} ms total`
      }
    }

    if (reducedMotion()) { show(stages.length); return setTimeout(resolve, 0) }
    let i = 0
    show(0)
    const timer = setInterval(() => {
      show(++i)
      if (i >= stages.length) { clearInterval(timer); setTimeout(resolve, 450) }
    }, STEP_MS)
  })
}

/** FILE → geometry → coordinate grid → projected geometry → dimension lines. */
function pipelineGlyph() {
  const grid = (p) => Array.from({ length: 5 }, (_, i) => {
    const t = 40 + i * 55, top = p ? t : 150 + (t - 150) * 0.72
    return `M${top} 30L${t} 270`
  }).join('') + Array.from({ length: 5 }, (_, i) => `M40 ${40 + i * 55}L260 ${40 + i * 55}`).join('')
  const el = svg(`
    <rect x="20" y="20" width="260" height="260" fill="#fff" stroke="#DDE1DC"/>
    <path class="g-grid" d="${grid(false)}" stroke="#2F6B4F" stroke-opacity=".28" fill="none" style="opacity:0;transition:opacity .4s"/>
    <g class="g-file"><rect x="120" y="115" width="60" height="70" fill="none" stroke="#151716"/>
      <text x="150" y="155" text-anchor="middle" font-family="JetBrains Mono" font-size="12" fill="#151716">FILE</text></g>
    <path class="g-shape" d="M95 82L205 92L215 212L85 202Z" fill="#2F6B4F" fill-opacity=".08" stroke="#1E4534" stroke-width="2" style="opacity:0;transition:opacity .3s"/>
    <g class="g-dims" stroke="#B9772A" fill="none" style="opacity:0;transition:opacity .3s">
      <path d="M80 238H220M80 233v10M220 233v10"/><path d="M242 80V215M237 80h10M237 215h10"/></g>
    <text class="g-cap" x="24" y="296" font-family="JetBrains Mono" font-size="10" fill="#6B716C">UPLOAD</text>`,
  { viewBox: '0 0 300 300', 'aria-hidden': 'true', style: 'width:100%;max-width:300px;margin:0 auto' })
  const q = (s) => el.querySelector(s)
  return {
    el,
    set({ parsed, crs, projected, measured, caption }) {
      q('.g-file').style.display = parsed ? 'none' : ''
      q('.g-shape').style.opacity = parsed ? 1 : 0
      q('.g-shape').setAttribute('d', projected ? 'M80 80L220 95L205 215L95 200Z' : 'M95 82L205 92L215 212L85 202Z')
      q('.g-shape').setAttribute('fill-opacity', measured ? 0.2 : 0.08)
      q('.g-grid').style.opacity = crs ? 1 : 0
      q('.g-grid').setAttribute('d', grid(projected))
      q('.g-dims').style.opacity = measured ? 1 : 0
      q('.g-cap').textContent = caption
    },
  }
}
