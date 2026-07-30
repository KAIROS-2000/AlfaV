'use client'

import { ThemeToggleButton } from '@/components/theme-toggle-button'
import { api } from '@/lib/api'
import { useSessionUser } from '@/lib/auth-session'
import { setAnonymousSession } from '@/lib/session-store'
import { Menu, X } from 'lucide-react'
import Image from 'next/image'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
	useCallback,
	useEffect,
	useMemo,
	useRef,
	useState,
	useSyncExternalStore,
	type TouchEvent as ReactTouchEvent,
} from 'react'
import { createPortal } from 'react-dom'

type UserRole = 'student' | 'teacher' | 'parent' | 'manager' | 'admin' | 'superadmin'
type HeaderZone = 'teacher' | 'public' | 'app' | 'parent' | 'admin'

const roleSet = new Set<UserRole>(['student', 'teacher', 'parent', 'manager', 'admin', 'superadmin'])

function resolveHeaderZone(pathname: string | null): HeaderZone {
	if (pathname?.startsWith('/teacher')) return 'teacher'
	if (pathname?.startsWith('/admin') || pathname?.startsWith('/superadmin') || pathname?.startsWith('/manager'))
		return 'admin'
	if (pathname?.startsWith('/parent/') || pathname === '/parent') return 'parent'
	if (pathname === '/' || pathname === '/tournament' || pathname === '/it-career')
		return 'public'
	return 'app'
}

type NavLink = { href: string; label: string }

/** Пользовательская форма репортов на публичном маршруте. Staff-модерация — в админках. */
const BUG_HUNTER_LINK: NavLink = { href: '/bug-hunter', label: 'Баг-хантер' }

function bugHunterLinkForRole(role: UserRole | null): NavLink {
	if (role === 'admin') return { href: '/admin/bug-hunter', label: 'Баг-хантер' }
	if (role === 'superadmin') return { href: '/superadmin/bug-hunter', label: 'Баг-хантер' }
	return BUG_HUNTER_LINK
}

function isCabinetLink(link: NavLink) {
	if (
		link.href === '/dashboard' ||
		link.href === '/parent/dashboard' ||
		link.href.startsWith('/admin') ||
		link.href.startsWith('/superadmin')
	)
		return true
	if (/кабинет/i.test(link.label)) return true
	if (link.label === 'Админ' || link.label === 'Суперадмин') return true
	return false
}

function isLessonsLink(link: NavLink) {
	return link.href === '/roadmap' || link.label === 'Уроки'
}

/** Меньше число — выше приоритет (остаётся в шапке дольше). */
function navLinkPriority(link: NavLink): number {
	if (link.href === '/') return 0
	if (link.href === '/it-career') return 1
	if (isCabinetLink(link)) return 0
	if (isLessonsLink(link)) return 1
	if (link.href.includes('messages') || /сообщен/i.test(link.label)) return 2
	if (link.href.includes('bug-hunter') || /баг-хантер/i.test(link.label)) return 2
	if (link.href === '/leaderboard' || /рейтинг/i.test(link.label)) return 3
	if (link.href === '/useful' || link.label === 'Полезное') return 4
	if (link.href === '/tournament' || /турнир/i.test(link.label)) return 5
	if (link.href === '/teacher' || link.label === 'Учитель') return 2
	if (link.href.includes('/logs') || link.label === 'Логи') return 5
	if (link.href === '/parent' || /родител/i.test(link.label)) return 3
	if (link.href === '/auth/register' || link.label === 'Регистрация') return 4
	if (link.href === '/profile' || /профиль/i.test(link.label)) return 6
	return 7
}

function orderNavLinksByPriority(links: NavLink[]): NavLink[] {
	return [...links].sort((a, b) => {
		const diff = navLinkPriority(a) - navLinkPriority(b)
		if (diff !== 0) return diff
		return links.findIndex(l => l.href === a.href) - links.findIndex(l => l.href === b.href)
	})
}

