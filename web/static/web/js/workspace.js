// The file workspace: header, 2D map or 2.5D inspector, the measurement and CRS/technical panels, and the feature explorer.
// Everything here comes from the public API, GET /api/files/{id}/ and /measurements/.
import { api } from './api.js'
import { h, icon } from './dom.js'
import { errorState } from './error-state.js'
import { fmtInt } from './geo.js'
import { MapViewer } from './map-viewer.js'
import { crsPanel, measurementPanel, summaryPanel, technicalPanel } from './panels.js'
import { FeatureTable } from './feature-table.js'
import { replayPipeline } from './pipeline.js'

const root = document.getElementById('workspace')
const fileId = root.dataset.fileId

function seg(label, options, value, onChange) {
  const g = h('div.seg', { role: 'group', 'aria-label': label })
  const set = (k) => g.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', String(b.dataset.k === k)))
  for (const [k, text] of options) g.append(h('button', { type: 'button', 'data-k': k, text, onclick: () => { set(k); onChange(k) } }))
  set(value)
  return g
}

async function main() {
  let file, data
  try {
    [file, data] = await Promise.all([api.getFile(fileId), api.getMeasurements(fileId)])
  } catch (e) {
    root.replaceChildren(h('div', { style: 'max-width:760px;margin:40px auto' },
      errorState({ code: e.code, message: e.message, actions: [h('a.btn', { href: '/#workspace', text: 'Upload a file' })] })))
    return
  }
  const params = new URLSearchParams(location.search)
  if (params.has('replay')) {
    await replayPipeline(root, file)
    history.replaceState(null, '', location.pathname)
  }
  if (file.status === 'failed') {
    root.replaceChildren(h('div', { style: 'max-width:760px;margin:40px auto;display:grid;gap:20px' },
      errorState({ code: file.error_code, message: file.error_message, actions: [h('a.btn', { href: '/#workspace', text: 'Upload another file' })] }),
      technicalPanel(file)))
    return
  }
  render(file, data.features)
}

function render(file, features) {
  const state = { mode: 'simple', view: '2d', selected: null, inspector: null }
  const names = Object.fromEntries(features.filter((f) => f.measurement_crs).map((f) => [f.measurement_crs, f.measurement_crs_name]))
  const byId = new Map(features.map((f) => [f.feature_id, f]))

  const viz = h('div.viz')
  const side = h('aside.ws-side')
  const tableHost = h('div')
  const firstFailed = features.find((f) => f.status !== 'success')

  root.replaceChildren(
    h('div.ws-head', {},
      h('div', { style: 'min-width:0' }, h('p.label', { text: `File #${file.id} · ${file.format} · ${file.crs || 'CRS unknown'}` }), h('h1', { text: file.filename })),
      h('div.ws-head__controls', {},
        h(`span.badge.badge--${file.status}`, { text: file.status.replaceAll('_', ' ') }),
        seg('Detail level', [['simple', 'Simple'], ['technical', 'Technical']], 'simple', (k) => { state.mode = k; drawSide() }),
        seg('Visualization', [['2d', '2D map'], ['3d', 'Inspect 2.5D']], '2d', (k) => { state.view = k; drawViz() }))),
    h('div.ws-grid', {},
      file.failed_count > 0 && h('div.notice', { role: 'status' }, icon('alert', 'warn'),
        h('span', {}, h('b', { text: fmtInt(file.failed_count) }), ` of ${fmtInt(file.feature_count)} features could not be measured · ${fmtInt(file.successful_count)} were processed.`),
        firstFailed && h('button.link', { type: 'button', text: `View feature #${firstFailed.feature_id}`, onclick: () => select(firstFailed.feature_id, { fromTable: true }) })),
      h('div.ws-main', {}, viz, side),
      tableHost))

  let map = null
  const table = new FeatureTable(tableHost, { features, onSelect: (id, o) => select(id, o), onHover: (id) => map?.setHovered(id) })

  function select(id, { fromTable = false } = {}) {
    state.selected = state.selected === id && !fromTable ? null : id
    map?.setSelected(state.selected, { fit: fromTable })
    table.setSelected(state.selected)
    drawSide()
    if (state.view === '3d') drawViz()
    if (fromTable) {
      const r = viz.getBoundingClientRect()
      if (r.bottom < 80 || r.top > innerHeight - 80) viz.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }

  function drawSide() {
    const f = byId.get(state.selected)
    side.replaceChildren(
      f ? measurementPanel(f, file, () => select(null, { fromTable: true })) : summaryPanel(file),
      state.mode === 'simple' ? crsPanel(file, names) : technicalPanel(file, f))
  }

  async function drawViz() {
    state.inspector?.destroy()
    state.inspector = null
    if (state.view === '2d') {
      map?.destroy()
      map = new MapViewer(viz, { features, geographic: !!file.source_crs, onSelect: (id) => select(id), onHover: (id) => map.setHovered(id) })
      map.setSelected(state.selected)
      return
    }
    map?.destroy()
    map = null
    viz.replaceChildren(h('p.viz__fallback.label', { role: 'status', text: 'Loading 2.5D inspector…' }))
    try {
      const { mountInspector } = await import('./inspector.js')
      if (state.view === '3d') state.inspector = mountInspector(viz, { file, features, selected: byId.get(state.selected) || null })
    } catch {
      viz.replaceChildren(h('p.viz__fallback', { text: 'The 2.5D inspector could not be loaded. The 2D map shows the same data.' }))
    }
  }

  drawSide()
  drawViz()
}

main()
