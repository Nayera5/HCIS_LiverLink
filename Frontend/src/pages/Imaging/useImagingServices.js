import { useCallback } from 'react'
import { listAllServices } from '../../api/billing'
import { useApi } from '../../hooks/useApi'

/** Imaging services of the Billing catalog. `params`: a constant from imagingRules (keep it stable). */
export function useImagingServices(params) {
  const loader = useCallback(() => listAllServices(params), [params])
  const { data, error, loading, reload } = useApi(loader)
  return { services: data || [], error, loading, reload }
}
