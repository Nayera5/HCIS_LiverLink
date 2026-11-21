import { useCallback, useMemo, useState } from 'react'
import { getErrorMessage } from '../../api/auth'
import Alert from '../../components/ui/Alert'
import { EmptyState, LoadingBlock } from '../../components/ui/Feedback'
import { ClipboardIcon } from '../../components/ui/icons'
import SelectField from '../../components/ui/SelectField'
import { useApi } from '../../hooks/useApi'
import LabTrendChart from './LabTrendChart'

/**
 * Pick one test from `results` and chart its history.
 * `loadTrend(testCode)` is getPatientTrend (staff) or getMyTrend (patient portal).
 */
export default function ResultsTrendPanel({ results, loadTrend }) {
  const tests = useMemo(() => {
    const seen = new Map()
    results.forEach((r) => seen.has(r.test_code) || seen.set(r.test_code, r.test_name))
    return [...seen].map(([value, label]) => ({ value, label }))
  }, [results])

  const [chosen, setChosen] = useState('')
  const code = tests.some((t) => t.value === chosen) ? chosen : tests[0]?.value

  const loader = useCallback(() => (code ? loadTrend(code) : Promise.resolve(null)), [code, loadTrend])
  const { data, error, loading } = useApi(loader)

  if (!tests.length) {
    return (
      <EmptyState icon={ClipboardIcon} title="No results to chart yet">
        A chart appears once a test has at least one result.
      </EmptyState>
    )
  }

  return (
    <div className="form-stack">
      <SelectField label="Test" value={code} options={tests} onChange={(event) => setChosen(event.target.value)} />
      {error && <Alert variant="error">{getErrorMessage(error, 'Could not load the trend.')}</Alert>}
      {loading && !data ? (
        <LoadingBlock label="Loading trend" />
      ) : data ? (
        <div className={loading ? 'lab-refetch' : ''}>
          <LabTrendChart points={data.points} testName={data.test.name} unit={data.test.unit}
            normalMin={data.test.normal_min} normalMax={data.test.normal_max} />
        </div>
      ) : null}
    </div>
  )
}
