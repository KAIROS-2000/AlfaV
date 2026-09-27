export type RegistrationFlowResponse = {
  user?: { role?: string } | null
  requires_password_setup?: boolean
  requires_login_after_password_setup?: boolean
}

/** Production parent signup stays anonymous until the emailed setup link is completed. */
export function awaitsParentPasswordSetup(response: RegistrationFlowResponse) {
  return response.user?.role === 'parent' && response.requires_password_setup === true
}
