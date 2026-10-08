// Side panels: file summary (Simple), selected-feature measurement, CRS transformation, Technical mode.
import { countUp, enter, h, icon, svg } from './dom.js'
import { errorState } from './error-state.js'
import { fmtDistance, fmtInt, fmtNum, featureLabel } from './geo.js'

const STATUS_TEXT = { completed: 'Processed', completed_with_errors: 'Processed with errors', failed: 'Failed' }

function stat(label, value, { wide, small, tone } = {}) {
  const v = h(`p.stat__value${small ? '.stat__value--small' : ''}${tone ? `.${tone}` : ''}.num`)
  if (typeof value === 'function') value(v); else v.textContent = value
  return h(`div.stat${wide ? '.stat--wide' : ''}`, {}, h('p.label', { text: label }), v)
}

export function summaryPanel(file) {
  const t = file.totals || {}
  const items = []
  if (t.area_m2 > 0) items.push(stat('Total area', (el) => countUp(el, t.area_ha, (v) => `${fmtNum(v)} ha`)))
  if (t.length_m > 0) items.push(stat('Total length', (el) => countUp(el, t.length_m, fmtDistance)))
  items.push(stat('Features', (el) => countUp(el, file.feature_count, (v) => fmtInt(Math.round(v)))))
  items.push(stat('Status', STATUS_TEXT[file.status] || file.status, { small: true, tone: file.failed_count ? 'warn' : 'ok' }))
  items.push(stat('Successful', fmtInt(file.successful_count), { small: true }))
  items.push(stat('Failed', fmtInt(file.failed_count), { small: true, tone: file.failed_count ? 'bad' : '' }))
  if (items.length % 2) items[items.length - 1].classList.add('stat--wide')
  return h('div.stats', {}, items)
}

export function measurementPanel(feature, file, onClear) {
  const m = feature.measurement
  const head = h('div.panel__head', {},
    h('div', { style: 'min-width:0' }, h('p.label', { text: `Feature #${feature.feature_id}` }),
      h('p', { style: 'margin-top:2px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap', text: featureLabel(feature) })),
    h('button.btn', { type: 'button', text: 'All features', onclick: onClear }))
  let body
  if (feature.status !== 'success') {
    const others = fmtInt(file.successful_count)
    body = errorState({
      code: ['MISSING_CRS', 'INVALID_CRS', 'UNSUPPORTED_CRS'].includes(feature.error_code) ? feature.error_code : 'MEASUREMENT_UNAVAILABLE',
      tone: feature.status === 'unsupported' ? 'warning' : 'error',
      message: `${feature.error} · ${others} other features were processed successfully.`,
    })
  } else if (m) {
    const area = feature.measurement_type === 'area'
    const big = h('p.measure__big.num')
    countUp(big, area ? m.area_ha : m.length_m, area ? (v) => `${fmtNum(v, v >= 100 ? 1 : 2)} ha` : fmtDistance)
    body = h('div', {},
      h('p.label', { text: area ? 'Area' : 'Length' }), big,
      h('p.measure__sub.num', { text: area ? `${fmtNum(m.area_m2)} m²` : `${fmtNum(m.length_m)} m` }),
      enter(h('dl.measure__meta', {},
        h('div', {}, h('dt.label', { text: 'CRS' }), h('dd.mono', { style: 'margin:0', text: feature.measurement_crs })),
        h('div', {}, h('dt.label', { text: 'Geometry' }), h('dd.mono', { style: 'margin:0', text: feature.geometry_type })),
        h('div.full', {}, h('dt.label', { text: 'Projection' }), h('dd', { style: 'margin:0', text: feature.measurement_crs_name }))),
      { delay: 600 }))
  } else {
    body = h('div', {}, h('p.label', { text: 'Measurement' }),
      h('p', { style: 'margin-top:4px;font-size:20px;font-weight:500', text: 'Not required' }),
      h('p.muted', { style: 'font-size:14px;margin-top:2px', text: `${feature.geometry_type} geometry has no area or length.` }),
      h('p.mono', { style: 'margin-top:10px;font-size:13px', text: feature.source_crs || 'CRS unknown' }))
  }
  return enter(h('div.panel', {}, head, h('div.panel__body', { 'aria-live': 'polite' }, body)))
}

// Meridians converge (geographic) and straighten into a square grid (projected); same path structure.
function gridPath(projected) {
  const v = Array.from({ length: 7 }, (_, i) => {
    const x = 10 + i * 30, top = projected ? x : 100 + (x - 100) * 0.55
    return `M${top} 8Q${projected ? x : (top + x) / 2 + (x - 100) * 0.1} 46 ${x} 84`
  })
  const hz = Array.from({ length: 4 }, (_, i) => {
    const y = 8 + i * 25, sag = projected ? 0 : 6 - i * 1.5
    return `M10 ${y}Q100 ${y - sag} 190 ${y}`
  })
  return v.join('') + hz.join('')
}

