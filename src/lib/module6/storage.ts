import { sha256HexFromText } from '../crypto'
import type { EvidenceRecord, ExceptionCase, FulfillmentStep, Order, OrderStatus } from './types'
import { tryLoadDemoDataFromApi } from './remote'

const KEYS = {
  orders: 'petsc_demo_orders_v1',
  evidence: 'petsc_demo_evidence_v1',
  exceptions: 'petsc_demo_exceptions_v1',
  counter: 'petsc_demo_counter_v1'
} as const

function nowIso() {
  return new Date().toISOString()
}

function readJson<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    if (!raw) return fallback
    return JSON.parse(raw) as T
  } catch {
    return fallback
  }
}

function writeJson(key: string, value: unknown) {
  localStorage.setItem(key, JSON.stringify(value))
}

function nextOrderId() {
  const current = readJson<number>(KEYS.counter, 1)
  writeJson(KEYS.counter, current + 1)
  const seq = String(current).padStart(3, '0')
  return `PSC20260415${seq}`
}

export function resetDemoData() {
  Object.values(KEYS).forEach((k) => localStorage.removeItem(k))
}

export async function ensureSeedData() {
  const existingOrders = readJson<Order[]>(KEYS.orders, [])
  const existingEvidence = readJson<EvidenceRecord[]>(KEYS.evidence, [])
  const existingExceptions = readJson<ExceptionCase[]>(KEYS.exceptions, [])

  if (existingOrders.length && existingEvidence.length) return

  const remote = await tryLoadDemoDataFromApi(import.meta.env.VITE_PETSC_API_BASE)
  if (remote) {
    writeJson(KEYS.orders, remote.orders)
    writeJson(KEYS.evidence, remote.evidence)
    writeJson(KEYS.exceptions, remote.exceptions ?? [])
    writeJson(KEYS.counter, remote.orders.length + 1)
    return
  }

  const order1: Order = {
    id: 'PSC20260415001',
    createdAt: '2026-04-15T09:30:00.000Z',
    fromCity: '上海',
    toCity: '北京',
    petName: '小白',
    petType: '猫',
    weightKg: 4.5,
    ownerName: '张**',
    ownerPhone: '13812345678',
    ownerIdCard: '110101199901011234',
    pickupAddress: '上海市徐汇区虹桥路 100 号',
    status: '运输中',
    price: { base: 180, distanceKm: 1067, weightKg: 4.5, insurance: 30, total: 210 }
  }

  const order2: Order = {
    id: 'PSC20260415002',
    createdAt: '2026-04-15T10:10:00.000Z',
    fromCity: '广州',
    toCity: '深圳',
    petName: '大黄',
    petType: '狗',
    weightKg: 12.3,
    ownerName: '李**',
    ownerPhone: '13900001111',
    ownerIdCard: '440101199812129999',
    pickupAddress: '广州市天河区体育西路 88 号',
    status: '异常处理中',
    price: { base: 120, distanceKm: 137, weightKg: 12.3, insurance: 50, total: 170 }
  }

  const seedOrders = [order1, order2]
  writeJson(KEYS.orders, seedOrders)
  writeJson(KEYS.counter, 3)

  const e1Content = `PetSC Evidence Demo - ${order1.id}`
  const e2Content = `PetSC Evidence Demo - ${order2.id}`
  const [h1, h2] = await Promise.all([sha256HexFromText(e1Content), sha256HexFromText(e2Content)])

  const evidence: EvidenceRecord[] = [
    {
      id: `EV-${order1.id}-handover`,
      orderId: order1.id,
      docType: '交接单',
      createdAt: '2026-04-15T09:35:00.000Z',
      onChainHash: h1,
      offChainHash: h1,
      contentHint: e1Content
    },
    {
      id: `EV-${order2.id}-handover`,
      orderId: order2.id,
      docType: '交接单',
      createdAt: '2026-04-15T10:15:00.000Z',
      onChainHash: h2,
      offChainHash: h2,
      contentHint: e2Content
    }
  ]
  writeJson(KEYS.evidence, evidence)

  const exceptions: ExceptionCase[] = [
    {
      id: 'EX-20260415-001',
      orderId: order2.id,
      type: '延误',
      status: '处理中',
      createdAt: '2026-04-15 12:20',
      summary: '中转站天气原因导致航班延误，预计顺延 6 小时',
      evidenceRecordId: `EV-${order2.id}-handover`
    }
  ]
  writeJson(KEYS.exceptions, existingExceptions.length ? existingExceptions : exceptions)
}

