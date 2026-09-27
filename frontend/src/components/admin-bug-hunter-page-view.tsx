'use client'

import { AdminAreaShell } from '@/components/admin-area-shell'
import { FiveItemPager, SERVER_PAGE_SIZE, useFiveItemWindow } from '@/components/five-item-navigator'
import { api, getApiErrorMessage } from '@/lib/api'
import { showErrorToast, showSuccessToast } from '@/lib/toast'
import type { BugHunterStaffListResponse, BugHunterStaffSettingsResponse } from '@/types'
import { Inbox, Loader2, Settings2 } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

type AdminArea = 'admin' | 'superadmin'

const FILTERS: Array<{ value: string; label: string }> = [
	{ value: '', label: 'Все' },
	{ value: 'pending', label: 'На модерации' },
	{ value: 'approved', label: 'Принято' },
	{ value: 'rejected', label: 'Отклонено' },
]

export function AdminBugHunterPageView({ area }: { area: AdminArea }) {
	const [filter, setFilter] = useState('')
	const [payload, setPayload] = useState<BugHunterStaffListResponse | null>(null)
	const [loading, setLoading] = useState(true)
	const [listError, setListError] = useState('')
	const [busyId, setBusyId] = useState<number | null>(null)
	const [xpDraft, setXpDraft] = useState('')
	const [xpMax, setXpMax] = useState(10_000)
	const [xpSaving, setXpSaving] = useState(false)
	const [xpLoading, setXpLoading] = useState(true)
	const [page, setPage] = useState(1)

	const loadSettings = useCallback(async () => {
		setXpLoading(true)
		try {
			const s = await api<BugHunterStaffSettingsResponse>(
				'/support/staff/bug-hunter/settings',
				undefined,
				'required',
			)
			setXpDraft(String(s.approved_xp ?? 0))
			setXpMax(s.max_xp ?? 10_000)
		} catch (e) {
			showErrorToast(getApiErrorMessage(e, 'Не удалось загрузить настройки XP.'))
		} finally {
			setXpLoading(false)
		}
	}, [])

	const load = useCallback(async () => {
		setLoading(true)
		setListError('')
		try {
			const qs = new URLSearchParams({ page: String(page), page_size: String(SERVER_PAGE_SIZE) })
			if (filter) qs.set('status', filter)
			const res = await api<BugHunterStaffListResponse>(
				`/support/staff/bug-reports?${qs.toString()}`,
				undefined,
				'required',
			)
			setPayload(res)
		} catch (e) {
			const msg = getApiErrorMessage(e, 'Не удалось загрузить заявки.')
			setListError(msg)
			setPayload(null)
			showErrorToast(msg)
		} finally {
			setLoading(false)
		}
	}, [filter, page])

	useEffect(() => {
		void loadSettings()
	}, [loadSettings])

	async function saveXpReward() {
		const n = Number.parseInt(String(xpDraft).trim(), 10)
		if (Number.isNaN(n)) {
			showErrorToast('Введите целое число XP.')
			return
		}
		setXpSaving(true)
		try {
			await api<{ approved_xp: number; max_xp: number }>(
				'/support/staff/bug-hunter/settings',
				{ method: 'PATCH', body: JSON.stringify({ approved_xp: n }) },
				'required',
			)
			showSuccessToast('Размер вознаграждения сохранён.')
			void loadSettings()
			void load()
		} catch (e) {
			showErrorToast(getApiErrorMessage(e, 'Не удалось сохранить XP.'))
		} finally {
			setXpSaving(false)
		}
	}

	useEffect(() => {
		void load()
	}, [load])

	async function moderate(id: number, status: 'approved' | 'rejected') {
		setBusyId(id)
		try {
			await api(
				`/support/staff/bug-reports/${id}`,
				{
					method: 'PATCH',
					body: JSON.stringify({ moderation_status: status }),
				},
				'required',
			)
			showSuccessToast(status === 'approved' ? 'Заявка принята, XP начислены автору.' : 'Заявка отклонена.')
			void load()
		} catch (e) {
			showErrorToast(getApiErrorMessage(e, 'Не удалось сохранить решение.'))
		} finally {
			setBusyId(null)
		}
	}

	const reports = payload?.reports ?? []
	const reportsWindow = useFiveItemWindow({ items: reports, pagination: payload?.pagination, loading, onPageChange: setPage, resetKey: filter })
	const count = payload?.pagination.total ?? reports.length

	return (
		<AdminAreaShell area={area} section='bug-hunter'>
			<div className='codequest-card p-5 sm:p-6'>
				<p className='brand-eyebrow'>Качество платформы</p>
				<h1 className='mt-2 text-2xl font-black text-slate-900 sm:text-3xl'>Баг-хантер</h1>
				<p className='mt-1 max-w-prose text-sm leading-7 text-slate-600'>
					Раздел для заявок пользователей об ошибках. Ниже — список заявок; XP начисляется только после вашего одобрения.
				</p>
			</div>

			{/* Основной блок — заявки */}
			<div className='codequest-card overflow-hidden'>
				<div className='border-b border-slate-100 bg-slate-50 px-5 py-4 sm:flex sm:flex-wrap sm:items-center sm:justify-between sm:gap-3'>
					<div className='flex items-start gap-3'>
						<span className='mt-0.5 inline-flex size-10 shrink-0 items-center justify-center rounded-2xl bg-white text-slate-800 ring-1 ring-slate-200'>
							<Inbox className='size-5' aria-hidden />
						</span>
						<div>
							<h2 className='text-lg font-black text-slate-900'>Заявки пользователей</h2>
							<p className='mt-1 text-xs text-slate-600'>
								Описание, шаги воспроизведения и маршрут по платформе. Скриншот — при наличии.
								<span className='font-semibold text-slate-800'>
									{' '}
									{loading ? '' : `${count} шт.${payload ? ` · награда за принятую заявку: ${payload.xp_reward_on_approval} XP` : ''}`}
								</span>
							</p>
						</div>
					</div>
				</div>

				<div className='border-b border-slate-100 px-5 py-3'>
					<p className='mb-2 text-[11px] font-black uppercase tracking-wide text-slate-500'>
						Фильтр по статусу
					</p>
					<div className='flex flex-wrap gap-2'>
						{FILTERS.map((f) => (
							<button
								key={f.value || 'all'}
								type='button'
								onClick={() => { setFilter(f.value); setPage(1) }}
								className={`rounded-full px-3 py-1.5 text-xs font-black uppercase tracking-wide ring-1 ring-inset transition ${
									filter === f.value
										? 'bg-slate-900 text-white ring-slate-900'
										: 'bg-white text-slate-600 ring-slate-200 hover:bg-slate-50'
								}`}
							>
								{f.label}
							</button>
						))}
					</div>
				</div>

				<div className='space-y-4 px-5 py-5'>
					{loading ? (
						<p className='flex items-center gap-2 text-sm font-medium text-slate-600'>
							<Loader2 className='size-4 animate-spin' aria-hidden />
							Загрузка заявок…
						</p>
					) : null}

					{listError ? (
						<div className='rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm font-semibold text-rose-800'>
							{listError}
						</div>
					) : null}

					{!loading && !listError && reports.length === 0 ? (
						<p className='rounded-2xl border border-dashed border-slate-200 bg-white px-4 py-8 text-center text-sm text-slate-600'>
							Заявок пока нет. Когда пользователи отправят репорт с страницы «Баг-хантер», они появятся здесь.
						</p>
					) : null}

					{reportsWindow.visibleItems.map((r) => (
						<div
							key={r.id}
							className='overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm'
						>
							<div className='flex flex-wrap items-start justify-between gap-3 border-b border-slate-100 bg-slate-50/90 px-4 py-3 sm:px-5'>
								<div>
									<p className='text-xs font-black uppercase tracking-wide text-slate-500'>
										Заявка №{r.id}
									</p>
									<p className='text-sm font-semibold text-slate-800'>
										{r.reporter_email ?? '—'}{' '}
										{r.reporter_role ? (
											<span className='font-normal text-slate-500'>({r.reporter_role})</span>
										) : null}
									</p>
									{r.created_at ? (
										<p className='mt-1 text-xs text-slate-500'>
											{new Date(r.created_at).toLocaleString('ru-RU')}
										</p>
									) : null}
								</div>
								<span className='rounded-full bg-white px-3 py-1 text-xs font-black uppercase tracking-wide ring-1 ring-slate-200'>
									{r.moderation_status}
									{r.moderation_status === 'approved' && r.xp_awarded ? ` · +${r.xp_awarded} XP` : ''}
								</span>
							</div>

							<div className='space-y-4 px-4 py-4 sm:px-5 sm:py-5'>
								{r.screenshot?.url ? (
									<div>
										<p className='mb-2 text-[11px] font-black uppercase tracking-wide text-slate-500'>
											Скриншот
										</p>
										<img
											src={r.screenshot.url}
											alt='Скриншот из заявки'
											className='max-h-80 w-full rounded-xl object-contain ring-1 ring-slate-200'
										/>
									</div>
								) : null}
								<div>
									<p className='mb-1.5 text-[11px] font-black uppercase tracking-wide text-slate-500'>
										Что пошло не так
									</p>
									<p className='whitespace-pre-wrap text-sm text-slate-800'>{r.description}</p>
								</div>
								<div>
									<p className='mb-1.5 text-[11px] font-black uppercase tracking-wide text-slate-500'>
										Шаги воспроизведения
									</p>
									<p className='whitespace-pre-wrap text-sm text-slate-700'>{r.reproduction_steps}</p>
								</div>
								<div>
									<p className='mb-1.5 text-[11px] font-black uppercase tracking-wide text-slate-500'>
										Маршрут пользователя по платформе
									</p>
									<p className='whitespace-pre-wrap text-sm text-slate-700'>{r.user_journey_path}</p>
								</div>
								{r.moderator_note ? (
									<p className='rounded-xl bg-slate-50 px-3 py-2 text-xs text-slate-700'>
										<span className='font-bold text-slate-800'>Комментарий модератора:</span>{' '}
										{r.moderator_note}
									</p>
								) : null}

								{r.moderation_status === 'pending' ? (
									<div className='flex flex-wrap gap-2 border-t border-slate-100 pt-4'>
										<button
											type='button'
											disabled={busyId === r.id}
											onClick={() => void moderate(r.id, 'approved')}
											className='rounded-xl bg-emerald-600 px-4 py-2 text-sm font-bold text-white shadow-sm disabled:opacity-50'
										>
											Принять и начислить XP
										</button>
										<button
											type='button'
											disabled={busyId === r.id}
											onClick={() => void moderate(r.id, 'rejected')}
											className='rounded-xl bg-slate-200 px-4 py-2 text-sm font-bold text-slate-800 disabled:opacity-50'
										>
											Отклонить
										</button>
									</div>
								) : null}
							</div>
						</div>
					))}
					<FiveItemPager window={reportsWindow} loading={loading} itemLabel='заявок' />
				</div>
			</div>

			{/* Настройки XP — вторичный блок */}
			<div className='codequest-card p-5 sm:p-6'>
				<div className='flex items-start gap-3'>
					<span className='inline-flex size-10 shrink-0 items-center justify-center rounded-2xl bg-slate-100 text-slate-800'>
						<Settings2 className='size-5' aria-hidden />
					</span>
					<div className='min-w-0 flex-1'>
						<h2 className='text-lg font-black text-slate-900'>Награда XP</h2>
						<p className='mt-1 text-sm text-slate-600'>
							Размер начисления за одобренную заявку. Допустимо от 0 до {xpLoading ? '…' : xpMax} XP.
						</p>
						<div className='mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-end'>
							<label className='flex min-w-[10rem] max-w-xs flex-1 flex-col gap-1.5'>
								<span className='text-xs font-black uppercase tracking-wide text-slate-600'>
									XP за принятую заявку
								</span>
								<input
									type='number'
									min={0}
									max={xpMax}
									step={1}
									disabled={xpLoading || xpSaving}
									className='rounded-xl border border-slate-200 px-3 py-2 text-sm font-semibold disabled:opacity-50'
									value={xpDraft}
									onChange={(e) => setXpDraft(e.target.value)}
									aria-label='XP за принятую заявку'
								/>
							</label>
							<button
								type='button'
								disabled={xpLoading || xpSaving}
								onClick={() => void saveXpReward()}
								className='rounded-xl bg-slate-900 px-4 py-2 text-sm font-bold text-white disabled:opacity-50'
							>
								{xpSaving ? 'Сохранение…' : 'Сохранить'}
							</button>
						</div>
					</div>
				</div>
			</div>
		</AdminAreaShell>
	)
}
