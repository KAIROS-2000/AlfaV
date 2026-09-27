export type AppTheme = 'light' | 'dark' | 'sky' | 'forest' | 'sunset' | 'lavender' | 'sakura' | 'mint'

const THEME_KEY = 'codequest_theme'
export const DEFAULT_THEME: AppTheme = 'light'
export const THEME_CHANGE_EVENT = 'progyx:theme-change'
export const THEME_TRANSITION_DURATION_MS = 620
export const THEME_REDUCED_TRANSITION_DURATION_MS = 200
const ALL_THEMES: AppTheme[] = ['light', 'dark', 'sky', 'forest', 'sunset', 'lavender', 'sakura', 'mint']

type ThemeTransitionOptions = {
  origin?: { x: number; y: number }
  persist?: boolean
}

export function isAppTheme(value: unknown): value is AppTheme {
  return ALL_THEMES.includes(value as AppTheme)
}

export function resolveTheme(value: unknown, fallback: AppTheme = DEFAULT_THEME): AppTheme {
  return isAppTheme(value) ? value : fallback
}

export function getStoredTheme(): AppTheme | null {
  if (typeof window === 'undefined') return null
  try {
    const value = window.localStorage.getItem(THEME_KEY)
    return isAppTheme(value) ? value : null
  } catch {
    return null
  }
}

export function getDocumentTheme(): AppTheme {
  if (typeof document === 'undefined') return DEFAULT_THEME
  return resolveTheme(document.documentElement.dataset.theme)
}

export function applyTheme(theme: AppTheme = DEFAULT_THEME) {
  if (typeof document === 'undefined') return
  const nextTheme = resolveTheme(theme)
  const root = document.documentElement
  const previousTheme = resolveTheme(root.dataset.theme)

  root.dataset.theme = nextTheme
  root.style.colorScheme = nextTheme === 'dark' ? 'dark' : 'light'

  if (typeof window !== 'undefined' && previousTheme !== nextTheme) {
    window.dispatchEvent(new CustomEvent<AppTheme>(THEME_CHANGE_EVENT, { detail: nextTheme }))
  }
}

export function persistTheme(theme: AppTheme) {
  if (typeof window === 'undefined') return
  try {
    window.localStorage.setItem(THEME_KEY, theme)
  } catch {
    // Storage can be unavailable; the current page can still change theme.
  }
}

export function setTheme(theme: AppTheme, options?: { persist?: boolean }) {
  const persist = options?.persist ?? true
  const nextTheme = resolveTheme(theme)
  applyTheme(nextTheme)

  if (persist) {
    persistTheme(nextTheme)
  }
}

function prefersReducedMotion() {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false
  }

  return window.matchMedia('(prefers-reduced-motion: reduce)').matches
}

function resolveTransitionOrigin(origin?: { x: number; y: number }) {
  if (typeof window === 'undefined') return null

  return origin ?? {
    x: window.innerWidth / 2,
    y: window.innerHeight / 2,
  }
}

function getRevealRadius(origin: { x: number; y: number }) {
  if (typeof window === 'undefined') return 0

  const horizontal = Math.max(origin.x, window.innerWidth - origin.x)
  const vertical = Math.max(origin.y, window.innerHeight - origin.y)

  return Math.hypot(horizontal, vertical)
}

function clearThemeTransitionState(root: HTMLElement) {
  delete root.dataset.themeTransition
  delete root.dataset.themeTransitionTarget
}

/** True while `setThemeWithTransition` runs — hydrator must not call applyTheme/setTheme (breaks the circular wipe). */
export function isThemeViewTransitionRunning(): boolean {
  if (typeof document === 'undefined') return false
  return document.documentElement.dataset.themeTransition === 'running'
}

let pendingThemeTransition: Promise<void> | null = null

export function setThemeWithTransition(
  theme: AppTheme,
  options?: ThemeTransitionOptions,
): Promise<void> {
  // A second startViewTransition skips the first one. Queue changes so its
  // fallback and cleanup cannot overwrite a newer choice or its snapshots.
  const operation = pendingThemeTransition
    ? pendingThemeTransition.then(() => runThemeTransition(theme, options))
    : runThemeTransition(theme, options)
  const pending = operation.finally(() => {
    if (pendingThemeTransition === pending) pendingThemeTransition = null
  })
  pendingThemeTransition = pending
  return pending
}

async function runThemeTransition(
  theme: AppTheme,
  options?: ThemeTransitionOptions,
) {
  const persist = options?.persist ?? true
  const nextTheme = resolveTheme(theme)

  if (persist) {
    persistTheme(nextTheme)
  }

  if (typeof document === 'undefined') {
    applyTheme(nextTheme)
    return
  }

  const root = document.documentElement
  const currentTheme = resolveTheme(root.dataset.theme)

  if (currentTheme === nextTheme) {
    applyTheme(nextTheme)
    return
  }

  const origin = resolveTransitionOrigin(options?.origin)
  if (
    !origin ||
    typeof document.startViewTransition !== 'function' ||
    typeof root.animate !== 'function'
  ) {
    applyTheme(nextTheme)
    return
  }

  root.dataset.themeTransition = 'running'
  root.dataset.themeTransitionTarget = nextTheme

  let updateDone: Promise<unknown> | undefined
  let finished: Promise<unknown> | undefined
  let transition: ViewTransition | undefined
  try {
    transition = document.startViewTransition!.call(document, () => {
      applyTheme(nextTheme)
    })

    // Skipped transitions can reject multiple promises together. Observe all
    // of them immediately, including those we have not started awaiting yet.
    updateDone = transition.updateCallbackDone.catch(() => undefined)
    finished = transition.finished.catch(() => undefined)

    await transition.ready

    root.animate(
      {
        clipPath: [
          `circle(0px at ${origin.x}px ${origin.y}px)`,
          `circle(${getRevealRadius(origin)}px at ${origin.x}px ${origin.y}px)`,
        ],
      },
      {
        // Keep explicit theme changes visible even when the OS reduces motion.
        duration: prefersReducedMotion()
          ? THEME_REDUCED_TRANSITION_DURATION_MS
          : THEME_TRANSITION_DURATION_MS,
        easing: 'cubic-bezier(0.76, 0, 0.24, 1)',
        fill: 'both',
        pseudoElement: '::view-transition-new(root)',
      },
    )

  } catch {
    transition?.skipTransition()
    // A skipped transition still runs its update callback. Let that settle
    // before applying the fallback or allowing the next queued selection.
    await updateDone
    applyTheme(nextTheme)
  } finally {
    await finished
    clearThemeTransitionState(root)
  }
}

export function getThemeInitScript() {
  return `(() => {
    try {
      const key = ${JSON.stringify(THEME_KEY)};
      const all = ${JSON.stringify(ALL_THEMES)};
      const stored = window.localStorage.getItem(key);
      const theme = all.includes(stored) ? stored : ${JSON.stringify(DEFAULT_THEME)};
      document.documentElement.dataset.theme = theme;
      document.documentElement.style.colorScheme = (theme === 'dark') ? 'dark' : 'light';
    } catch (error) {
      document.documentElement.dataset.theme = ${JSON.stringify(DEFAULT_THEME)};
      document.documentElement.style.colorScheme = 'light';
    }
  })();`
}