const MIN_HEADER_NAV_VISIBLE = 2
const HEADER_STACKED_BELOW_PX = 1360

/** Сколько вкладок оставить в шапке по ширине (остальное — в сайдбар). */
function getHeaderVisibleCount(width: number, linkCount: number): number {
	if (linkCount <= MIN_HEADER_NAV_VISIBLE) return linkCount

	if (width >= 1080) return linkCount
	if (width >= 960) return Math.max(MIN_HEADER_NAV_VISIBLE, linkCount - 1)
	if (width >= 880) return Math.max(MIN_HEADER_NAV_VISIBLE, linkCount - 2)
	if (width >= 780) return Math.max(MIN_HEADER_NAV_VISIBLE, linkCount - 3)
	if (width >= 700) return Math.max(MIN_HEADER_NAV_VISIBLE, linkCount - 4)

	return MIN_HEADER_NAV_VISIBLE
}

function splitNavLinksByVisibleCount(
	links: NavLink[],
	visibleCount: number,
): { primary: NavLink[]; overflow: NavLink[] } {
	if (links.length === 0) {
		return { primary: [], overflow: [] }
	}

	const count = Math.max(
		MIN_HEADER_NAV_VISIBLE,
		Math.min(visibleCount, links.length),
	)
	const ordered = orderNavLinksByPriority(links)
	const primary = ordered.slice(0, count)
	const primaryHrefs = new Set(primary.map(link => link.href))
	const overflow = ordered.filter(link => !primaryHrefs.has(link.href))

	return { primary, overflow }
}

type HeaderDensity = 'normal' | 'compact-1' | 'compact-2' | 'compact-3'

type HeaderLayout = {
	width: number
	density: HeaderDensity
	useStackedNav: boolean
	useCompactShell: boolean
}

function resolveHeaderLayout(width: number): HeaderLayout {
	let density: HeaderDensity = 'normal'

	if (width >= 1280) {
		density = 'normal'
	} else if (width >= 1160) {
		density = 'compact-1'
	} else if (width >= 1040) {
		density = 'compact-2'
	} else {
		density = 'compact-3'
	}

	return {
		width,
		density,
		useStackedNav: width < HEADER_STACKED_BELOW_PX,
		useCompactShell: width < 768,
	}
}

const HEADER_LAYOUT_MQ = '(max-width: 767px)'

function subscribeHeaderLayout(onChange: () => void) {
	if (typeof window === 'undefined') return () => {}
	window.addEventListener('resize', onChange, { passive: true })
	const mq = window.matchMedia(HEADER_LAYOUT_MQ)
	mq.addEventListener('change', onChange)
	return () => {
		window.removeEventListener('resize', onChange)
		mq.removeEventListener('change', onChange)
	}
}

function getHeaderLayoutWidthSnapshot(): number {
	if (typeof window === 'undefined') {
		return 1280
	}
	return window.innerWidth
}

function getHeaderLayoutServerSnapshot(): number {
	return 1280
}

function useHeaderLayout() {
	const width = useSyncExternalStore(
		subscribeHeaderLayout,
		getHeaderLayoutWidthSnapshot,
		getHeaderLayoutServerSnapshot,
	)

	return useMemo(() => resolveHeaderLayout(width), [width])
}

