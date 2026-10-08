// The scroll story. Each scene has its own module and timeline, and its own ScrollTrigger drives it.
// The data comes from the server (web/story.py), so it's real pipeline results on the bundled samples.
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
  // Static version: I jump every timeline to its end state and skip the scroll animation.
  for (const [, tl] of timelines) tl.progress(1)
} else {
  gsap.registerPlugin(ScrollTrigger)
  const mm = gsap.matchMedia()
  // On wide screens I pin each scene and scrub through it.
  mm.add('(min-width: 900px)', () => {
    for (const [section, tl] of timelines) {
      ScrollTrigger.create({
        trigger: section, pin: section.querySelector('.scene__pin'), start: 'top top',
        end: section.dataset.scene === 'hero' ? '+=60%' : '+=130%', scrub: 0.6, animation: tl,
      })
    }
  })
  // On narrow screens the text and stage are stacked, so no pinning. It just scrubs while the stage passes through the screen.
  mm.add('(max-width: 899px)', () => {
    for (const [section, tl] of timelines) {
      ScrollTrigger.create({ trigger: section.querySelector('[data-stage]'), start: 'top 85%', end: 'bottom 35%', scrub: 0.6, animation: tl })
    }
  })
}
