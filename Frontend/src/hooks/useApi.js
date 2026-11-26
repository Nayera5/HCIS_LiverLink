import { useCallback, useEffect, useState } from 'react'

/**
 * Runs `loader()` (a memoised function returning a promise) and tracks its result.
 * When `loader` changes (e.g. new filters) the data reloads; `loading` is derived, so the
 * previous data stays visible while the next request runs.
 *
 * @returns {{ data, error, loading, reload, setData }}
 */
export function useApi(loader) {
  const [version, setVersion] = useState(0)
  const [state, setState] = useState({
    data: null, dataSource: null, error: null, source: null, version: -1,
  })

  useEffect(() => {
    let active = true
    loader().then(
      (data) => active && setState({ data, dataSource: loader, error: null, source: loader, version }),
      (error) => active && setState((prev) => ({ ...prev, error, source: loader, version })),
    )
    return () => {
      active = false
    }
  }, [loader, version])

  const reload = useCallback(() => setVersion((v) => v + 1), [])
  const setData = useCallback((data) => setState((prev) => ({ ...prev, data })), [])
  const hasDataForLoader = state.dataSource === loader && state.data !== null

  const loading = state.source !== loader || state.version !== version
  return { data: state.data, error: loading ? null : state.error, loading, hasDataForLoader, reload, setData }
}