export function crsPanel(file, names) {
  const src = file.source_crs, targets = file.measurement_crs || []
  if (!src) {
    const code = file.warnings?.some((w) => w.includes('.prj file could not')) ? 'INVALID_CRS' : 'MISSING_CRS'
    return errorState({ code, tone: 'warning', message: 'Features are shown in their raw source coordinates.' })
  }
  const reprojected = targets.length > 0 && !(targets.length === 1 && targets[0] === src.code)
  const block = (title, code, name, sub) => h('div.panel.crs__block', {}, h('p.label', { text: title }),
    h('p.crs__code', { text: code }), h('p', { style: 'font-size:14px', text: name }), h('p.label', { style: 'margin-top:2px;text-transform:none;letter-spacing:0', text: sub }))
  const path = svg(`<path d="${gridPath(false)}" fill="none" stroke="#2F6B4F" stroke-opacity=".55"/>`, { viewBox: '0 0 200 92', 'aria-hidden': 'true' })
  const root = h('div.crs', {},
    block('Input', src.code, src.name, `${src.type}${src.units ? ` · ${src.units}` : ''}`),
    h('div.crs__morph', {}, path, h('p.label', { style: 'margin-top:6px', text: reprojected ? '↓ Transform · degrees → metres' : src.type === 'projected' ? 'Source CRS is metric · no transform' : 'No measurable features' })),
    targets.length > 0 && block('Measurement CRS', targets.join(', '), targets.map((t) => names[t] || t).join(', '), `projected · ${targets.length > 1 ? 'UTM zone per feature' : 'metre'}`),
    targets.length > 0 && h('p.crs__ready', {}, icon('check'), 'Measurement ready'))
  // Morph the grid when the panel scrolls into view: the coordinate space changes, the data does not.
  new IntersectionObserver(([e], obs) => {
    if (!e.isIntersecting) return
    obs.disconnect()
    root.classList.add('is-in')
    if (!reprojected) return
    const p = path.querySelector('path')
    const anim = p.animate?.([{ d: `path("${gridPath(false)}")` }, { d: `path("${gridPath(true)}")` }], { duration: 900, delay: 200, easing: 'cubic-bezier(.3,0,.2,1)', fill: 'forwards' })
    if (!anim) p.setAttribute('d', gridPath(true))
  }).observe(root)
  return root
}

export function technicalPanel(file, feature) {
  const src = file.source_crs, m = feature?.measurement
  const geo = m?.geodesic_value, value = feature?.value
  const delta = geo && value ? ((value - geo) / geo) * 100 : null
  const unit = feature?.unit
  const section = (title, rows) => h('section', {}, h('h3', { text: title }),
    h('dl.kv', {}, rows.filter(Boolean).map(([k, v]) => [h('dt', { text: k }), h('dd', { text: v ?? '—' })])))
  return h('div.panel.tech', {},
    section('Input', [
      ['Format', file.format], ['File', `${file.filename} · ${(file.file_size / 1024).toFixed(1)} KB`],
      ['CRS', src ? `${src.code} · ${src.name}` : 'unknown'],
      ['Geometry', Object.entries(file.geometry_types || {}).map(([k, v]) => `${k} ×${v}`).join(', ')],
      file.layers?.length > 0 && ['Layers', file.layers.join(', ')],
      file.components?.length > 1 && ['Components', file.components.map((c) => c.name.split('/').pop()).join(', ')],
    ]),
    section('Transformation', [
      ['Target CRS', (file.measurement_crs || []).join(', ') || 'none'],
      ['Rule', src?.type === 'projected' && file.measurement_crs?.[0] === src.code ? 'projected source kept' : 'UTM zone of feature centroid'],
    ]),
    section('Measurement', [
      ['Method', 'Planar, in projected CRS'], ['Units', 'm² (area) · m (length)'],
      feature && ['Feature', `#${feature.feature_id} · ${feature.geometry_type}`],
      value != null && ['Planar', `${fmtNum(value)} ${unit}`],
      geo != null && value != null && ['Geodesic check', `${fmtNum(geo)} ${unit} (Δ ${delta >= 0 ? '+' : ''}${fmtNum(delta, 3)}%)`],
      feature?.status !== 'success' && feature && ['Error', `${feature.error_code}: ${feature.error}`],
    ]),
    section('Processing', [
      ['Status', file.status], ['Features', fmtInt(file.feature_count)], ['Success', fmtInt(file.successful_count)],
      ['Failed', fmtInt(file.failed_count)], file.duration_ms != null && ['Duration', `${(file.duration_ms / 1000).toFixed(3)} s`],
      ...(file.stages || []).map((s) => [`· ${s.stage}`, s.status === 'skipped' ? 'skipped' : `${s.duration_ms} ms`]),
      ...(file.warnings || []).map((w, i) => [`Warning ${i + 1}`, w]),
    ]))
}
