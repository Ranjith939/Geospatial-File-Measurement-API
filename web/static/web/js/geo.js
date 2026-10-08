// Display-only geometry helpers. Measurements always come from the API; nothing here measures
// a feature. Web Mercator is used purely to draw WGS84 geometry on screen.

const R = 6378137

export function projector(geographic) {
  if (!geographic) return ([x, y]) => [x, -y] // unknown CRS: draw source coordinates as-is
  return ([lon, lat]) => {
    const phi = (Math.max(-85, Math.min(85, lat)) * Math.PI) / 180
    return [(R * lon * Math.PI) / 180, -R * Math.log(Math.tan(Math.PI / 4 + phi / 2))]
  }
}

export function unproject([x, y]) {
  return [(x / R) * (180 / Math.PI), (2 * Math.atan(Math.exp(-y / R)) - Math.PI / 2) * (180 / Math.PI)]
}

/** Visit every coordinate ring/line of a GeoJSON geometry as arrays of positions. */
export function eachPath(geom, fn) {
  if (!geom) return
  const c = geom.coordinates
  switch (geom.type) {
    case 'Point': fn([c], 'point'); break
    case 'MultiPoint': c.forEach((p) => fn([p], 'point')); break
    case 'LineString': case 'LinearRing': fn(c, 'line'); break
    case 'MultiLineString': c.forEach((l) => fn(l, 'line')); break
    case 'Polygon': c.forEach((r) => fn(r, 'ring')); break
    case 'MultiPolygon': c.forEach((p) => p.forEach((r) => fn(r, 'ring'))); break
    case 'GeometryCollection': geom.geometries.forEach((g) => eachPath(g, fn)); break
  }
}

export function toSvg(geom, project) {
  const parts = []
  const points = []
  eachPath(geom, (coords, kind) => {
    if (kind === 'point') return points.push(project(coords[0]))
    const d = coords.map((p, i) => { const [x, y] = project(p); return `${i ? 'L' : 'M'}${x.toFixed(2)} ${y.toFixed(2)}` }).join('')
    parts.push(kind === 'ring' ? d + 'Z' : d)
  })
  return { d: parts.join(''), points }
}

export function bboxOf(geoms, project) {
  let b = null
  for (const g of geoms) eachPath(g, (coords) => coords.forEach((p) => {
    const [x, y] = project(p)
    b = b ? [Math.min(b[0], x), Math.min(b[1], y), Math.max(b[2], x), Math.max(b[3], y)] : [x, y, x, y]
  }))
  return b
}

export function haversine([lon1, lat1], [lon2, lat2]) {
  const toR = Math.PI / 180, dLat = (lat2 - lat1) * toR, dLon = (lon2 - lon1) * toR
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * toR) * Math.cos(lat2 * toR) * Math.sin(dLon / 2) ** 2
  return 2 * 6371008.8 * Math.asin(Math.sqrt(a))
}

/** Pick a "nice" number (1, 2, 5 x 10^n) at or below v. */
export function niceStep(v) {
  const p = 10 ** Math.floor(Math.log10(v)), f = v / p
  return (f >= 5 ? 5 : f >= 2 ? 2 : 1) * p
}

const nf = (d) => new Intl.NumberFormat('en-US', { maximumFractionDigits: d, minimumFractionDigits: d })

export function fmtDistance(m) {
  if (m == null) return '—'
  return m >= 1000 ? `${nf(m >= 10000 ? 1 : 2).format(m / 1000)} km` : `${nf(m >= 100 ? 0 : 1).format(m)} m`
}

export function fmtArea(m2) {
  if (m2 == null) return '—'
  return m2 >= 10000 ? `${nf(2).format(m2 / 10000)} ha` : `${nf(m2 >= 100 ? 0 : 1).format(m2)} m²`
}

export function fmtMeasurement(m) {
  if (!m) return '—'
  return m.area_m2 != null ? fmtArea(m.area_m2) : fmtDistance(m.length_m)
}

export const fmtInt = (n) => new Intl.NumberFormat('en-US').format(n ?? 0)
export const fmtNum = (n, d = 2) => (n == null ? '—' : nf(d).format(n))

export function featureLabel(f) {
  const p = f.properties || {}
  return p.name || p.Name || p.NAME || p.parcel_id || (p.parcel_no && `Parcel ${p.parcel_no}`) || p.title || `Feature ${f.feature_id}`
}
