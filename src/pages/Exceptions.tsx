import { Link, useSearchParams } from 'react-router-dom'
import { AlertCircle, ArrowRight, FileCheck2 } from 'lucide-react'
import StatusPill, { type StatusTone } from '../components/StatusPill'
import { getExceptions, getOrderById } from '../lib/module6/storage'

function toneByStatus(status: string): StatusTone {
  if (status === '已赔付') return 'green'
  if (status === '已解决') return 'green'
  if (status === '处理中') return 'orange'
  if (status === '已上报') return 'red'
  return 'zinc'
}

export default function Exceptions() {
  const [sp] = useSearchParams()
  const orderId = sp.get('orderId')
  const all = getExceptions()
  const list = orderId ? all.filter((x) => x.orderId === orderId) : all
  const order = orderId ? getOrderById(orderId) : null

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-zinc-900 tracking-tight">异常处理</h1>
          <p className="mt-2 text-sm font-semibold text-zinc-600">
            展示异常上报、处理状态与证据入口（演示环境：模拟数据驱动）。
          </p>
        </div>
        <Link
          to="/orders"
          className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-zinc-900 text-white font-black hover:bg-zinc-800"
        >
          返回订单列表
          <ArrowRight size={16} />
        </Link>
      </div>

      {order ? (
        <section className="mt-6 bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm">
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div>
              <p className="text-xs font-black text-zinc-400">当前订单</p>
              <p className="mt-1 text-sm font-black text-zinc-900">
                {order.fromCity} → {order.toCity} · {order.petName}（{order.petType}）
              </p>
              <p className="mt-1 text-xs font-semibold text-zinc-500 font-mono">NO. {order.id}</p>
            </div>
            <div className="flex items-center gap-2">
              <Link
                to={`/fulfillment/${encodeURIComponent(order.id)}`}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-800 font-black hover:bg-zinc-50"
              >
                履约追踪
                <ArrowRight size={16} />
              </Link>
              <Link
                to={`/evidence?orderId=${encodeURIComponent(order.id)}`}
                className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-orange-500 text-white font-black hover:bg-orange-600"
              >
                证据校验
                <FileCheck2 size={16} />
              </Link>
            </div>
          </div>
        </section>
      ) : null}

      <section className="mt-6 bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-black text-zinc-900">异常列表</h2>
          <div className="inline-flex items-center gap-2 text-xs font-black text-zinc-500">
            <AlertCircle size={14} />
            共 {list.length} 条
          </div>
        </div>

        <div className="mt-5 space-y-3">
          {list.map((ex) => (
            <div key={ex.id} className="rounded-2xl border border-zinc-100 bg-zinc-50 p-5">
              <div className="flex items-start justify-between gap-4 flex-wrap">
                <div>
                  <div className="flex items-center gap-2 flex-wrap">
                    <p className="text-sm font-black text-zinc-900">{ex.type}</p>
                    <StatusPill tone={toneByStatus(ex.status)}>{ex.status}</StatusPill>
                    <span className="text-xs font-semibold text-zinc-500 font-mono">NO. {ex.orderId}</span>
                  </div>
                  <p className="mt-2 text-sm font-semibold text-zinc-700">{ex.summary}</p>
                  <p className="mt-1 text-xs font-semibold text-zinc-500">上报时间：{ex.createdAt}</p>
                </div>
                <Link
                  to={`/evidence?orderId=${encodeURIComponent(ex.orderId)}`}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-800 font-black hover:bg-zinc-50"
                >
                  去校验证据
                  <ArrowRight size={16} />
                </Link>
              </div>

              <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-3 text-sm font-semibold text-zinc-700">
                <div className="rounded-xl bg-white border border-zinc-100 p-4">
                  <p className="text-xs font-black text-zinc-500">处理流程</p>
                  <p className="mt-1">上报 → 取证 → 评估 → 结案/赔付</p>
                </div>
                <div className="rounded-xl bg-white border border-zinc-100 p-4">
                  <p className="text-xs font-black text-zinc-500">证据策略</p>
                  <p className="mt-1">链上存 hash 锚定，链下存原文/文件</p>
                </div>
                <div className="rounded-xl bg-white border border-zinc-100 p-4">
                  <p className="text-xs font-black text-zinc-500">截图要点</p>
                  <p className="mt-1">异常类型 + 状态标签 + 证据入口</p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>
    </main>
  )
}
