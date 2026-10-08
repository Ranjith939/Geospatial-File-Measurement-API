// The 2.5D inspector. I load it with import() only when the user opens it, so nobody downloads
// Three.js otherwise. The stack model (inspector_stack.glb) is generated in code by
// D:\GLB\export_geomeasure.js, and the uploaded feature gets extruded onto its Geometry_Anchor node.
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'
import { eachPath, fmtMeasurement, featureLabel } from './geo.js'
import { h, icon, reducedMotion } from './dom.js'

const LAYERS = ['File', 'CRS', 'Geometry', 'Properties']
const GAP = 0.55
let introDone = false // the camera fly-in only plays once per page, not every time you pick a feature

/** A local frame in metres just for drawing. Equirectangular around the centre of the data, with north = -Z. */
function localFrame(geoms, geographic) {
  let b = null
  geoms.forEach((g) => eachPath(g, (cs) => cs.forEach(([x, y]) => {
    b = b ? [Math.min(b[0], x), Math.min(b[1], y), Math.max(b[2], x), Math.max(b[3], y)] : [x, y, x, y]
  })))
  if (!b) return null
  const cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2
  const kx = geographic ? 111320 * Math.cos((cy * Math.PI) / 180) : 1, ky = geographic ? 110540 : 1
  return { f: ([x, y]) => [(x - cx) * kx, (y - cy) * ky], span: Math.max((b[2] - b[0]) * kx, (b[3] - b[1]) * ky) || 1 }
}

function buildFeatures(features, selectedId, geographic, extent) {
  const group = new THREE.Group()
  group.name = 'Uploaded_Geometry'
  const frame = localFrame(features.map((f) => f.geometry), geographic)
  if (!frame) return group
  const s = extent / frame.span
  const P = (p) => { const [x, y] = frame.f(p); return [x * s, y * s] }
  for (const f of features) {
    const sel = f.feature_id === selectedId, dim = selectedId != null && !sel
    const height = sel ? 0.22 : dim ? 0.05 : 0.12 // just for looks, this isn't real elevation
    const mat = new THREE.MeshStandardMaterial({ color: f.status !== 'success' ? 0xc34a4a : sel ? 0x1e4534 : 0x2f6b4f, roughness: 0.55, transparent: dim, opacity: dim ? 0.35 : 1 })
    const rings = []
    eachPath(f.geometry, (coords, kind) => {
      if (kind === 'ring') rings.push(coords.map(P))
      else if (kind === 'line' && coords.length > 1) {
        const path = new THREE.CurvePath()
        for (let i = 1; i < coords.length; i++) {
          const [ax, ay] = P(coords[i - 1]), [bx, by] = P(coords[i])
          path.add(new THREE.LineCurve3(new THREE.Vector3(ax, 0.03, -ay), new THREE.Vector3(bx, 0.03, -by)))
        }
        group.add(new THREE.Mesh(new THREE.TubeGeometry(path, Math.max(8, coords.length * 4), sel ? 0.018 : 0.011, 6), mat))
      } else if (kind === 'point') {
        const [x, y] = P(coords[0])
        const pin = new THREE.Mesh(new THREE.CylinderGeometry(0.022, 0.022, height, 16), mat)
        pin.position.set(x, height / 2, -y)
        group.add(pin)
      }
    })
    // The first ring is the outer shell. A ring wound the other way is a hole in that shell.
    let shape = null
    for (const ring of rings) {
      const pts = ring.map(([x, y]) => new THREE.Vector2(x, y))
      if (shape && THREE.ShapeUtils.isClockWise(pts) !== THREE.ShapeUtils.isClockWise(shape.getPoints())) {
        shape.holes.push(new THREE.Path(pts))
        continue
      }
      if (shape) addShape(group, shape, height, mat)
      shape = new THREE.Shape(pts)
    }
    if (shape) addShape(group, shape, height, mat)
  }
  return group
}

function addShape(group, shape, height, material) {
  const geo = new THREE.ExtrudeGeometry(shape, { depth: height, bevelEnabled: false })
  geo.rotateX(-Math.PI / 2)
  group.add(new THREE.Mesh(geo, material),
    new THREE.LineSegments(new THREE.EdgesGeometry(geo, 30), new THREE.LineBasicMaterial({ color: 0x151716, transparent: true, opacity: 0.35 })))
}

