import type { EvidenceRecord, ExceptionCase, Order } from './types'

async function fetchJson<T>(url: string, timeoutMs: number): Promise<T> {
  const ctrl = new AbortController()
  const id = setTimeout(() => ctrl.abort(), timeoutMs)
  try {
    const res = await fetch(url, { signal: ctrl.signal })
    if (!res.ok) throw new Error(`HTTP ${res.status}`)
    return (await res.json()) as T
  } finally {
    clearTimeout(id)
  }
}

export async function tryLoadDemoDataFromApi(baseUrl: string | undefined) {
  if (!baseUrl) return null
  const base = baseUrl.replace(/\/+$/, '')
  try {
    const [orders, evidence, exceptions] = await Promise.all([
      fetchJson<Order[]>(`${base}/demo/orders`, 600),
      fetchJson<EvidenceRecord[]>(`${base}/demo/evidence`, 600),
      fetchJson<ExceptionCase[]>(`${base}/demo/exceptions`, 600)
    ])
    if (!orders.length || !evidence.length) return null
    return { orders, evidence, exceptions }
  } catch {
    return null
  }
}

