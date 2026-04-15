import { Link, useSearchParams } from 'react-router-dom'
import { ArrowRight, ClipboardList } from 'lucide-react'
import StatusPill, { type StatusTone } from '../components/StatusPill'
import MaskedText from '../components/MaskedText'
import { getOrders } from '../lib/module6/storage'

function toneByStatus(status: string): StatusTone {
  if (status === '运输中') return 'orange'
  if (status === '已完成') return 'green'
  if (status === '异常处理中') return 'red'
  if (status === '已下单') return 'blue'
  return 'zinc'
}

export default function Orders() {
  const [sp] = useSearchParams()
  const focus = sp.get('focus')
  const orders = getOrders()

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-zinc-900 tracking-tight">我的订单</h1>
          <p className="mt-2 text-sm font-semibold text-zinc-600">列表页用于截图：订单号、状态标签、脱敏后的托运人信息。</p>
        </div>
        <Link
          to="/quote"
          className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-orange-500 text-white font-black hover:bg-orange-600"
        >
          去报价下单
          <ArrowRight size={16} />
        </Link>
      </div>

      <section className="mt-6 bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-black text-zinc-900">订单列表</h2>
          <div className="inline-flex items-center gap-2 text-xs font-black text-zinc-500">
            <ClipboardList size={14} />
            共 {orders.length} 条
          </div>
        </div>

        <div className="mt-5 divide-y divide-zinc-100">
          {orders.map((o) => (
            <div
              key={o.id}
              className={`py-4 flex flex-col sm:flex-row sm:items-center gap-3 ${
                focus === o.id ? 'bg-orange-50/60 -mx-3 px-3 rounded-xl' : ''
              }`}
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="text-sm font-black text-zinc-900">
                    {o.fromCity} → {o.toCity} · {o.petName}（{o.petType}）
                  </p>
                  <StatusPill tone={toneByStatus(o.status)}>{o.status}</StatusPill>
                  {focus === o.id ? <StatusPill tone="orange">新生成</StatusPill> : null}
                </div>
                <div className="mt-2 grid grid-cols-1 sm:grid-cols-3 gap-2 text-xs font-semibold text-zinc-600">
                  <div>
                    订单号：<span className="font-mono text-zinc-900">{o.id}</span>
                  </div>
                  <div>
                    手机号：<MaskedText value={o.ownerPhone} kind="phone" className="text-zinc-900" />
                  </div>
                  <div>
                    身份证：<MaskedText value={o.ownerIdCard} kind="idCard" className="text-zinc-900" />
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Link
                  to={`/fulfillment/${encodeURIComponent(o.id)}`}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-zinc-900 text-white font-black hover:bg-zinc-800"
                >
                  履约追踪
                  <ArrowRight size={16} />
                </Link>
                <Link
                  to={`/evidence?orderId=${encodeURIComponent(o.id)}`}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-800 font-black hover:bg-zinc-50"
                >
                  证据校验
                  <ArrowRight size={16} />
                </Link>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mt-6 bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm">
        <h2 className="text-base font-black text-zinc-900">截图建议</h2>
        <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm font-semibold text-zinc-700">
          <div className="rounded-xl bg-zinc-50 border border-zinc-100 p-4">
            <p className="text-xs font-black text-zinc-500">建议 1</p>
            <p className="mt-1">截图时确保列表含：订单号、状态标签、脱敏字段。</p>
          </div>
          <div className="rounded-xl bg-zinc-50 border border-zinc-100 p-4">
            <p className="text-xs font-black text-zinc-500">建议 2</p>
            <p className="mt-1">选择“运输中”订单进入履约追踪页截图时间线。</p>
          </div>
          <div className="rounded-xl bg-zinc-50 border border-zinc-100 p-4">
            <p className="text-xs font-black text-zinc-500">建议 3</p>
            <p className="mt-1">选择“异常处理中”订单进入异常处理页截图处理状态。</p>
          </div>
        </div>
      </section>
    </main>
  )
}
