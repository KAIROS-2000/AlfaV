'use client'

import { AdminAreaShell } from '@/components/admin-area-shell'
import { RolePill } from '@/components/role-pill'
import { api, getApiErrorMessage } from '@/lib/api'
import { showErrorToast, showSuccessToast } from '@/lib/toast'
import type {
  BroadcastFilters,
  BroadcastPreviewResponse,
  ContactListItem,
  ContactsDirectoryResponse,
} from '@/types'
import { Loader2, Mail, Phone, Send, Users } from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'

type StaffArea = 'manager' | 'superadmin'

const roleLabels = {
  student: 'Ученики',
  teacher: 'Учителя',
  parent: 'Родители',
} as const

const defaultBroadcastFilters: BroadcastFilters = {
  roles: ['student', 'teacher', 'parent'],
  age_group: 'all',
  verified: null,
  parent_link: 'all',
}

export function ContactsPanel({ area, initial }: { area: StaffArea; initial: ContactsDirectoryResponse | null }) {
  const [data, setData] = useState(initial)
  const [loading, setLoading] = useState(!initial)
  const [q, setQ] = useState(initial?.filters.q ?? '')
  const [status, setStatus] = useState(initial?.filters.status ?? 'all')
  const [role, setRole] = useState('all')
  const [verified, setVerified] = useState('all')
  const [parentLink, setParentLink] = useState(initial?.filters.parent_link ?? 'all')
  const [page, setPage] = useState(1)

  const load = useCallback(async () => {
    setLoading(true)
    const params = new URLSearchParams({ page: String(page), page_size: '20', status, q })
    if (role !== 'all') params.set('roles', role)
    if (verified !== 'all') params.set('verified', verified)
    if (parentLink !== 'all') params.set('parent_link', parentLink)
    try {
      setData(await api<ContactsDirectoryResponse>(`/admin/contacts?${params.toString()}`, undefined, 'required'))
    } catch (error) {
      showErrorToast(getApiErrorMessage(error, 'Не удалось загрузить контакты.'))
    } finally {
      setLoading(false)
    }
  }, [page, parentLink, q, role, status, verified])

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 250)
    return () => window.clearTimeout(timer)
  }, [load])

  return (
    <AdminAreaShell area={area} section='contacts'>
      <section className='codequest-card p-5 sm:p-7' data-motion-reveal>
        <p className='brand-eyebrow'>Контактный центр</p>
        <div className='mt-2 flex flex-wrap items-end justify-between gap-3'>
          <div>
            <h1 className='text-2xl font-black text-slate-900 sm:text-3xl'>Все пользователи и родители</h1>
            <p className='mt-2 max-w-3xl text-sm leading-6 text-slate-600'>
              Контактные данные доступны только рабочим ролям. Поиск и фильтры работают на сервере.
            </p>
          </div>
          <span className='brand-chip brand-chip--soft'>{data?.pagination.total ?? 0} контактов</span>
        </div>
        <div className='mt-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5'>
          <input className='rounded-2xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm xl:col-span-2' value={q} onChange={event => { setQ(event.target.value); setPage(1) }} placeholder='Имя, email или телефон' />
          <select className='rounded-2xl border border-slate-200 bg-white px-3 py-3 text-sm' value={role} onChange={event => { setRole(event.target.value); setPage(1) }}>
            <option value='all'>Все роли</option><option value='student'>Ученики</option><option value='teacher'>Учителя</option><option value='parent'>Родители</option>
          </select>
          <select className='rounded-2xl border border-slate-200 bg-white px-3 py-3 text-sm' value={status} onChange={event => { setStatus(event.target.value as 'all' | 'active' | 'blocked'); setPage(1) }}><option value='all'>Любой статус</option><option value='active'>Активные</option><option value='blocked'>Заблокированные</option></select>
          <select className='rounded-2xl border border-slate-200 bg-white px-3 py-3 text-sm' value={verified} onChange={event => { setVerified(event.target.value); setPage(1) }}><option value='all'>Email: любой</option><option value='true'>Email подтверждён</option><option value='false'>Email не подтверждён</option></select>
          <select className='rounded-2xl border border-slate-200 bg-white px-3 py-3 text-sm' value={parentLink} onChange={event => { setParentLink(event.target.value as 'all' | 'linked' | 'unlinked'); setPage(1) }}><option value='all'>Связь родителя: любая</option><option value='linked'>Родители с детьми</option><option value='unlinked'>Родители без связи</option></select>
        </div>
      </section>

      <section className='space-y-3'>
        {loading && !data ? <div className='codequest-card flex items-center gap-2 p-6 text-slate-600'><Loader2 className='animate-spin' size={18} />Загрузка контактов…</div> : null}
        {data?.contacts.map(contact => <ContactCard key={contact.id} contact={contact} />)}
        {!loading && data?.contacts.length === 0 ? <div className='codequest-card p-8 text-center text-slate-500'>По выбранным фильтрам контактов нет.</div> : null}
        {data?.pagination.total_pages && data.pagination.total_pages > 1 ? <div className='flex items-center justify-between gap-3 py-2 text-sm'><button className='rounded-full border border-slate-200 px-4 py-2 disabled:opacity-50' disabled={loading || page <= 1} onClick={() => setPage(value => value - 1)}>Назад</button><span>Страница {data.pagination.page} из {data.pagination.total_pages}</span><button className='rounded-full border border-slate-200 px-4 py-2 disabled:opacity-50' disabled={loading || page >= data.pagination.total_pages} onClick={() => setPage(value => value + 1)}>Вперёд</button></div> : null}
      </section>
    </AdminAreaShell>
  )
}

