// The feature explorer. A table you can use with the keyboard, with a filter, showing 100 rows per page.
import { h } from './dom.js'
import { fmtMeasurement, featureLabel } from './geo.js'

const PAGE = 100

export class FeatureTable {
  constructor(host, { features, onSelect, onHover }) {
    Object.assign(this, { features, onSelect, onHover, filter: 'all', limit: PAGE, selected: null })
    const counts = { all: features.length, success: features.filter((f) => f.status === 'success').length }
    counts.failed = counts.all - counts.success
    this.seg = h('div.seg', { role: 'group', 'aria-label': 'Filter features' },
      ['all', 'success', 'failed'].map((k) => h('button', {
        type: 'button', 'aria-pressed': String(k === 'all'), onclick: () => this.setFilter(k),
      }, `${k} `, h('span', { style: 'opacity:.6', text: counts[k] }))))
    this.body = h('tbody')
    this.empty = h('p.panel__body.muted', { hidden: true })
    this.more = h('button.more', { type: 'button', hidden: true, onclick: () => { this.limit += PAGE; this.render() } })
    host.replaceChildren(h('section.panel', { 'aria-labelledby': 'features-h' },
      h('div.panel__head', {}, h('h2.label', { id: 'features-h', style: 'color:var(--ink)', text: 'Feature explorer' }), this.seg),
      h('div.table-wrap', {}, h('table.data', {},
        h('thead', {}, h('tr', {}, ['ID', 'Name', 'Geometry', 'Measurement', 'Source CRS', 'Measurement CRS', 'Props', 'Status'].map((t) => h('th', { scope: 'col', text: t })))),
        this.body)),
      this.empty, this.more))
    this.render()
  }

  setFilter(k) {
    this.filter = k
    this.limit = PAGE
    this.seg.querySelectorAll('button').forEach((b, i) => b.setAttribute('aria-pressed', String(['all', 'success', 'failed'][i] === k)))
    this.render()
  }

  setSelected(id) {
    this.selected = id
    this.body.querySelectorAll('tr').forEach((tr) => tr.setAttribute('aria-selected', String(Number(tr.dataset.id) === id)))
  }

  render() {
    const rows = this.features.filter((f) => this.filter === 'all' || (this.filter === 'success') === (f.status === 'success'))
    this.body.replaceChildren(...rows.slice(0, this.limit).map((f) => this.row(f)))
    this.empty.hidden = rows.length > 0
    this.empty.textContent = `No ${this.filter} features.`
    const rest = rows.length - this.limit
    this.more.hidden = rest <= 0
    this.more.textContent = `Show ${Math.min(PAGE, rest)} more of ${rest}`
  }

  row(f) {
    const pick = () => this.onSelect(f.feature_id, { fromTable: true })
    const ok = f.status === 'success'
    return h('tr', {
      'data-id': f.feature_id, tabindex: 0, 'aria-selected': String(f.feature_id === this.selected),
      onclick: pick, onkeydown: (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick() } },
      onmouseenter: () => this.onHover(f.feature_id), onmouseleave: () => this.onHover(null),
    },
      h('td.mono.muted.num', { text: String(f.feature_id).padStart(2, '0') }),
      h('td', { style: 'max-width:220px;overflow:hidden;text-overflow:ellipsis', text: featureLabel(f) }),
      h('td.mono', { text: f.geometry_type || '—' }),
      h('td.mono.num', { text: ok ? fmtMeasurement(f.measurement) : '—' }),
      h('td.mono', { text: f.source_crs || '—' }),
      h('td.mono', { text: f.measurement_crs || '—' }),
      h('td.mono.num', { text: Object.keys(f.properties || {}).length }),
      h('td', {}, ok
        ? h('span.mono.ok', { style: 'font-size:11.5px', text: `✓ ${f.measurement_status.replace('_', ' ')}` })
        : h('span.mono', { class: `mono ${f.status === 'unsupported' ? 'warn' : 'bad'}`, style: 'font-size:11.5px', title: f.error, text: `✕ ${(f.error_code || f.status).toLowerCase().replaceAll('_', ' ')}` })))
  }
}
