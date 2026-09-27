export function rejectedResults(
  results: readonly PromiseSettledResult<unknown>[],
): PromiseRejectedResult[] {
  return results.filter(
    (result): result is PromiseRejectedResult => result.status === 'rejected',
  )
}