function ContactCard({ contact }: { contact: ContactListItem }) {
  return <article className='codequest-card p-5 transition-transform duration-200 hover:-translate-y-0.5 sm:p-6'>
    <div className='flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between'>
      <div className='min-w-0'><div className='flex flex-wrap items-center gap-2'><h2 className='text-lg font-black text-slate-900'>{contact.full_name || 'Без имени'}</h2><RolePill role={contact.role} /></div><p className='mt-1 text-sm text-slate-500'>ID #{contact.id} · {contact.is_active ? 'активен' : 'заблокирован'} · email {contact.email_verified ? 'подтверждён' : 'не подтверждён'}</p></div>
      {contact.role === 'parent' ? <span className='brand-chip brand-chip--soft'>{contact.linked_children.length ? `Дети: ${contact.linked_children.join(', ')}` : 'Нет связи с ребёнком'}</span> : null}
    </div>
    <div className='mt-4 grid gap-3 text-sm sm:grid-cols-2'>
      <a className='flex items-center gap-2 break-all text-slate-700 hover:text-slate-950' href={`mailto:${contact.email}`}><Mail size={16} className='shrink-0 text-slate-400' />{contact.email}</a>
      <a className='flex items-center gap-2 text-slate-700 hover:text-slate-950' href={contact.phone ? `tel:${contact.phone}` : undefined}><Phone size={16} className='shrink-0 text-slate-400' />{contact.phone || 'Телефон не указан'}</a>
    </div>
  </article>
}

