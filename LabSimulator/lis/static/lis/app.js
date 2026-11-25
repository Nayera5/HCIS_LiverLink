/* External Laboratory Simulator: the single page. Plain JavaScript, no build step. */
'use strict'

const REFRESH_MS = 4000
const FLAGS = { N: 'N (normal)', L: 'L (low)', H: 'H (high)', LL: 'LL (critical low)', HH: 'HH (critical high)' }
const STEPS = ['received', 'processing', 'completed']
const STATUS_TONES = { received: 'blue', processing: 'amber', completed: 'green', cancelled: '' }

let orders = []
let selected = null // the open order, with its tests
let openMessageId = null
let busy = false
let readNumber = 0 // answers of older reads of an order are ignored

// ------------------------------------------------------------------ helpers

const $ = (id) => document.getElementById(id)
const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1)
const formatTime = (value) => (value ? new Date(value).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' }) : '—')
const formatBirthDate = (text) => (/^\d{8}/.test(text) ? `${text.slice(6, 8)}/${text.slice(4, 6)}/${text.slice(0, 4)}` : text || '—')

/** Creates an element. Text is always set as text, never as HTML, because it comes from HL7 messages. */
function el(tag, props = {}, ...children) {
  const node = document.createElement(tag)
  for (const [key, value] of Object.entries(props)) {
    if (key.startsWith('aria-') || key === 'colspan') {
      if (value) node.setAttribute(key, value)
    } else node[key] = value
  }
  node.append(...children)
  return node
}

const badge = (text, tone) => el('span', { className: `badge ${tone ? `badge--${tone}` : ''}` }, text)

async function api(path, body) {
  const options = body === undefined ? {} : {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': document.cookie.match(/lis_csrftoken=([^;]+)/)?.[1] || '' },
    body: JSON.stringify(body),
  }
  let response
  try {
    response = await fetch(`/api/${path}`, options)
  } catch {
    throw new Error('The simulator is not running.')
  }
  const data = await response.json().catch(() => null)
  if (!response.ok) throw new Error(data?.detail || `Request failed (${response.status}).`)
  return data
}

function notify(text, ok) {
  $('notice').textContent = text
  $('notice').className = `notice notice--${ok ? 'ok' : 'error'}`
  $('notice').hidden = !text
}

// ------------------------------------------------------------------ incoming orders

function orderStatusBadges(order) {
  const list = [badge(capitalize(order.status), STATUS_TONES[order.status])]
  if (order.results_sent_at) list.push(badge('Sent', 'green'))
  return list
}

function renderOrders() {
  const open = orders.filter((o) => !o.results_sent_at && o.status !== 'cancelled').length
  $('order-count').textContent = open
  $('order-count').hidden = !open
  if (!orders.length) {
    $('order-list').replaceChildren(el('p', { className: 'empty' }, 'No orders yet. Place a lab order in LiverLink and it appears here.'))
    return
  }
  const focused = document.activeElement?.dataset?.order
  $('order-list').replaceChildren(...orders.map((order) => {
    const item = el('button', { type: 'button', className: 'order-item', 'aria-current': order.id === selected?.id && 'true', onclick: () => openOrder(order.id) },
      el('div', { className: 'order-item__row' },
        el('span', { className: 'order-item__acc' }, order.accession_number),
        el('span', {}, ...orderStatusBadges(order))),
      el('div', { className: 'order-item__sub' }, `${order.patient_name || 'Unnamed'}, MRN ${order.mrn}`),
      el('div', { className: 'order-item__sub order-item__row' },
        el('span', {}, `Order #${order.placer_order_id}, ${formatTime(order.received_at)}`),
        order.priority === 'urgent' ? badge('Urgent', 'red') : ''))
    item.dataset.order = order.id
    return item
  }))
  if (focused) $('order-list').querySelector(`[data-order="${focused}"]`)?.focus()
}

async function refreshOrders() {
  const data = await api('orders/')
  if (JSON.stringify(data.orders) !== JSON.stringify(orders)) {
    orders = data.orders
    renderOrders()
  }
  // Reload the open order only when its status changed (e.g. LiverLink cancelled it), so typing is never lost.
  const row = orders.find((o) => o.id === selected?.id)
  if (row && !busy && (row.status !== selected.status || row.results_sent_at !== selected.results_sent_at)) await openOrder(row.id)
}

async function openOrder(id) {
  const number = ++readNumber
  try {
    const order = await api(`orders/${id}/`)
    if (number !== readNumber) return
    showOrder(order)
  } catch (error) {
    notify(error.message, false)
  }
}

function showOrder(order) {
  selected = order
  renderDetail()
  renderOrders()
}

/** Runs one action on the open order, then shows the order as the server returned it. */
async function act(action, success) {
  if (busy) return
  busy = true
  readNumber++
  setButtons(true)
  try {
    showOrder(await action())
    notify(success, true)
  } catch (error) {
    notify(error.message, false)
    setButtons(false)
  } finally {
    busy = false
  }
  refresh()
}

const setButtons = (disabled) =>
  $('order-detail').querySelectorAll('[data-enabled="true"]').forEach((button) => { button.disabled = disabled })

function actionButton(label, className, enabled, onclick, extra = {}) {
  const button = el('button', { type: 'button', className, disabled: !enabled, onclick, ...extra }, label)
  button.dataset.enabled = enabled
  return button
}

// ------------------------------------------------------------------ order details, workflow and results

function renderDetail() {
  const box = $('order-detail')
  if (!selected) {
    box.replaceChildren(el('p', { className: 'empty' }, 'Choose an order to see its details.'))
    return
  }
  const order = selected
  const editing = order.status === 'processing'
  const facts = [
    ['Accession number', order.accession_number], ['Internal order ID', `#${order.placer_order_id}`],
    ['Patient MRN', order.mrn], ['Patient', order.patient_name || '—'],
    ['Date of birth', formatBirthDate(order.birth_date)], ['Sex', order.sex || '—'],
    ['Ordered by', order.ordered_by || '—'], ['Sent by', order.sender], ['Priority', capitalize(order.priority)],
  ]

  const note = order.status === 'cancelled' ? 'LiverLink cancelled this order.'
    : order.results_sent_at ? `Results sent and accepted on ${formatTime(order.results_sent_at)}.`
      : order.status === 'received' ? 'Set the sample to Processing to enter results.'
        : order.status === 'completed' ? 'Ready to send. Go back to Processing to correct a value.' : ''

  box.replaceChildren(
    el('h2', { className: 'card__title' }, `Order ${order.accession_number} `, ...orderStatusBadges(order)),
    el('div', { className: 'card__body' },
      el('dl', { className: 'facts' }, ...facts.map(([name, value]) => el('div', {}, el('dt', {}, name), el('dd', {}, value)))),
      el('h3', { className: 'section-title' }, 'Sample status'),
      el('div', { className: 'steps' }, ...STEPS.flatMap((step, index) => [
        index ? el('span', { className: 'arrow' }, '→') : '',
        actionButton(capitalize(step), 'step', order.allowed_moves.includes(step), () => changeStatus(step),
          { 'aria-current': step === order.status && 'step' }),
      ])),
      el('h3', { className: 'section-title' }, `Tests and results (${order.tests.length})`),
      el('div', { className: 'table-wrap results' },
        el('table', {},
          el('thead', {}, el('tr', {}, ...['Test', 'Value', 'Unit', 'Reference range', 'Flag'].map((h) => el('th', { scope: 'col' }, h)))),
          el('tbody', {}, ...order.tests.map((test) => resultRow(test, editing))))),
      el('div', { className: 'actions' },
        actionButton('Save results', 'btn', editing, () => act(saveResults, 'Results saved.')),
        actionButton('Send results to LiverLink', 'btn btn--primary', order.status === 'completed' && !order.results_sent_at,
          () => act(() => api(`orders/${order.id}/send/`, {}), 'ORU^R01 sent. LiverLink answered AA (accepted).')),
        el('span', { className: 'small' }, note))),
  )
}

function resultRow(test, editing) {
  const input = (key, label, extra = {}) => {
    const node = el('input', { value: test[key], disabled: !editing, 'aria-label': `${test.name} ${label}`, ...extra })
    node.dataset.key = key
    return node
  }
  const value = input('value', 'value', { inputMode: 'decimal', maxLength: 12 })
  const range = input('reference_range', 'reference range', { maxLength: 50 })
  const flag = el('select', { disabled: !editing, 'aria-label': `${test.name} flag` },
    el('option', { value: '' }, '—'),
    ...Object.entries(FLAGS).map(([code, label]) => el('option', { value: code }, label)))
  flag.value = test.flag
  flag.dataset.key = 'flag'
  // The flag is suggested from the range; staff can still change it.
  value.oninput = range.oninput = () => { flag.value = suggestFlag(value.value, range.value, flag.value) }

  const row = el('tr', {},
    el('td', {}, el('div', { className: 'test-name' }, test.name), el('div', { className: 'small mono' }, test.code)),
    ...[value, input('unit', 'unit', { maxLength: 30 }), range, flag].map((node) => el('td', {}, node)))
  row.dataset.test = test.id
  return row
}

/** N, L or H from a range such as "0.1-1.2"; keeps `current` when there is no usable range. */
function suggestFlag(value, range, current) {
  if (value.trim() === '') return ''
  const match = range.match(/^\s*([\d.]+)\s*-\s*([\d.]+)\s*$/)
  const number = Number(value)
  if (!match || Number.isNaN(number)) return current
  return number < Number(match[1]) ? 'L' : number > Number(match[2]) ? 'H' : 'N'
}

function saveResults() {
  const results = [...$('order-detail').querySelectorAll('tr[data-test]')].map((row) => {
    const data = { id: Number(row.dataset.test) }
    row.querySelectorAll('[data-key]').forEach((node) => { data[node.dataset.key] = node.value })
    return data
  })
  return api(`orders/${selected.id}/results/`, { results })
}

function changeStatus(status) {
  const { id, status: current } = selected
  act(async () => {
    if (current === 'processing') await saveResults() // leaving the entry step keeps what was typed
    return api(`orders/${id}/status/`, { status })
  }, `Sample is now ${status}.`)
}

// ------------------------------------------------------------------ HL7 message monitor

const directionBadge = (direction) => (direction === 'inbound' ? badge('← Inbound', 'blue') : badge('→ Outbound', 'amber'))
const ackBadge = (code) => (code ? badge(code, code === 'AA' ? 'green' : 'red') : '—')

let messagesShown = ''

async function refreshMessages() {
  const { messages } = await api('messages/')
  const snapshot = JSON.stringify(messages)
  if (snapshot === messagesShown) return
  messagesShown = snapshot
  $('message-list').replaceChildren(...(messages.length ? messages.map((msg) => el('tr', {},
    el('td', {}, formatTime(msg.created_at)),
    el('td', {}, directionBadge(msg.direction)),
    el('td', {}, el('div', { className: 'test-name' }, msg.message_type), el('div', { className: 'small mono' }, msg.control_id || '—')),
    el('td', {}, ackBadge(msg.ack_code)),
    el('td', {}, badge(capitalize(msg.status), msg.status === 'error' ? 'red' : 'green'),
      msg.error_text ? el('div', { className: 'small error-text' }, msg.error_text) : ''),
    el('td', {}, el('button', { type: 'button', className: 'btn btn--link', 'aria-label': `View message ${msg.control_id}`, onclick: () => openMessage(msg.id) }, 'View')),
  )) : [el('tr', {}, el('td', { className: 'empty', colspan: '6' }, 'No HL7 messages yet.'))]))
}

async function openMessage(id) {
  openMessageId = id
  try {
    const msg = await api(`messages/${id}/`)
    if (openMessageId !== id) return
    const box = $('message-detail')
    box.replaceChildren(
      el('h2', { className: 'card__title' }, `${msg.message_type}, ${msg.control_id || 'no control ID'}`),
      el('div', { className: 'card__body columns' }, rawMessage('Message', msg.raw_message), rawMessage('Acknowledgement', msg.ack_message)))
    box.hidden = false
    box.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  } catch (error) {
    notify(error.message, false)
  }
}

/** One HL7 segment per line, segment name highlighted. */
function rawMessage(title, text) {
  const lines = text.split(/\r\n|\r|\n/).filter(Boolean)
  return el('div', {}, el('p', { className: 'small' }, title),
    lines.length ? el('pre', { className: 'raw', tabIndex: 0 }, ...lines.map((line) => el('div', {}, el('b', {}, line.slice(0, 3)), line.slice(3))))
      : el('p', {}, 'No acknowledgement received.'))
}

// ------------------------------------------------------------------ tabs and automatic refresh

let connectionLost = false

async function refresh() {
  try {
    await refreshOrders()
    if (!$('tab-messages').hidden) await refreshMessages()
    if (connectionLost) notify('', true)
    connectionLost = false
  } catch (error) {
    connectionLost = true
    notify(error.message, false)
  }
}

document.querySelectorAll('[data-tab]').forEach((button) => {
  button.onclick = () => {
    document.querySelectorAll('[data-tab]').forEach((other) => other.removeAttribute('aria-current'))
    button.setAttribute('aria-current', 'page')
    $('tab-orders').hidden = button.dataset.tab !== 'orders'
    $('tab-messages').hidden = button.dataset.tab !== 'messages'
    notify('', true)
    refresh()
  }
})

renderDetail()
renderOrders()
refresh()
setInterval(refresh, REFRESH_MS)