export function SiteHeader() {
	const pathname = usePathname()
	const zone = resolveHeaderZone(pathname)
	const { user } = useSessionUser({ auth: 'optional' })
	const [sidebarOpen, setSidebarOpen] = useState(false)
	const [drawerPortalReady, setDrawerPortalReady] = useState(false)
	const openEdgeSwipeRef = useRef<{
		startX: number
		startY: number
		active: boolean
	} | null>(null)
	const closeSwipeRef = useRef<{
		startX: number
		startY: number
	} | null>(null)
	const role = useMemo<UserRole | null>(() => {
		const value = user?.role
		return value && roleSet.has(value as UserRole) ? (value as UserRole) : null
	}, [user])

	const isAuthenticated = Boolean(user)

	function handleLogout() {
		const confirmed = window.confirm(
			'Вы уверены, что хотите выйти из учетной записи?',
		)
		if (!confirmed) return

		void api('/auth/logout', { method: 'POST' }, 'required')
			.catch(() => undefined)
			.finally(() => {
				setAnonymousSession()
				window.location.href = '/auth/login'
			})
	}

	const bugHunterNav = useMemo(() => bugHunterLinkForRole(role), [role])

	const links = useMemo(() => {
		if (!isAuthenticated) {
			if (zone === 'public') {
				return [
					{ href: '/', label: 'Главная' },
					{ href: '/it-career', label: 'Карьера IT' },
					{ href: '/tournament', label: 'Турнир' },
					{ href: '/parent', label: 'Родителям' },
					bugHunterNav,
				]
			}
			if (zone === 'parent') {
				return [
					{ href: '/', label: 'Главная' },
					{ href: '/it-career', label: 'Карьера IT' },
					{ href: '/parent', label: 'Родителям' },
					{ href: '/auth/register', label: 'Регистрация' },
					bugHunterNav,
				]
			}
			return [
				{ href: '/', label: 'Главная' },
				{ href: '/it-career', label: 'Карьера IT' },
				{ href: '/tournament', label: 'Турнир' },
				{ href: '/parent', label: 'Родителям' },
				bugHunterNav,
			]
		}

		const secured = [
			{ href: '/dashboard', label: 'Кабинет' },
			{ href: '/messages', label: 'Сообщения' },
			bugHunterNav,
			{ href: '/roadmap', label: 'Уроки' },
			{ href: '/useful', label: 'Полезное' },
			{ href: '/leaderboard', label: 'Рейтинг' },
			{ href: '/tournament', label: 'Турнир' },
			{ href: '/profile', label: 'Профиль' },
		]

		// if (role === 'admin' || role === 'superadmin') {
		// 	return [
		// 		{ href: '/admin', label: 'Админ' },
		// 		...(role === 'superadmin'
		// 			? [{ href: '/superadmin', label: 'Суперадмин' }]
		// 			: []),
		// 		{ href: '/roadmap', label: 'Уроки' },
		// 		{ href: '/profile', label: 'Профиль' },
		// 	]
		// }

		if (role === 'admin') {
			return [
				{ href: '/admin/users', label: 'Админ' },
				{ href: '/admin/messages', label: 'Сообщения' },
				bugHunterNav,
				{ href: '/admin/logs', label: 'Логи' },
				{ href: '/roadmap', label: 'Уроки' },
				{ href: '/useful', label: 'Полезное' },
				{ href: '/tournament', label: 'Турнир' },
				{ href: '/profile', label: 'Профиль' },
			]
		} else if (role === 'superadmin') {
			return [
				{ href: '/superadmin/users', label: 'Суперадмин' },
				{ href: '/superadmin/messages', label: 'Сообщения' },
				bugHunterNav,
				{ href: '/superadmin/logs', label: 'Логи' },
				{ href: '/roadmap', label: 'Уроки' },
				{ href: '/useful', label: 'Полезное' },
				{ href: '/tournament', label: 'Турнир' },
				{ href: '/profile', label: 'Профиль' },
			]
		} else if (role === 'manager') {
			return [
				{ href: '/manager/contacts', label: 'Менеджер' },
				{ href: '/manager/broadcasts', label: 'Рассылки' },
				{ href: '/dashboard', label: 'Кабинет' },
				{ href: '/messages', label: 'Сообщения' },
				{ href: '/roadmap', label: 'Уроки' },
				{ href: '/useful', label: 'Полезное' },
				{ href: '/leaderboard', label: 'Рейтинг' },
				{ href: '/tournament', label: 'Турнир' },
				{ href: '/profile', label: 'Профиль' },
			]
		} else if (role === 'teacher') {
			return [
				{ href: '/dashboard', label: 'Кабинет' },
				{ href: '/teacher', label: 'Учитель' },
				{ href: '/messages', label: 'Сообщения' },
				bugHunterNav,
				{ href: '/roadmap', label: 'Уроки' },
				{ href: '/useful', label: 'Полезное' },
				{ href: '/leaderboard', label: 'Рейтинг' },
				{ href: '/tournament', label: 'Турнир' },
				{ href: '/profile', label: 'Профиль' },
			]
		}

		if (role === 'parent') {
			return [
				{ href: '/parent/dashboard', label: 'Семейный кабинет' },
				{ href: '/roadmap', label: 'Уроки' },
				{ href: '/useful', label: 'Полезное' },
				{ href: '/messages', label: 'Сообщения' },
				bugHunterNav,
				{ href: '/tournament', label: 'Турнир' },
				{ href: '/profile', label: 'Профиль' },
			]
		}

		if (zone === 'parent' && role === 'student') {
			return [
				{ href: '/', label: 'Главная' },
				{ href: '/dashboard', label: 'Кабинет ученика' },
				bugHunterNav,
			]
		}

		return secured
	}, [isAuthenticated, role, zone, bugHunterNav])

	const headerLayout = useHeaderLayout()

	const headerVisibleCount = useMemo(
		() => getHeaderVisibleCount(headerLayout.width, links.length),
		[headerLayout.width, links.length],
	)

	const { primary: headerPrimaryLinks, overflow: headerOverflowLinks } =
		useMemo(
			() => splitNavLinksByVisibleCount(links, headerVisibleCount),
			[links, headerVisibleCount],
		)

	const useSidebarMenu = headerOverflowLinks.length >= 1
	const useCompactShell =
		useSidebarMenu && headerLayout.useCompactShell
	const useStackedNav =
		!useCompactShell &&
		(headerLayout.useStackedNav || links.length >= 5)

	const navLinks = useSidebarMenu ? headerPrimaryLinks : links

	useEffect(() => {
		setDrawerPortalReady(true)
	}, [])

	useEffect(() => {
		setSidebarOpen(false)
	}, [pathname])

	useEffect(() => {
		if (!sidebarOpen) return
		const prev = document.body.style.overflow
		document.body.style.overflow = 'hidden'
		return () => {
			document.body.style.overflow = prev
		}
	}, [sidebarOpen])

	useEffect(() => {
		if (!sidebarOpen) return
		function onKeyDown(e: KeyboardEvent) {
			if (e.key === 'Escape') setSidebarOpen(false)
		}
		window.addEventListener('keydown', onKeyDown)
		return () => window.removeEventListener('keydown', onKeyDown)
	}, [sidebarOpen])

	useEffect(() => {
		if (!useSidebarMenu || sidebarOpen) return

		const edgePx = 44

		function onTouchStart(e: TouchEvent) {
			if (e.touches.length !== 1) return
			const t = e.touches[0]
			if (t.clientX < window.innerWidth - edgePx) return
			openEdgeSwipeRef.current = {
				startX: t.clientX,
				startY: t.clientY,
				active: true,
			}
		}

		function onTouchMove(e: TouchEvent) {
			const s = openEdgeSwipeRef.current
			if (!s?.active || e.touches.length !== 1) return
			const t = e.touches[0]
			if (Math.abs(t.clientY - s.startY) > 55) {
				s.active = false
			}
		}

		function onTouchEnd(e: TouchEvent) {
			const s = openEdgeSwipeRef.current
			openEdgeSwipeRef.current = null
			if (!s?.active || e.changedTouches.length !== 1) return
			const t = e.changedTouches[0]
			const dx = t.clientX - s.startX
			const dy = Math.abs(t.clientY - s.startY)
			if (dx < -64 && dy < 72) setSidebarOpen(true)
		}

		document.addEventListener('touchstart', onTouchStart, { passive: true })
		document.addEventListener('touchmove', onTouchMove, { passive: true })
		document.addEventListener('touchend', onTouchEnd, { passive: true })
		return () => {
			document.removeEventListener('touchstart', onTouchStart)
			document.removeEventListener('touchmove', onTouchMove)
			document.removeEventListener('touchend', onTouchEnd)
		}
	}, [useSidebarMenu, sidebarOpen])

	const onSidebarTouchStart = useCallback((e: ReactTouchEvent) => {
		if (e.touches.length !== 1) return
		const t = e.touches[0]
		closeSwipeRef.current = { startX: t.clientX, startY: t.clientY }
	}, [])

	const onSidebarTouchEnd = useCallback((e: ReactTouchEvent) => {
		const s = closeSwipeRef.current
		closeSwipeRef.current = null
		if (!s || e.changedTouches.length !== 1) return
		const t = e.changedTouches[0]
		const dx = t.clientX - s.startX
		const dy = Math.abs(t.clientY - s.startY)
		if (dx > 56 && dy < 80) setSidebarOpen(false)
	}, [])

	// const metaLabel =
	//   zone === 'public'
	//     ? '7–15 лет · проекты · уроки'
	//     : zone === 'parent'
	//       ? 'спокойный доступ для семьи'
	//       : zone === 'admin'
	//         ? 'контент · публикация · роли'
	//         : role === 'student'
	//           ? 'уроки · XP · задания'
	//           : 'единый кабинет'

	// const brandSubtitle =
	// 	zone === 'public'
	// 		? 'IT-школа с понятным маршрутом для детей и родителей'
	// 		: zone === 'parent'
	// 			? 'Семейный обзор прогресса и модулей'
	// 			: zone === 'admin'
	// 				? 'Рабочая панель платформы'
	// 				: 'Личный кабинет ученика'

	function renderNavLink(link: NavLink) {
		const isActive =
			pathname === link.href ||
			(link.href !== '/' && pathname?.startsWith(link.href))
		return (
			<Link
				key={link.href}
				href={link.href}
				className={`progyx-header__link ${isActive ? 'progyx-header__link--active' : ''}`}
			>
				{link.label}
			</Link>
		)
	}

	return (
		<header
			className={`progyx-header ${zone === 'public' ? 'progyx-header--public' : 'progyx-header--app'} progyx-header--${headerLayout.density} ${useStackedNav ? 'progyx-header--stacked' : ''} ${useCompactShell ? 'progyx-header--mobile-drawer' : ''} ${useSidebarMenu ? 'progyx-header--with-sidebar' : ''}`}
		>
			<div
				className={`progyx-header__shell ${useStackedNav ? 'progyx-header__shell--stacked' : ''} ${useCompactShell ? 'progyx-header__shell--mobile-drawer' : ''}`}
			>
				<Link
					href='/'
					className={`progyx-header__brand ${isAuthenticated ? 'progyx-header__brand--auth' : ''}`}
				>
					<Image
						src='/progyx-logo.png'
						alt='Логотип Progyx'
						width={80}
						height={80}
						className='h-14 w-14 shrink-0 object-contain sm:h-16 sm:w-16'
						priority
					/>
					<div className='progyx-header__brand-copy'>
						<span className='progyx-header__brand-tag'>Progyx</span>
						<p className='progyx-header__brand-title'>
							Образовательная платформа
						</p>
						{/* <p className='progyx-header__brand-subtitle'>{brandSubtitle}</p> */}
					</div>
				</Link>

				<nav
					className={`progyx-header__nav ${useStackedNav ? 'progyx-header__nav--stacked' : ''} ${useSidebarMenu ? 'progyx-header__nav--with-sidebar' : ''} ${useCompactShell ? 'progyx-header__nav--compact' : ''}`}
					aria-label='Основная навигация'
				>
					{navLinks.map(renderNavLink)}
				</nav>

				<div
					className={`progyx-header__actions ${isAuthenticated ? 'progyx-header__actions--auth' : 'progyx-header__actions--guest'} ${useSidebarMenu ? 'progyx-header__actions--with-menu' : ''}`}
				>
					{useSidebarMenu ? (
						<button
							type='button'
							className='progyx-header__icon-button progyx-header__icon-button--menu'
							aria-label='Открыть меню'
							aria-expanded={sidebarOpen}
							aria-controls='site-header-mobile-drawer'
							onClick={() => setSidebarOpen(true)}
						>
							<Menu className='progyx-header__icon-button-svg' strokeWidth={2.25} />
						</button>
					) : null}
					{/* <span className='progyx-header__signal'>{metaLabel}</span> */}
					<ThemeToggleButton user={user} />
					{isAuthenticated ? (
						<button
							className='progyx-header__button progyx-header__button--primary progyx-header__button--desktop-auth'
							onClick={handleLogout}
						>
							Выйти
						</button>
					) : null}
				</div>
				{!isAuthenticated ? (
					<div className='progyx-header__guest-auth'>
						<Link
							href='/auth/login'
							className='progyx-header__button progyx-header__button--ghost'
						>
							Войти
						</Link>
						<Link
							href='/auth/register'
							className='progyx-header__button progyx-header__button--primary'
						>
							<span className='progyx-header__button-label progyx-header__button-label--full'>
								Создать аккаунт
							</span>
							<span className='progyx-header__button-label progyx-header__button-label--short'>
								Регистрация
							</span>
						</Link>
					</div>
				) : null}
			</div>

			{drawerPortalReady && useSidebarMenu
				? createPortal(
						<>
							<div
								className={`progyx-header__sidebar-backdrop ${sidebarOpen ? 'progyx-header__sidebar-backdrop--open' : ''}`}
								aria-hidden={!sidebarOpen}
								onClick={() => setSidebarOpen(false)}
								onTouchStart={onSidebarTouchStart}
								onTouchEnd={onSidebarTouchEnd}
							/>
							<aside
								id='site-header-mobile-drawer'
								className={`progyx-header__sidebar-panel ${sidebarOpen ? 'progyx-header__sidebar-panel--open' : ''}`}
								aria-hidden={!sidebarOpen}
								onTouchStart={onSidebarTouchStart}
								onTouchEnd={onSidebarTouchEnd}
							>
								<div className='progyx-header__sidebar-head'>
									<p className='progyx-header__sidebar-title'>Разделы</p>
									<button
										type='button'
										className='progyx-header__icon-button progyx-header__icon-button--close'
										aria-label='Закрыть меню'
										onClick={() => setSidebarOpen(false)}
									>
										<X className='progyx-header__icon-button-svg' strokeWidth={2.25} />
									</button>
								</div>
								<nav
									className='progyx-header__sidebar-nav'
									aria-label='Дополнительная навигация'
								>
									{headerOverflowLinks.map(link => {
										const isActive =
											pathname === link.href ||
											(link.href !== '/' &&
												pathname?.startsWith(link.href))
										return (
											<Link
												key={link.href}
												href={link.href}
												className={`progyx-header__sidebar-link ${isActive ? 'progyx-header__sidebar-link--active' : ''}`}
												onClick={() => setSidebarOpen(false)}
											>
												{link.label}
											</Link>
										)
									})}
								</nav>
								{isAuthenticated ? (
									<div className='progyx-header__sidebar-foot'>
										<button
											type='button'
											className='progyx-header__sidebar-logout'
											onClick={() => {
												setSidebarOpen(false)
												handleLogout()
											}}
										>
											Выйти
										</button>
									</div>
								) : null}
							</aside>
						</>,
						document.body,
					)
				: null}
		</header>
	)
}
