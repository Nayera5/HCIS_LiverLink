const listeners = new Set()

export function announceSlotAvailabilityChanged() {
  listeners.forEach((listener) => listener())
}

export function subscribeToSlotAvailabilityChanges(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}
