'use client'

import { useEffect, useState } from 'react'
import { AuthForm } from '@/components/auth-form'
import { api, getApiErrorMessage } from '@/lib/api'
import type { RegistrationLegalConfig } from '@/lib/site-config'
import { showErrorToast } from '@/lib/toast'
import type { AuthOptions } from '@/types'

const DEFAULT_REGISTER_OPTIONS: AuthOptions = {
	roles: ['student', 'teacher', 'parent'],
	age_groups: ['junior', 'middle', 'senior'],
}

export function RegisterPageClient({ legalConfig }: { legalConfig: RegistrationLegalConfig }) {
  const [options, setOptions] = useState<AuthOptions | undefined>()

  useEffect(() => {
    api<AuthOptions>('/auth/options')
      .then(setOptions)
      .catch((error) => {
        setOptions(DEFAULT_REGISTER_OPTIONS)
        showErrorToast(
          getApiErrorMessage(
            error,
            'Не удалось загрузить настройки регистрации. Используются значения по умолчанию.',
          ),
        )
      })
  }, [])

  return <AuthForm mode="register" options={options} legalConfig={legalConfig} />
}
