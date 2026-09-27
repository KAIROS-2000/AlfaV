import { getLegalDocument } from '@/lib/server-site-config'
import type { LegalDocumentKind } from '@/lib/site-config'

export function LegalDocumentPage({ kind }: { kind: LegalDocumentKind }) {
  const document = getLegalDocument(kind)
  const paragraphs = document.content?.split(/\n\s*\n/).filter(Boolean) || []

  return (
    <main className="brand-page-shell py-10 sm:py-16">
      <article className="codequest-card mx-auto max-w-4xl p-6 sm:p-10">
        <p className="brand-eyebrow">Правовая информация</p>
        <h1 className="mt-3 text-3xl font-black text-slate-900 sm:text-5xl">
          {document.title}
        </h1>
        <dl className="mt-5 flex flex-wrap gap-x-8 gap-y-2 text-sm text-slate-600">
          <div>
            <dt className="inline font-semibold">Версия: </dt>
            <dd className="inline">{document.legalDocumentVersion}</dd>
          </div>
          {document.legalEffectiveDate ? (
            <div>
              <dt className="inline font-semibold">Действует с: </dt>
              <dd className="inline">{document.legalEffectiveDate}</dd>
            </div>
          ) : null}
        </dl>

        {paragraphs.length ? (
          <div className="mt-8 space-y-5 whitespace-pre-line text-base leading-8 text-slate-700">
            {paragraphs.map((paragraph, index) => (
              <p key={index}>{paragraph}</p>
            ))}
          </div>
        ) : (
          <div role="status" className="mt-8 rounded-2xl border border-amber-200 bg-amber-50 p-5 text-amber-950">
            Утверждённый текст документа не настроен для этой среды.
          </div>
        )}
      </article>
    </main>
  )
}
