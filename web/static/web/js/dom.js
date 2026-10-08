// Small DOM helpers: element builder, icons, count-up, entrance animation, reduced-motion check.

export const reducedMotion = () => window.matchMedia('(prefers-reduced-motion: reduce)').matches

/** h('div.panel', {attrs}, ...children): children may be strings, nodes, arrays or falsy. */
export function h(tag, attrs, ...children) {
  const [name, ...classes] = tag.split('.')
  const el = document.createElement(name || 'div')
  if (classes.length) el.className = classes.join(' ')
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue
    if (k.startsWith('on')) el.addEventListener(k.slice(2).toLowerCase(), v)
    else if (k === 'text') el.textContent = v
    else el.setAttribute(k, v === true ? '' : v)
  }
  for (const c of children.flat(Infinity)) if (c != null && c !== false) el.append(c.nodeType ? c : String(c))
  return el
}

/** Build SVG markup into a node: svg('<path d=".."/>', {viewBox}) */
export function svg(markup, attrs = {}) {
  const el = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v)
  el.innerHTML = markup
  return el
}

export function icon(name, cls = '', size = 16) {
  return svg(`<use href="#i-${name}"/>`, { 'aria-hidden': 'true', width: size, height: size, style: 'flex:none', ...(cls ? { class: cls } : {}) })
}

/** Animate el.textContent from 0 to value with an ease-out curve. Returns a cancel function. */
export function countUp(el, value, format, duration = 800) {
  if (reducedMotion() || !value) { el.textContent = format(value || 0); return () => {} }
  const start = performance.now()
  let raf
  const tick = (t) => {
    const p = Math.min(1, (t - start) / duration)
    el.textContent = format(value * (1 - (1 - p) ** 3))
    if (p < 1) raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
  return () => cancelAnimationFrame(raf)
}

/** Fade/slide an element in with the Web Animations API (no-op for reduced motion). */
export function enter(el, { y = 6, duration = 250, delay = 0 } = {}) {
  if (!reducedMotion()) {
    el.animate([{ opacity: 0, transform: `translateY(${y}px)` }, { opacity: 1, transform: 'none' }],
      { duration, delay, easing: 'cubic-bezier(.2,.7,.2,1)', fill: 'backwards' })
  }
  return el
}

/** Tween 0 -> 1 over duration, calling fn(t) each frame. */
export function tween(duration, fn, ease = (t) => 1 - (1 - t) ** 3) {
  if (reducedMotion()) { fn(1); return () => {} }
  const start = performance.now()
  let raf
  const tick = (now) => {
    const p = Math.min(1, (now - start) / duration)
    fn(ease(p))
    if (p < 1) raf = requestAnimationFrame(tick)
  }
  raf = requestAnimationFrame(tick)
  return () => cancelAnimationFrame(raf)
}