export function getOrders() {
  return readJson<Order[]>(KEYS.orders, [])
}

export function getOrderById(orderId: string) {
  return getOrders().find((o) => o.id === orderId) ?? null
}

export function getLatestOrder() {
  const orders = getOrders()
  if (!orders.length) return null
  return [...orders].sort((a, b) => b.createdAt.localeCompare(a.createdAt))[0]
}

export function getEvidenceRecords() {
  return readJson<EvidenceRecord[]>(KEYS.evidence, [])
}

export function getEvidenceByOrder(orderId: string) {
  return getEvidenceRecords().filter((e) => e.orderId === orderId)
}

export function getExceptions() {
  return readJson<ExceptionCase[]>(KEYS.exceptions, [])
}

export function setOrderStatus(orderId: string, status: OrderStatus) {
  const orders = getOrders()
  const next = orders.map((o) => (o.id === orderId ? { ...o, status } : o))
  writeJson(KEYS.orders, next)
}

export function addException(ex: ExceptionCase) {
  const all = getExceptions()
  writeJson(KEYS.exceptions, [ex, ...all])
}

export async function createOrderFromQuote(input: {
  fromCity: string
  toCity: string
  petName: string
  petType: Order['petType']
  weightKg: number
  ownerName: string
  ownerPhone: string
  ownerIdCard: string
  pickupAddress: string
}) {
  const id = nextOrderId()
  const createdAt = nowIso()
  const price = {
    base: 160,
    distanceKm: 1000,
    weightKg: input.weightKg,
    insurance: 30,
    total: 190
  }

  const order: Order = {
    id,
    createdAt,
    fromCity: input.fromCity,
    toCity: input.toCity,
    petName: input.petName,
    petType: input.petType,
    weightKg: input.weightKg,
    ownerName: input.ownerName,
    ownerPhone: input.ownerPhone,
    ownerIdCard: input.ownerIdCard,
    pickupAddress: input.pickupAddress,
    status: '已下单',
    price
  }

  const orders = getOrders()
  writeJson(KEYS.orders, [order, ...orders])

  const contentHint = `PetSC Evidence Demo - ${id}`
  const hash = await sha256HexFromText(contentHint)
  const evidence: EvidenceRecord = {
    id: `EV-${id}-handover`,
    orderId: id,
    docType: '交接单',
    createdAt,
    onChainHash: hash,
    offChainHash: hash,
    contentHint
  }
  const evidenceAll = getEvidenceRecords()
  writeJson(KEYS.evidence, [evidence, ...evidenceAll])

  return { order, evidence }
}

export function buildFulfillmentSteps(order: Order): FulfillmentStep[] {
  const base: FulfillmentStep[] = [
    { stage: '已送达', time: '2026-04-16 18:20', location: `${order.toCity} · 收货点`, description: '完成交付，签收确认', completed: order.status === '已完成' },
    { stage: '运输中', time: '2026-04-16 09:10', location: '北京中转站', description: '在途运输，状态稳定', completed: order.status !== '已下单' && order.status !== '已报价' },
    { stage: '中转中', time: '2026-04-16 03:40', location: '济南分拣中心', description: '完成分拣并转运', completed: order.status !== '已下单' && order.status !== '已报价' },
    { stage: '已发货', time: '2026-04-15 22:00', location: `${order.fromCity} · 分拨中心`, description: '离开起运地，进入干线运输', completed: true },
    { stage: '已揽收', time: '2026-04-15 18:00', location: `${order.fromCity} · 上门揽收`, description: '完成称重检查并封箱', completed: true }
  ]

  if (order.status === '异常处理中') {
    return base.map((s) => (s.stage === '运输中' ? { ...s, description: '运输中（异常处理中）', completed: false } : s))
  }
  return base
}
