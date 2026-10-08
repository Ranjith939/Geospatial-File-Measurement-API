// Scroll story: one module and one timeline per scene, each driven by its own ScrollTrigger.
// Data comes from the server (web/story.py), i.e. from real pipeline results on bundled samples.
import { reducedMotion } from '../dom.js'
import hero from './hero.js'
import file from './file.js'
import geometry from './geometry.js'
import coordinates from './coordinates.js'
import problem from './problem.js'
import transform from './transform.js'
import measure from './measure.js'
import features from './features.js'
import failure from './failure.js'
import workspace from './workspace.js'

const SCENES = { hero, file, geometry, coordinates, problem, transform, measure, features, failure, workspace }
const data = JSON.parse(document.getElementById('story-data').textContent)
const { gsap, ScrollTrigger } = window

const timelines = []
for (const section of document.querySelectorAll('[data-scene]')) {
  const build = SCENES[section.dataset.scene]
  const tl = gsap.timeline({ paused: true, defaults: { ease: 'none' } })
  build({ section, stage: section.querySelector('[data-stage]'), tl, data, gsap })
  timelines.push([section, tl])
}

if (reducedMotion() || !ScrollTrigger) {
  // Static scenes: every timeline shown at its final state, no scroll choreography.
  for (const [, tl] of timelines) tl.progress(1)
} else {
  gsap.registerPlugin(ScrollTrigger)
  const mm = gsap.matchMedia()
  // Wide screens: pin each scene and scrub through it.
  mm.add('(min-width: 900px)', () => {
    for (const [section, tl] of timelines) {
      ScrollTrigger.create({
        trigger: section, pin: section.querySelector('.scene__pin'), start: 'top top',
        end: section.dataset.scene === 'hero' ? '+=60%' : '+=130%', scrub: 0.6, animation: tl,
      })
    }
  })
  // Narrow screens: no pinning (text and stage are stacked); scrub while the stage crosses the viewport.
  mm.add('(max-width: 899px)', () => {
    for (const [section, tl] of timelines) {
      ScrollTrigger.create({ trigger: section.querySelector('[data-stage]'), start: 'top 85%', end: 'bottom 35%', scrub: 0.6, animation: tl })
    }
  })
}
