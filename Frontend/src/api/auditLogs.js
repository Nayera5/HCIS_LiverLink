// Audit log viewer (backend: GET /api/audit-logs/, audit.view = Super Admin only). Read-only.
import { authRequest, toQuery } from './http'

/** params: { action, kind, user, actor, patient, patient_mrn, entity_type, entity_id, date_from, date_to, page, page_size } */
export function listAuditLogs(params = {}) {
  return authRequest(`/audit-logs/${toQuery(params)}`)
}