export function BroadcastPanel({ area }: { area: StaffArea }) {
  const [filters, setFilters] = useState<BroadcastFilters>(defaultBroadcastFilters)
  const [title, setTitle] = useState('')
  const [body, setBody] = useState('')
  const [preview, setPreview] = useState<BroadcastPreviewResponse | null>(null)
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [sending, setSending] = useState(false)

  const previewAudience = useCallback(async () => {
    setLoadingPreview(true)
    try { setPreview(await api<BroadcastPreviewResponse>('/admin/broadcasts/preview', { method: 'POST', body: JSON.stringify({ filters }) }, 'required')) } catch (error) { showErrorToast(getApiErrorMessage(error, 'Не удалось рассчитать аудиторию.')) } finally { setLoadingPreview(false) }
  }, [filters])

  useEffect(() => { const timer = window.setTimeout(() => void previewAudience(), 200); return () => window.clearTimeout(timer) }, [previewAudience])

  function toggleRole(role: BroadcastFilters['roles'][number]) { setFilters(value => ({ ...value, roles: value.roles.includes(role) ? value.roles.filter(item => item !== role) : [...value.roles, role] })) }

  async function send() {
    if (!title.trim() || !body.trim() || !preview?.recipient_count) return
    if (!window.confirm(`Отправить рассылку ${preview.recipient_count} получателям?`)) return
    setSending(true)
    try {
      const result = await api<{ recipient_count: number }>('/admin/broadcasts', { method: 'POST', body: JSON.stringify({ title, body, filters }) }, 'required')
      showSuccessToast(`Рассылка отправлена: ${result.recipient_count} получателей.`)
      setTitle(''); setBody(''); await previewAudience()
    } catch (error) { showErrorToast(getApiErrorMessage(error, 'Не удалось отправить рассылку.')) } finally { setSending(false) }
  }

  return <AdminAreaShell area={area} section='broadcasts'>
    <div className='grid gap-6 xl:grid-cols-[minmax(0,1fr)_20rem]'>
      <section className='codequest-card p-5 sm:p-7' data-motion-reveal>
        <p className='brand-eyebrow'>Рассылка</p><h1 className='mt-2 text-2xl font-black text-slate-900 sm:text-3xl'>Сообщение пользователям и родителям</h1><p className='mt-2 text-sm leading-6 text-slate-600'>Получатели пересчитываются на сервере непосредственно перед отправкой. Email учитывает персональные настройки уведомлений.</p>
        <div className='mt-6 grid gap-4'><label className='space-y-2'><span className='text-sm font-semibold text-slate-700'>Заголовок</span><input maxLength={200} className='w-full rounded-2xl border border-slate-200 px-4 py-3' value={title} onChange={event => setTitle(event.target.value)} placeholder='Например, важное обновление платформы' /></label><label className='space-y-2'><span className='text-sm font-semibold text-slate-700'>Текст сообщения</span><textarea maxLength={4000} rows={7} className='w-full rounded-2xl border border-slate-200 px-4 py-3' value={body} onChange={event => setBody(event.target.value)} placeholder='Напишите понятный текст для аудитории…' /></label></div>
      </section>
      <aside className='codequest-card h-fit p-5 sm:p-6' data-motion-reveal>
        <div className='flex items-center gap-2'><Users size={19} className='text-slate-500' /><h2 className='font-black text-slate-900'>Аудитория</h2></div>
        <div className='mt-4 space-y-4'>
          <div><p className='mb-2 text-xs font-black uppercase tracking-[0.12em] text-slate-500'>Кому</p><div className='flex flex-wrap gap-2'>{Object.entries(roleLabels).map(([role, label]) => <button type='button' key={role} onClick={() => toggleRole(role as BroadcastFilters['roles'][number])} className={`rounded-full border px-3 py-2 text-sm font-semibold transition ${filters.roles.includes(role as BroadcastFilters['roles'][number]) ? 'border-slate-900 bg-slate-900 text-white' : 'border-slate-200 bg-white text-slate-600'}`}>{label}</button>)}</div></div>
          <label className='block space-y-1 text-sm font-semibold text-slate-700'>Возраст<select className='mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal' value={filters.age_group} onChange={event => setFilters(value => ({ ...value, age_group: event.target.value as BroadcastFilters['age_group'] }))}><option value='all'>Все</option><option value='junior'>Младшая</option><option value='middle'>Средняя</option><option value='senior'>Старшая</option></select></label>
          <label className='block space-y-1 text-sm font-semibold text-slate-700'>Email<select className='mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal' value={filters.verified === null ? 'all' : String(filters.verified)} onChange={event => setFilters(value => ({ ...value, verified: event.target.value === 'all' ? null : event.target.value === 'true' }))}><option value='all'>Любой статус</option><option value='true'>Подтверждён</option><option value='false'>Не подтверждён</option></select></label>
          <label className='block space-y-1 text-sm font-semibold text-slate-700'>Родители<select className='mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 font-normal' value={filters.parent_link} onChange={event => setFilters(value => ({ ...value, parent_link: event.target.value as BroadcastFilters['parent_link'] }))}><option value='all'>Не учитывать связь</option><option value='linked'>Только с ребёнком</option><option value='unlinked'>Без связи с ребёнком</option></select></label>
        </div>
        <div className='mt-6 rounded-2xl bg-slate-50 p-4'><p className='text-xs font-black uppercase tracking-[0.12em] text-slate-500'>Получатели</p><p className='mt-1 text-3xl font-black text-slate-900'>{loadingPreview ? '…' : preview?.recipient_count ?? 0}</p><p className='mt-2 text-xs text-slate-500'>Ученики: {preview?.by_role.student ?? 0} · Учителя: {preview?.by_role.teacher ?? 0} · Родители: {preview?.by_role.parent ?? 0}</p></div>
        <button type='button' disabled={sending || !title.trim() || !body.trim() || !preview?.recipient_count} onClick={() => void send()} className='brand-button-primary mt-4 inline-flex w-full items-center justify-center gap-2 disabled:opacity-50'><Send size={16} />{sending ? 'Отправляем…' : 'Отправить рассылку'}</button>
      </aside>
    </div>
  </AdminAreaShell>
}
