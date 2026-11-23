// Reporting & Analytics API (backend: apps/reporting). Permissions are enforced server-side.
import { authRequest, downloadFile, toQuery } from './http'

// Report key (as returned by the backend) -> URL segment.
const REPORT_PATHS = {
  patients: 'patients',
  financial: 'financial',
  system_usage: 'system-usage',
  transplant: 'transplant',
}

/** params: { date_from, date_to } (YYYY-MM-DD, optional). */
export function getReport(key, params = {}) {
  return authRequest(`/reports/${REPORT_PATHS[key]}/${toQuery(params)}`)
}

/** format: 'csv' | 'pdf'. The download is recorded in the audit log by the backend. */
export function exportReport(key, format, params = {}) {
  return downloadFile(`/reports/${REPORT_PATHS[key]}/${toQuery({ ...params, export: format })}`,
    `liverlink-${REPORT_PATHS[key]}.${format}`)
}
