'use client'

import { RolePill } from '@/components/role-pill'
import { api, getApiErrorMessage } from '@/lib/api'
import { showErrorToast, showSuccessToast } from '@/lib/toast'
import type { AdminManagerDirectoryResponse, AdminUserListItem } from '@/types'
import { useCallback, useEffect, useState } from 'react'

export function SuperadminManagersPanel({ initialData }: { initialData: AdminManagerDirectoryResponse | null }) {
  const [data, setData] = useState(initialData)
  const [loading, setLoading] = useState(!initialData)
  const [busy, setBusy] = useState<number | null>(null)
  const [form, setForm] = useState({ full_name: '', email: '', phone: '', password: '' })
  const [creating, setCreating] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    try { setData(await api<AdminManagerDirectoryResponse>('/admin/managers?page=1&page_size=50', undefined, 'required')) } catch (error) { showErrorToast(getApiErrorMessage(error, 'Не удалось загрузить менеджеров.')) } finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  async function create(event: React.FormEvent) {
    event.preventDefault(); setCreating(true)
    try { await api('/admin/managers', { method: 'POST', body: JSON.stringify(form) }, 'required'); showSuccessToast('Менеджер создан.'); setForm({ full_name: '', email: '', phone: '', password: '' }); await load() } catch (error) { showErrorToast(getApiErrorMessage(error, 'Не удалось создать менеджера.')) } finally { setCreating(false) }
  }
  async function change(user: AdminUserListItem, action: 'block' | 'unblock' | 'delete') {
    if (action === 'delete' && !window.confirm(`Удалить менеджера ${user.email}?`)) return
    setBusy(user.id)
    try { await api(`/admin/managers/${user.id}${action === 'delete' ? '' : `/${action}`}`, { method: action === 'delete' ? 'DELETE' : 'PATCH' }, 'required'); showSuccessToast(action === 'delete' ? 'Менеджер удалён.' : 'Статус менеджера обновлён.'); await load() } catch (error) { showErrorToast(getApiErrorMessage(error, 'Не удалось обновить менеджера.')) } finally { setBusy(null) }
  }

  return <div className='grid gap-6 xl:grid-cols-[22rem_minmax(0,1fr)]'>
    <form onSubmit={create} className='codequest-card h-fit p-5 sm:p-6' data-motion-reveal>
      <p className='brand-eyebrow'>Новая роль</p><h1 className='mt-2 text-2xl font-black text-slate-900'>Создать менеджера</h1><p className='mt-2 text-sm leading-6 text-slate-600'>Менеджер получает обычный кабинет, контакты и рассылки — без прав администратора.</p>
      <div className='mt-5 space-y-3'><input required className='w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm' placeholder='ФИО' value={form.full_name} onChange={event => setForm(value => ({ ...value, full_name: event.target.value }))} /><input required type='email' className='w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm' placeholder='Email' value={form.email} onChange={event => setForm(value => ({ ...value, email: event.target.value }))} /><input className='w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm' placeholder='Телефон (необязательно)' value={form.phone} onChange={event => setForm(value => ({ ...value, phone: event.target.value }))} /><input required minLength={12} type='password' className='w-full rounded-2xl border border-slate-200 px-4 py-3 text-sm' placeholder='Пароль (минимум 12 символов)' value={form.password} onChange={event => setForm(value => ({ ...value, password: event.target.value }))} /></div>
      <button disabled={creating} className='brand-button-primary mt-5 w-full disabled:opacity-50'>{creating ? 'Создаём…' : 'Создать менеджера'}</button>
    </form>
    <section className='space-y-4'><div className='codequest-card p-5 sm:p-6'><p className='brand-eyebrow'>Команда</p><div className='mt-2 flex flex-wrap items-center justify-between gap-3'><h2 className='text-2xl font-black text-slate-900'>Менеджеры</h2><span className='brand-chip brand-chip--soft'>{data?.pagination.total ?? 0} всего</span></div></div>
      {loading && !data ? <div className='codequest-card p-6 text-slate-500'>Загрузка…</div> : null}
      {data?.managers.map(user => <article key={user.id} className='codequest-card flex flex-col gap-4 p-5 transition-transform duration-200 hover:-translate-y-0.5 sm:flex-row sm:items-center sm:justify-between sm:p-6'><div className='min-w-0'><div className='flex flex-wrap items-center gap-2'><h3 className='font-black text-slate-900'>{user.full_name}</h3><RolePill role='manager' /></div><p className='mt-1 break-all text-sm text-slate-500'>{user.email}{user.phone ? ` · ${user.phone}` : ''}</p></div><div className='flex flex-wrap gap-2'><button type='button' disabled={busy === user.id} onClick={() => void change(user, user.is_active ? 'block' : 'unblock')} className='rounded-full bg-amber-100 px-4 py-2 text-sm font-semibold text-amber-800 disabled:opacity-50'>{user.is_active ? 'Блокировать' : 'Разблокировать'}</button><button type='button' disabled={busy === user.id} onClick={() => void change(user, 'delete')} className='rounded-full bg-rose-100 px-4 py-2 text-sm font-semibold text-rose-800 disabled:opacity-50'>Удалить</button></div></article>)}
      {!loading && data?.managers.length === 0 ? <div className='codequest-card p-8 text-center text-slate-500'>Менеджеры пока не созданы.</div> : null}
    </section>
  </div>
}