export function mountInspector(host, { file, features, selected }) {
  let renderer
  try {
    renderer = new THREE.WebGLRenderer({ antialias: true })
  } catch {
    host.replaceChildren(h('p.viz__fallback', { text: 'WebGL is not available in this browser. The 2D map and the feature table show the same information.' }))
    return { destroy() {} }
  }
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.outputColorSpace = THREE.SRGBColorSpace

  const src = file.source_crs, props = Object.keys((selected || features[0])?.properties || {})
  const info = {
    File: [file.filename, `${file.format} · ${(file.file_size / 1024).toFixed(1)} KB`],
    CRS: [src?.code || 'CRS unknown', file.measurement_crs?.length ? `→ ${file.measurement_crs.join(', ')}` : 'not transformed'],
    Geometry: selected
      ? [`${selected.geometry_type} #${selected.feature_id}`, selected.measurement ? fmtMeasurement(selected.measurement) : selected.status !== 'success' ? 'measurement failed' : 'no measurement']
      : [`${file.feature_count} features`, Object.keys(file.geometry_types || {}).join(', ')],
    Properties: [`${props.length} attributes`, props.slice(0, 3).join(', ')],
  }
  const tags = Object.fromEntries(LAYERS.map((n) => [n, h('div.inspector__tag', {}, h('div', {},
    h('p.label', { style: 'color:var(--ink)', text: n }), h('p', { text: info[n][0] }), h('p.mono', { text: info[n][1] })))]))
  const toggle = h('button.btn', { type: 'button', 'aria-pressed': 'false' }, icon('layers'), h('span', { text: 'Inspect geometry' }))
  const box = h('div.inspector', {}, renderer.domElement,
    h('div.inspector__tags', { 'aria-hidden': 'true' }, Object.values(tags)),
    h('div.inspector__bar', {}, toggle),
    h('p.inspector__note', { text: `Visualization only · extrusion height is not elevation${selected ? ` · ${featureLabel(selected)}` : ''}` }))
  host.replaceChildren(box)

  const scene = new THREE.Scene()
  scene.background = new THREE.Color(0xf7f8f6)
  scene.add(new THREE.HemisphereLight(0xffffff, 0xdde1dc, 2.1))
  const sun = new THREE.DirectionalLight(0xffffff, 1.6)
  sun.position.set(3, 6, 2)
  scene.add(sun)
  const camera = new THREE.PerspectiveCamera(32, 1, 0.05, 50)
  const controls = new OrbitControls(camera, renderer.domElement)
  Object.assign(controls, { enableDamping: true, maxPolarAngle: Math.PI * 0.47, minDistance: 2, maxDistance: 9 })
  controls.target.set(0, 0.5, 0)

  const end = new THREE.Vector3(3.6, 3.1, 4.1), start = new THREE.Vector3(0.01, 6.5, 0.4)
  const fly = !reducedMotion() && !introDone
  camera.position.copy(fly ? start : end)
  const intro = { t: fly ? 0 : 1 }
  const layers = {}
  const state = { explode: 0, target: 0 }

  toggle.addEventListener('click', () => {
    state.target = state.target ? 0 : 1
    if (reducedMotion()) state.explode = state.target
    toggle.setAttribute('aria-pressed', String(!!state.target))
    toggle.querySelector('span').textContent = state.target ? 'Collapse' : 'Inspect geometry'
  })

  new GLTFLoader().load(window.GEOMEASURE.modelUrl, (gltf) => {
    scene.add(gltf.scene)
    LAYERS.forEach((n, i) => { const o = gltf.scene.getObjectByName(`Layer_${n}`); if (o) layers[n] = { o, y: o.position.y, i } })
    const anchor = gltf.scene.getObjectByName('Geometry_Anchor')
    const shown = selected ? [selected] : features.filter((f) => f.geometry)
    anchor?.add(buildFeatures(shown.slice(0, 3000), selected?.feature_id ?? null, !!file.source_crs, anchor.userData?.extent ?? 1.5))
  }, undefined, () => host.replaceChildren(h('p.viz__fallback', { text: 'The inspector model could not be loaded.' })))

  const resize = () => {
    const { width, height } = box.getBoundingClientRect()
    renderer.setSize(width, height, false)
    camera.aspect = width / Math.max(height, 1)
    camera.updateProjectionMatrix()
  }
  const ro = new ResizeObserver(resize)
  ro.observe(box)
  resize()

  const v = new THREE.Vector3()
  let raf
  const tick = () => {
    raf = requestAnimationFrame(tick)
    if (intro.t < 1) {
      intro.t = Math.min(1, intro.t + 1 / 70)
      camera.position.lerpVectors(start, end, 1 - (1 - intro.t) ** 3)
      if (intro.t === 1) introDone = true
    }
    state.explode += (state.target - state.explode) * 0.12
    for (const { o, y, i } of Object.values(layers)) o.position.y = y + state.explode * GAP * i
    controls.target.y = 0.15 + state.explode * 0.75 // keeps the whole stack in view while it opens up
    controls.update()
    renderer.render(scene, camera)
    const { width, height } = box.getBoundingClientRect()
    for (const n of LAYERS) {
      const tab = layers[n]?.o.getObjectByName(`Tab_${n}`)
      if (!tab) continue
      tab.getWorldPosition(v).project(camera)
      tags[n].style.transform = `translate(${((v.x + 1) / 2) * width}px, ${((1 - v.y) / 2) * height}px) translate(-100%, -50%)`
      tags[n].style.opacity = String(Math.max(0, state.explode * 1.4 - 0.4))
    }
  }
  tick()

  return {
    destroy() {
      cancelAnimationFrame(raf)
      ro.disconnect()
      controls.dispose()
      scene.traverse((o) => { o.geometry?.dispose(); [].concat(o.material || []).forEach((m) => m.dispose()) })
      renderer.dispose()
    },
  }
}
