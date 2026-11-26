import assert from 'node:assert/strict'
import { test } from 'node:test'
import { announceSlotAvailabilityChanged, subscribeToSlotAvailabilityChanges } from './slotAvailability.js'

test('slot availability subscribers refresh on changes and can unsubscribe', () => {
  let refreshes = 0
  const unsubscribe = subscribeToSlotAvailabilityChanges(() => { refreshes += 1 })

  announceSlotAvailabilityChanged()
  assert.equal(refreshes, 1)

  unsubscribe()
  announceSlotAvailabilityChanged()
  assert.equal(refreshes, 1)
})
