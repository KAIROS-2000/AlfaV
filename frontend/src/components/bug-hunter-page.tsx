'use client'

import Link from 'next/link'
import { useCallback, useEffect, useMemo, useState } from 'react'

import { api, getApiErrorMessage } from '@/lib/api'
import { useSessionUser } from '@/lib/auth-session'
import { showErrorToast, showSuccessToast } from '@/lib/toast'
import type { BugHunterMyReportsResponse, BugHunterSubmitResponse } from '@/types'
import { Bug, Loader2, Trophy } from 'lucide-react'

export function BugHunterPage({
	initialXpHint,
}: {
	initialXpHint?: number | null
}) {
	const { user, refresh } = useSessionUser({ auth: 'optional' })
	const [desc, setDesc] = useState('')
	const [steps, setSteps] = useState('')
	const [pathText, setPathText] = useState('')
	const [file, setFile] = useState<File | null>(null)
	const [busy, setBusy] = useState(false)
	const [history, setHistory] = useState<BugHunterMyReportsResponse | null>(null)
	const [loadingHistory, setLoadingHistory] = useState(false)

	const xpReward = history?.xp_reward_on_approval ?? initialXpHint ?? null

	const loadMine = useCallback(async () => {
		if (!user) return
		setLoadingHistory(true)
		try {
			const res = await api<BugHunterMyReportsResponse>('/support/bug-reports/me', undefined, 'required')
			setHistory(res)
		} catch (e) {
			showErrorToast(getApiErrorMessage(e, 'Не удалось загрузить историю репортов.'))
		} finally {
			setLoadingHistory(false)
		}
	}, [user])

	useEffect(() => {
		void loadMine()
	}, [loadMine])

	async function onSubmit(ev: React.FormEvent) {
		ev.preventDefault()
		if (!user) {
			showErrorToast('Войдите в аккаунт, чтобы отправить репорт.')
			return
		}
		setBusy(true)
		try {
			const fd = new FormData()
			fd.append('description', desc.trim())
			fd.append('reproduction_steps', steps.trim())
			fd.append('user_journey_path', pathText.trim())
			if (file) fd.append('screenshot', file)

			const res = await api<BugHunterSubmitResponse>(
				'/support/bug-reports',
				{ method: 'POST', body: fd },
				'required',
			)
			showSuccessToast(`${res.message} За принятый баг можно получить до ${res.xp_on_approval_preview} XP.`)
			setDesc('')
			setSteps('')
			setPathText('')
			setFile(null)
			void loadMine()
			void refresh?.()
		} catch (e) {
			showErrorToast(getApiErrorMessage(e, 'Не удалось отправить отчёт.'))
		} finally {
			setBusy(false)
		}
	}

	const moderationLabel = useMemo(
		() =>
			new Map([
				['pending', 'На модерации'],
				['approved', 'Принят'],
				['rejected', 'Отклонён'],
			]),
		[],
	)

	if (!user) {
		return (
			<section className='codequest-card mx-auto mt-10 max-w-2xl space-y-4 p-6 sm:p-8'>
				<div className='flex items-center gap-3'>
					<span className='inline-flex size-11 items-center justify-center rounded-2xl bg-amber-100 text-amber-900'>
						<Bug className='size-6' aria-hidden />
					</span>
					<div>
						<p className='brand-eyebrow'>Обратная связь</p>
						<h1 className='text-2xl font-black text-slate-900'>Баг-хантер</h1>
					</div>
				</div>
				<p className='text-sm leading-7 text-slate-600'>
					Сообщите о сбое и помогите сделать платформу надёжнее. За полезные репорты, которые примет
					команда, начисляется опыт (XP).
				</p>
				<p className='text-sm font-semibold text-slate-700'>Чтобы отправить отчёт, войдите в аккаунт.</p>
				<div className='flex flex-wrap gap-3'>
					<Link href='/auth/login' className='progyx-header__button progyx-header__button--primary'>
						Войти
					</Link>
					<Link href='/auth/register' className='progyx-header__button progyx-header__button--ghost'>
						Регистрация
					</Link>
				</div>
			</section>
		)
	}

	return (
		<div className='mx-auto w-full max-w-3xl space-y-8 px-4 py-10 sm:px-6'>
			<header className='space-y-2'>
				<p className='brand-eyebrow'>Обратная связь</p>
				<h1 className='text-3xl font-black text-slate-900'>Баг-хантер</h1>
				<p className='max-w-prose text-sm leading-7 text-slate-600'>
					Опишите ошибку и путь по платформе. По желанию приложите скриншот. XP начисляется{' '}
					<strong className='font-semibold text-slate-800'>только после одобрения модератором</strong>.
					{xpReward != null && xpReward > 0 ? (
						<span className='mt-2 flex items-center gap-2 rounded-2xl bg-violet-50 px-4 py-2 text-sm font-semibold text-violet-900 ring-1 ring-violet-200'>
							<Trophy className='size-4 shrink-0' aria-hidden />
							До {xpReward} XP за принятый репорт
						</span>
					) : null}
				</p>
			</header>

			<section className='codequest-card p-6 sm:p-8'>
				<form className='space-y-5' onSubmit={(e) => void onSubmit(e)}>
					<div className='space-y-2'>
						<label className='text-sm font-bold text-slate-800' htmlFor='bh-desc'>
							Что пошло не так
						</label>
						<textarea
							id='bh-desc'
							required
							minLength={8}
							rows={4}
							className='w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none ring-slate-900/10 focus:ring-2'
							value={desc}
							onChange={(e) => setDesc(e.target.value)}
							placeholder='Кратко: что видите или что ожидали.'
						/>
					</div>
					<div className='space-y-2'>
						<label className='text-sm font-bold text-slate-800' htmlFor='bh-steps'>
							Шаги воспроизведения
						</label>
						<textarea
							id='bh-steps'
							required
							minLength={8}
							rows={5}
							className='w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none ring-slate-900/10 focus:ring-2'
							value={steps}
							onChange={(e) => setSteps(e.target.value)}
							placeholder={'1. …\n2. …\n3. …'}
						/>
					</div>
					<div className='space-y-2'>
						<label className='text-sm font-bold text-slate-800' htmlFor='bh-path'>
							Маршрут по платформе
						</label>
						<textarea
							id='bh-path'
							required
							minLength={4}
							rows={3}
							className='w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm outline-none ring-slate-900/10 focus:ring-2'
							value={pathText}
							onChange={(e) => setPathText(e.target.value)}
							placeholder='Например: Главная → Уроки → Модуль X → задача …'
						/>
					</div>
					<div className='space-y-2'>
						<span className='text-sm font-bold text-slate-800'>Скриншот (PNG, JPG, WEBP до 5 МБ)</span>
						<input
							type='file'
							name='screenshot'
							accept='image/png,image/jpeg,image/webp'
							onChange={(e) => setFile(e.target.files?.[0] ?? null)}
							className='block w-full text-sm text-slate-600 file:mr-4 file:rounded-xl file:border-0 file:bg-slate-100 file:px-4 file:py-2 file:font-semibold file:text-slate-800 hover:file:bg-slate-200'
						/>
					</div>
					<button
						type='submit'
						disabled={busy}
						className='inline-flex items-center gap-2 rounded-2xl bg-slate-900 px-6 py-3 text-sm font-black uppercase tracking-wide text-white disabled:opacity-50'
					>
						{busy ? <Loader2 className='size-4 animate-spin' aria-hidden /> : null}
						Отправить репорт
					</button>
				</form>
			</section>

			<section className='space-y-3'>
				<h2 className='text-lg font-black text-slate-900'>Мои репорты</h2>
				{loadingHistory ? (
					<p className='flex items-center gap-2 text-sm text-slate-500'>
						<Loader2 className='size-4 animate-spin' aria-hidden /> Загрузка…
					</p>
				) : null}
				<ul className='space-y-3'>
					{(history?.reports ?? []).map((r) => (
						<li key={r.id} className='codequest-card rounded-2xl border border-slate-100 p-4'>
							<div className='flex flex-wrap items-start justify-between gap-2'>
								<span className='rounded-full bg-slate-100 px-3 py-1 text-xs font-black uppercase tracking-wide text-slate-700'>
									#{r.id}{' · '}
									{moderationLabel.get(r.moderation_status) ?? r.moderation_status}
								</span>
								<span className='text-xs text-slate-500'>
									{r.created_at
										? new Date(r.created_at).toLocaleString('ru-RU', {
												dateStyle: 'short',
												timeStyle: 'short',
											})
										: ''}
								</span>
							</div>
							{r.moderation_status === 'approved' && r.xp_awarded > 0 ? (
								<p className='mt-2 text-sm font-semibold text-emerald-700'>
									Начислено XP: +{r.xp_awarded}
								</p>
							) : null}
							<p className='mt-2 whitespace-pre-wrap text-sm text-slate-700'>{r.description}</p>
							{r.screenshot?.url ? (
								<div className='mt-3 overflow-hidden rounded-xl ring-1 ring-slate-200'>
									{/* Relative URL через тот же origin (Next `/api`). */}
									<img
										src={r.screenshot.url}
										alt='Снимок экрана к репорту'
										className='max-h-64 w-full object-contain bg-slate-50'
									/>
								</div>
							) : null}
						</li>
					))}
				</ul>
				{(history?.reports ?? []).length === 0 && !loadingHistory ? (
					<p className='text-sm text-slate-500'>Пока нет отправленных репортов.</p>
				) : null}
			</section>
		</div>
	)
}
