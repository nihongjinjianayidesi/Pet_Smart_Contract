import { useMemo } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { AlertTriangle, ArrowRight, ChevronLeft, MapPin, Truck } from 'lucide-react'
import StatusPill, { type StatusTone } from '../components/StatusPill'
import { addException, buildFulfillmentSteps, getLatestOrder, getOrderById, setOrderStatus } from '../lib/module6/storage'
import type { ExceptionCase, Order } from '../lib/module6/types'

function toneByStatus(status: Order['status']): StatusTone {
  if (status === '运输中') return 'orange'
  if (status === '已完成') return 'green'
  if (status === '异常处理中') return 'red'
  if (status === '已下单') return 'blue'
  return 'zinc'
}

export default function Fulfillment() {
  const { orderId } = useParams()
  const navigate = useNavigate()

  const order = useMemo(() => {
    if (orderId) return getOrderById(orderId)
    return getLatestOrder()
  }, [orderId])

  if (!order) {
    return (
      <main className="max-w-5xl mx-auto px-4 py-8">
        <div className="bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm">
          <p className="text-sm font-semibold text-zinc-700">暂无订单，请先前往“托运报价”生成订单。</p>
          <Link
            to="/quote"
            className="mt-4 inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-orange-500 text-white font-black hover:bg-orange-600"
          >
            去报价下单
            <ArrowRight size={16} />
          </Link>
        </div>
      </main>
    )
  }

  const steps = buildFulfillmentSteps(order)

  const triggerException = () => {
    setOrderStatus(order.id, '异常处理中')
    const ex: ExceptionCase = {
      id: `EX-${order.id}`,
      orderId: order.id,
      type: '争议',
      status: '已上报',
      createdAt: '2026-04-16 11:20',
      summary: '到站体检发现轻微应激反应，触发争议处理（演示）',
      evidenceRecordId: `EV-${order.id}-handover`
    }
    addException(ex)
    navigate(`/exceptions?orderId=${encodeURIComponent(order.id)}`)
  }

  return (
    <div className="min-h-screen bg-zinc-50 pb-24">
      <header className="bg-white px-4 py-4 shadow-sm flex items-center gap-3 sticky top-0 z-20">
        <button onClick={() => navigate(-1)} className="p-2 hover:bg-zinc-100 rounded-full transition-colors">
          <ChevronLeft size={24} className="text-zinc-900" />
        </button>
        <div className="min-w-0">
          <h1 className="text-lg font-bold text-zinc-900">履约追踪</h1>
          <p className="text-zinc-400 text-xs font-mono truncate">NO. {order.id}</p>
        </div>
        <div className="ml-auto">
          <StatusPill tone={toneByStatus(order.status)}>{order.status}</StatusPill>
        </div>
      </header>

      <main className="max-w-2xl mx-auto">
        <div className="w-full h-56 bg-zinc-200 relative overflow-hidden">
          <img
            src="https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=simple+minimalist+map+route+with+truck+icon&image_size=landscape_16_9"
            alt="Map"
            className="w-full h-full object-cover opacity-80"
          />
          <div className="absolute bottom-4 left-4 right-4 bg-white/90 backdrop-blur-sm p-3 rounded-xl shadow-lg flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
              <Truck className="text-orange-600 w-5 h-5" />
            </div>
            <div className="min-w-0">
              <p className="text-xs text-zinc-500">线路</p>
              <p className="text-sm font-bold text-zinc-900 truncate">
                {order.fromCity} → {order.toCity} · {order.petName}（{order.petType}）
              </p>
            </div>
          </div>
        </div>

        <div className="mx-4 -mt-6 relative z-10 bg-white rounded-2xl p-4 shadow-xl border border-zinc-100">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-xs font-black text-zinc-400">订单金额</p>
              <p className="mt-1 text-xl font-black text-zinc-900 font-mono">¥{order.price.total}</p>
            </div>
            <div className="text-right">
              <p className="text-xs font-black text-zinc-400">创建时间</p>
              <p className="mt-1 text-sm font-bold text-zinc-900">{order.createdAt.slice(0, 10)}</p>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-3 text-xs font-semibold text-zinc-700">
            <div className="rounded-xl bg-zinc-50 border border-zinc-100 p-3">
              <p className="text-[10px] font-black text-zinc-500">关键节点</p>
              <p className="mt-1">{steps[1]?.location ?? '—'}</p>
            </div>
            <div className="rounded-xl bg-zinc-50 border border-zinc-100 p-3">
              <p className="text-[10px] font-black text-zinc-500">预计送达</p>
              <p className="mt-1">2026-04-16 18:20</p>
            </div>
          </div>
        </div>

        <div className="m-4 bg-white rounded-2xl p-6 shadow-md border border-zinc-100">
          <h3 className="text-base font-bold text-zinc-900 mb-6">履约时间线</h3>
          <div className="space-y-8">
            {steps.map((step, index) => (
              <div key={`${step.stage}-${index}`} className="relative flex gap-4">
                {index !== steps.length - 1 && <div className="absolute left-3 top-7 bottom-[-20px] w-0.5 bg-zinc-100"></div>}
                <div className="relative z-10">
                  {index === 0 ? (
                    <div className="w-6 h-6 bg-orange-500 rounded-full flex items-center justify-center ring-4 ring-orange-100">
                      <div className="w-2 h-2 bg-white rounded-full"></div>
                    </div>
                  ) : (
                    <div className="w-6 h-6 bg-white border-2 border-zinc-200 rounded-full flex items-center justify-center">
                      <MapPin className="w-3.5 h-3.5 text-zinc-300" />
                    </div>
                  )}
                </div>

                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className={`text-sm font-bold ${index === 0 ? 'text-orange-600' : 'text-zinc-900'}`}>{step.stage}</h4>
                    <span className="text-xs text-zinc-400">{step.time}</span>
                  </div>
                  <p className="text-sm font-medium text-zinc-600 mb-1">{step.location}</p>
                  <p className="text-xs text-zinc-400 leading-relaxed">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="m-4 bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h3 className="text-base font-black text-zinc-900">异常演示（用于截图链路）</h3>
              <p className="mt-2 text-sm font-semibold text-zinc-600">点击后会为当前订单写入一条“异常/争议”记录，并跳转到异常处理页。</p>
            </div>
            <button
              type="button"
              onClick={triggerException}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-red-500 text-white font-black hover:bg-red-600"
            >
              <AlertTriangle size={16} />
              触发异常
            </button>
          </div>

          <div className="mt-4 flex flex-wrap gap-2">
            <Link
              to={`/exceptions?orderId=${encodeURIComponent(order.id)}`}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-800 font-black hover:bg-zinc-50"
            >
              查看异常处理
              <ArrowRight size={16} />
            </Link>
            <Link
              to={`/evidence?orderId=${encodeURIComponent(order.id)}`}
              className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-white border border-zinc-200 text-zinc-800 font-black hover:bg-zinc-50"
            >
              进入证据校验
              <ArrowRight size={16} />
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
