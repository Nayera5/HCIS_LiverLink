import assert from 'node:assert/strict'
import { describe, test } from 'node:test'
import { loadAllPages } from './pagination.js'

describe('paginated API loading', () => {
  test('loads and combines every page using consistent filters', async () => {
    const calls = []
    const pages = [
      { next: '/api/services/?page=2', results: [{ id: 1 }, { id: 2 }] },
      { next: null, results: [{ id: 3 }] },
    ]
    const results = await loadAllPages(async (params) => {
      calls.push(params)
      return pages[params.page - 1]
    }, { category: 'imaging', active_only: 'true' })

    assert.deepEqual(results, [{ id: 1 }, { id: 2 }, { id: 3 }])
    assert.deepEqual(calls, [
      { category: 'imaging', active_only: 'true', page: 1, page_size: 100 },
      { category: 'imaging', active_only: 'true', page: 2, page_size: 100 },
    ])
  })
})
