import assert from 'node:assert/strict'
import test, { type TestContext } from 'node:test'

import {
  getStoredTheme,
  isThemeViewTransitionRunning,
  setThemeWithTransition,
  THEME_TRANSITION_DURATION_MS,
  THEME_REDUCED_TRANSITION_DURATION_MS,
} from './theme.ts'

function deferred() {
  let resolve!: () => void
  let reject!: (reason: Error) => void
  const promise = new Promise<void>((yes, no) => { resolve = yes; reject = no })
  return { promise, resolve, reject }
}

function browser(t: TestContext) {
  const events: Event[] = []
  const storage = new Map<string, string>()
  const animations: { frames: PropertyIndexedKeyframes; options: KeyframeAnimationOptions }[] = []
  const root = {
    dataset: { theme: 'light' } as Record<string, string>,
    style: { colorScheme: 'light' },
    animate(frames: PropertyIndexedKeyframes, options: KeyframeAnimationOptions) {
      animations.push({ frames, options })
    },
  }
  const transitions: {
    update: () => void
    ready: ReturnType<typeof deferred>
    updated: ReturnType<typeof deferred>
    finished: ReturnType<typeof deferred>
    oldTheme: string
    skipped: boolean
  }[] = []
  const documentMock = {
    documentElement: root,
    startViewTransition(update: () => void) {
      const state = {
        update() { update(); state.updated.resolve() },
        ready: deferred(), updated: deferred(), finished: deferred(),
        oldTheme: root.dataset.theme, skipped: false,
      }
      transitions.push(state)
      return {
        ready: state.ready.promise,
        updateCallbackDone: state.updated.promise,
        finished: state.finished.promise,
        skipTransition() { state.skipped = true },
      }
    },
  }
  const windowMock = {
    innerWidth: 800, innerHeight: 600,
    matchMedia: () => ({ matches: false }),
    dispatchEvent: (event: Event) => { events.push(event) },
    localStorage: {
      getItem: (key: string) => storage.get(key) ?? null,
      setItem: (key: string, value: string) => { storage.set(key, value) },
    },
  }
  for (const [key, value] of Object.entries({ window: windowMock, document: documentMock })) {
    const descriptor = Object.getOwnPropertyDescriptor(globalThis, key)
    Object.defineProperty(globalThis, key, { configurable: true, value })
    t.after(() => {
      if (descriptor) Object.defineProperty(globalThis, key, descriptor)
      else Reflect.deleteProperty(globalThis, key)
    })
  }
  return { root, windowMock, documentMock, transitions, animations, storage, events }
}

const tick = () => new Promise<void>((resolve) => setImmediate(resolve))

test('captures the old theme before updating and reveals the new snapshot from the chosen point', async (t) => {
  const env = browser(t)
  const operation = setThemeWithTransition('dark', { origin: { x: 100, y: 200 } })
  const transition = env.transitions[0]
  assert.equal(transition.oldTheme, 'light')
  assert.equal(env.root.dataset.theme, 'light')
  assert.equal(isThemeViewTransitionRunning(), true)
  transition.update()
  assert.equal(env.root.dataset.theme, 'dark')
  assert.equal(env.root.style.colorScheme, 'dark')
  assert.equal(env.animations.length, 0)
  transition.ready.resolve()
  await tick()
  assert.deepEqual(env.animations[0], {
    frames: { clipPath: ['circle(0px at 100px 200px)', `circle(${Math.hypot(700, 400)}px at 100px 200px)`] },
    options: { duration: THEME_TRANSITION_DURATION_MS, easing: 'cubic-bezier(0.76, 0, 0.24, 1)', fill: 'both', pseudoElement: '::view-transition-new(root)' },
  })
  assert.equal(isThemeViewTransitionRunning(), true)
  transition.finished.resolve()
  await operation
  assert.equal(isThemeViewTransitionRunning(), false)
  assert.equal(env.root.dataset.themeTransitionTarget, undefined)
  assert.equal(env.events.length, 1)
})

test('serializes rapid selections even when the earlier snapshot fails before its callback', async (t) => {
  const env = browser(t)
  const first = setThemeWithTransition('dark')
  const second = setThemeWithTransition('forest')
  assert.equal(env.transitions.length, 1)
  const old = env.transitions[0]
  old.ready.reject(new Error('snapshot skipped'))
  await tick()
  assert.equal(old.skipped, true)
  assert.equal(env.root.dataset.theme, 'light')
  assert.equal(env.transitions.length, 1)
  old.update()
  old.finished.resolve()
  await first
  await tick()
  assert.equal(env.transitions.length, 2)
  assert.equal(env.transitions[1].oldTheme, 'dark')
  assert.equal(env.root.dataset.themeTransitionTarget, 'forest')
  const latest = env.transitions[1]
  latest.update()
  latest.ready.resolve()
  await tick()
  latest.finished.resolve()
  await second
  assert.equal(env.root.dataset.theme, 'forest')
  assert.equal(getStoredTheme(), 'forest')
  assert.equal(isThemeViewTransitionRunning(), false)
})

test('handles all rejected transition promises without leaving stale state', async (t) => {
  const env = browser(t)
  const operation = setThemeWithTransition('sky')
  const transition = env.transitions[0]
  transition.ready.reject(new Error('ready failed'))
  transition.updated.reject(new Error('update failed'))
  transition.finished.reject(new Error('finished failed'))
  await operation
  assert.equal(env.root.dataset.theme, 'sky')
  assert.equal(isThemeViewTransitionRunning(), false)
})

test('falls back if starting or animating the transition throws', async (t) => {
  const env = browser(t)
  env.root.animate = () => { throw new Error('pseudo-element animation unsupported') }
  const operation = setThemeWithTransition('mint')
  const transition = env.transitions[0]
  transition.update()
  transition.ready.resolve()
  await tick()
  assert.equal(transition.skipped, true)
  transition.finished.resolve()
  await operation
  assert.equal(env.root.dataset.theme, 'mint')
  env.documentMock.startViewTransition = () => { throw new Error('start failed') }
  await setThemeWithTransition('sakura')
  assert.equal(env.root.dataset.theme, 'sakura')
  assert.equal(isThemeViewTransitionRunning(), false)
})

test('keeps an abbreviated circular reveal when motion is reduced and storage is denied', async (t) => {
  const env = browser(t)
  env.windowMock.matchMedia = () => ({ matches: true })
  env.windowMock.localStorage.getItem = () => { throw new Error('storage denied') }
  env.windowMock.localStorage.setItem = () => { throw new Error('storage denied') }
  assert.equal(getStoredTheme(), null)
  const operation = setThemeWithTransition('lavender')
  assert.equal(env.root.dataset.theme, 'light')
  const transition = env.transitions[0]
  transition.update()
  transition.ready.resolve()
  await tick()
  assert.equal(env.animations[0].options.duration, THEME_REDUCED_TRANSITION_DURATION_MS)
  assert.equal(env.animations[0].options.pseudoElement, '::view-transition-new(root)')
  transition.finished.resolve()
  await operation
  assert.equal(env.root.dataset.theme, 'lavender')
  assert.equal(env.transitions.length, 1)
})

test('works without view transitions and supports nonpersistent choices', async (t) => {
  const env = browser(t)
  Reflect.deleteProperty(env.documentMock, 'startViewTransition')
  await setThemeWithTransition('sunset', { persist: false })
  assert.equal(env.root.dataset.theme, 'sunset')
  assert.equal(env.storage.size, 0)
  assert.equal(env.transitions.length, 0)
})
