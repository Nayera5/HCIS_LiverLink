import { useEffect } from 'react'
import { subscribeToSlotAvailabilityChanges } from '../api/slotAvailability'
import { useApi } from './useApi'

export function useSlotAvailability(loader) {
  const result = useApi(loader)
  const { reload } = result

  useEffect(() => {
    return subscribeToSlotAvailabilityChanges(reload)
  }, [reload])

  return result
}
