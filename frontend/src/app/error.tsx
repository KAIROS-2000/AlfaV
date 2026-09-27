'use client'

import Link from 'next/link'
import { useEffect } from 'react'

export default function RouteError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  useEffect(() => {
    console.error('route_render_failed', error)
  }, [error])

  return (
    <main className="brand-page-shell py-10 sm:py-16">
      <section role="alert" className="codequest-card mx-auto max-w-xl p-6 sm:p-8">
        <p className="brand-eyebrow">Временная ошибка</p>
        <h1 className="mt-3 text-2xl font-black text-slate-900 sm:text-3xl">
          Не удалось загрузить страницу
        </h1>
        <p className="mt-3 text-sm leading-7 text-slate-600">
          Сервер не ответил или временно недоступен. Повторите запрос; если ошибка сохраняется, вернитесь позже.
        </p>
        <div className="mt-6 flex flex-wrap gap-3">
          <button type="button" className="brand-button-primary" onClick={reset}>
            Повторить
          </button>
          <Link href="/" className="brand-button-secondary">
            На главную
          </Link>
        </div>
      </section>
    </main>
  )
}
