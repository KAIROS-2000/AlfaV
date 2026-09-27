'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { Mail, MapPin, Phone } from 'lucide-react'
import { useSessionUser } from '@/lib/auth-session'
import type { PublicSiteConfig } from '@/lib/site-config'

export function SiteFooter({
	config,
	showRegisterLink = true,
}: {
	config: PublicSiteConfig
	showRegisterLink?: boolean
}) {
	const pathname = usePathname()
	const { status } = useSessionUser({ auth: 'optional' })
	/** Страницы, где не показываем ссылку регистрации в футере (как раньше на /tournament). */
	const suppressRegister = pathname?.startsWith('/tournament') ?? false
	const shouldShowRegisterLink =
		showRegisterLink && status === 'anonymous' && !suppressRegister

	const navLinks = [
		{ href: '/', label: 'Главная' },
		{ href: '/it-career', label: 'Перспективы IT' },
		{ href: '/parent', label: 'Родителям' },
		{ href: '/useful', label: 'Полезные задания' },
		{ href: '/leaderboard', label: 'Рейтинг' },
		{ href: '/support', label: 'Поддержка' },
		...(shouldShowRegisterLink
			? [{ href: '/auth/register', label: 'Создать аккаунт' }]
			: []),
	]

	const docLinks = [
		{ href: '/privacy', label: 'Политика конфиденциальности' },
		{ href: '/terms', label: 'Пользовательское соглашение' },
		{ href: '/personal-data', label: 'Обработка персональных данных' },
	]

	return (
		<footer className='site-footer' data-motion-reveal>
			<div className='site-footer__shell'>
				<div className='site-footer__grid--main'>
					<div className='site-footer__intro space-y-4'>
						<p className='brand-eyebrow'>Progyx</p>
						<h2 className='site-footer__title'>
							Маршрут, урок и прогресс в одном спокойном интерфейсе.
						</h2>
						<p className='site-footer__note'>
							Для ребёнка это понятный путь. Для семьи это прозрачная динамика
							без лишней сложности.
						</p>
					</div>

					<div className='site-footer__column'>
						<p className='site-footer__column-title'>Навигация</p>
						<nav className='site-footer__stack' aria-label='Разделы сайта'>
							{navLinks.map(link => (
								<Link key={link.href} href={link.href} className='site-footer__text-link'>
									{link.label}
								</Link>
							))}
						</nav>
					</div>

					<div className='site-footer__column'>
						<p className='site-footer__column-title'>Контакты</p>
						{config.configured ? <ul className='site-footer__contact-list'>
							{config.supportEmail ? <li>
								<a
									className='site-footer__contact-line'
									href={`mailto:${config.supportEmail}`}
								>
									<Mail className='site-footer__contact-icon' aria-hidden />
									<span>{config.supportEmail}</span>
								</a>
							</li> : null}
							{config.supportPhone && config.supportPhoneHref ? <li>
								<a
									className='site-footer__contact-line'
									href={config.supportPhoneHref}
								>
									<Phone className='site-footer__contact-icon' aria-hidden />
									<span>{config.supportPhone}</span>
								</a>
							</li> : null}
							{config.legalAddress ? <li>
								<span className='site-footer__contact-line site-footer__contact-line--static'>
									<MapPin className='site-footer__contact-icon' aria-hidden />
									<span>{config.legalAddress}</span>
								</span>
							</li> : null}
						</ul> : <p className='site-footer__note'>Контактные данные не настроены для этой среды.</p>}
					</div>

					<div className='site-footer__column'>
						<p className='site-footer__column-title'>Документы</p>
						<nav className='site-footer__stack' aria-label='Правовая информация'>
							{docLinks.map(link => (
								<Link key={link.label} href={link.href} className='site-footer__text-link'>
									{link.label}
								</Link>
							))}
						</nav>
					</div>
				</div>

				{config.configured ? <div className='site-footer__legal-block' role='region' aria-label='Реквизиты организации'>
					<p className='site-footer__legal-title'>Сведения об операторе</p>
					<dl className='site-footer__legal-dl'>
						<div>
							<dt>Наименование</dt>
							<dd>{config.legalName}</dd>
						</div>
						<div>
							<dt>ИНН</dt>
							<dd>{config.taxId}</dd>
						</div>
						<div>
							<dt>Регистрационный номер</dt>
							<dd>{config.registrationNumber}</dd>
						</div>
						<div>
							<dt>Юридический адрес</dt>
							<dd>{config.legalAddress}</dd>
						</div>
					</dl>
				</div> : null}

				<div className='site-footer__bottom'>
					<p className='site-footer__copyright'>
						© {new Date().getFullYear()} Progyx. Все права защищены.
					</p>
				</div>
			</div>
		</footer>
	)
}
