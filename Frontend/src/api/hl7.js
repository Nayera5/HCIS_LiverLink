// HL7 Message Monitor API (backend: apps/hl7, hl7.monitor = Super Admin only).
import { authRequest, toQuery } from './http'

/** params: { direction, status, type, search, page, page_size } */
export function listHl7Messages(params = {}) {
  return authRequest(`/hl7/messages/${toQuery(params)}`)
}

/** One message with its raw text and ACK. */
export function getHl7Message(id) {
  return authRequest(`/hl7/messages/${id}/`)
}

/** Try again to send a failed outbound message. */
export function resendHl7Message(id) {
  return authRequest(`/hl7/messages/${id}/resend/`, { method: 'POST' })
}
