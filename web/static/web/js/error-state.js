// Proper error screens for each API error code. I didn't want plain generic alerts.
import { h, icon, enter } from './dom.js'

const COPY = {
  INVALID_SHAPEFILE: ['File could not be processed', 'The uploaded ZIP does not contain a valid Shapefile structure.'],
  CORRUPT_ARCHIVE: ['File could not be processed', 'The ZIP archive is corrupt or unreadable.'],
  EMPTY_ARCHIVE: ['File could not be processed', 'The ZIP archive is empty.'],
  UNSAFE_ARCHIVE: ['Archive rejected', 'The ZIP contains unsafe entries (absolute paths, "..", links or excessive size).'],
  INVALID_KML: ['File could not be processed', 'The file is not valid KML.'],
  UNSUPPORTED_FILE_TYPE: ['Unsupported file type', 'Upload a .kml file or a .zip containing a Shapefile.'],
  FILE_TOO_LARGE: ['File too large', null],
  EMPTY_FILE: ['Empty file', 'The uploaded file contains no data.'],
  NO_FEATURES: ['No features found', 'The file was read, but it contains no features.'],
  MISSING_CRS: ['CRS information unavailable', 'The source dataset does not provide a usable coordinate reference system. Measurement cannot be safely calculated.'],
  INVALID_CRS: ['CRS could not be interpreted', 'The .prj file is present but is not a coordinate reference system GDAL can read. Measurement cannot be safely calculated.'],
  UNSUPPORTED_CRS: ['Unsupported CRS', 'The CRS is not tied to the surface of the Earth (for example a local site grid), so it cannot be reprojected for measurement.'],
  MEASUREMENT_UNAVAILABLE: ['Measurement unavailable', null],
  FILE_NOT_FOUND: ['File not found', null],
  NETWORK_ERROR: ['API unreachable', null],
}

export function errorState({ code, message, details = {}, tone = 'error', actions = [] }) {
  const [title, copy] = COPY[code] || ['File could not be processed', null]
  const missing = details.missing ? Object.entries(details.missing) : []
  return enter(h(`div.alert${tone === 'warning' ? '.alert--warning' : ''}`, { role: 'alert' },
    icon('alert', 'alert__icon'),
    h('div', { style: 'min-width:0' },
      h('h2', { text: title }),
      h('p', { text: copy || message }),
      copy && message && copy !== message && h('p.muted', { style: 'font-size:14px', text: message }),
      details.expected && h('div', { style: 'margin-top:12px' },
        h('p.label', { text: 'Expected' }), h('ul', {}, details.expected.map((e) => h('li', { text: e })))),
      missing.length > 0 && h('div', { style: 'margin-top:10px' },
        h('p.label', { text: 'Missing' }), h('ul', {}, missing.map(([s, e]) => h('li', { text: `${s}: ${e.join(', ')}` })))),
      details.found?.length > 0 && missing.length === 0 && h('div', { style: 'margin-top:10px' },
        h('p.label', { text: 'Found in the archive' }), h('ul', {}, details.found.map((n) => h('li', { text: n })))),
      details.reason && h('p.mono.muted', { style: 'margin-top:8px;font-size:12px;overflow-wrap:anywhere', text: details.reason }),
      actions.length > 0 && h('div.actions', {}, actions),
    )))
}
