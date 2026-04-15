import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Calculator, RefreshCcw, ArrowRight } from 'lucide-react'
import StatusPill from '../components/StatusPill'
import { createOrderFromQuote, resetDemoData } from '../lib/module6/storage'
import MaskedText from '../components/MaskedText'

export default function Quote() {
  const navigate = useNavigate()
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({
    fromCity: '上海',
    toCity: '北京',
    petName: '雪球',
    petType: '猫' as const,
    weightKg: 4.8,
    ownerName: '王**',
    ownerPhone: '13888889999',
    ownerIdCard: '310101199905051234',
    pickupAddress: '上海市徐汇区漕溪北路 88 号'
  })

  const quote = useMemo(() => {
    const base = 160
    const insurance = 30
    const distanceKm = 1067
    const total = base + insurance
    return { base, insurance, distanceKm, total }
  }, [])

  const onCreate = async () => {
    setSubmitting(true)
    try {
      const { order } = await createOrderFromQuote(form)
      navigate(`/orders?focus=${encodeURIComponent(order.id)}`)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-zinc-900 tracking-tight">托运报价</h1>
          <p className="mt-2 text-sm font-semibold text-zinc-600">演示页：生成报价后可一键下单，进入“我的订单”继续截图链路。</p>
        </div>
        <button
          type="button"
          onClick={() => {
            resetDemoData()
            location.reload()
          }}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-white border border-zinc-100 text-zinc-700 font-black hover:bg-zinc-50"
        >
          <RefreshCcw size={16} />
          重置演示数据
        </button>
      </div>

      <div className="mt-6 grid grid-cols-1 lg:grid-cols-2 gap-4">
        <section className="bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-black text-zinc-900">基础信息</h2>
            <StatusPill tone="orange">数据来源：Mock/演示</StatusPill>
          </div>

          <div className="mt-5 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <label className="space-y-1">
              <span className="text-xs font-black text-zinc-500">起运城市</span>
              <input
                value={form.fromCity}
                onChange={(e) => setForm((s) => ({ ...s, fromCity: e.target.value }))}
                className="w-full bg-zinc-50 border border-zinc-100 rounded-xl px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-orange-200"
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs font-black text-zinc-500">目的城市</span>
              <input
                value={form.toCity}
                onChange={(e) => setForm((s) => ({ ...s, toCity: e.target.value }))}
                className="w-full bg-zinc-50 border border-zinc-100 rounded-xl px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-orange-200"
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs font-black text-zinc-500">宠物名</span>
              <input
                value={form.petName}
                onChange={(e) => setForm((s) => ({ ...s, petName: e.target.value }))}
                className="w-full bg-zinc-50 border border-zinc-100 rounded-xl px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-orange-200"
              />
            </label>
            <label className="space-y-1">
              <span className="text-xs font-black text-zinc-500">体重（kg）</span>
              <input
                value={form.weightKg}
                type="number"
                step="0.1"
                onChange={(e) => setForm((s) => ({ ...s, weightKg: Number(e.target.value) }))}
                className="w-full bg-zinc-50 border border-zinc-100 rounded-xl px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-orange-200"
              />
            </label>

            <label className="space-y-1 sm:col-span-2">
              <span className="text-xs font-black text-zinc-500">上门取件地址（演示脱敏）</span>
              <input
                value={form.pickupAddress}
                onChange={(e) => setForm((s) => ({ ...s, pickupAddress: e.target.value }))}
                className="w-full bg-zinc-50 border border-zinc-100 rounded-xl px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-orange-200"
              />
              <p className="text-xs font-semibold text-zinc-500">
                前端展示：<MaskedText value={form.pickupAddress} kind="address" className="text-zinc-700" />
              </p>
            </label>
          </div>

          <div className="mt-6 border-t border-zinc-100 pt-5">
            <h3 className="text-sm font-black text-zinc-900">托运人信息（演示脱敏）</h3>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 gap-4">
              <label className="space-y-1">
                <span className="text-xs font-black text-zinc-500">手机号</span>
                <input
                  value={form.ownerPhone}
                  onChange={(e) => setForm((s) => ({ ...s, ownerPhone: e.target.value }))}
                  className="w-full bg-zinc-50 border border-zinc-100 rounded-xl px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-orange-200"
                />
                <p className="text-xs font-semibold text-zinc-500">
                  展示：<MaskedText value={form.ownerPhone} kind="phone" className="text-zinc-700" />
                </p>
              </label>
              <label className="space-y-1">
                <span className="text-xs font-black text-zinc-500">身份证号</span>
                <input
                  value={form.ownerIdCard}
                  onChange={(e) => setForm((s) => ({ ...s, ownerIdCard: e.target.value }))}
                  className="w-full bg-zinc-50 border border-zinc-100 rounded-xl px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-orange-200"
                />
                <p className="text-xs font-semibold text-zinc-500">
                  展示：<MaskedText value={form.ownerIdCard} kind="idCard" className="text-zinc-700" />
                </p>
              </label>
            </div>
          </div>
        </section>

        <section className="bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-black text-zinc-900">报价结果</h2>
            <div className="inline-flex items-center gap-2 text-xs font-black text-zinc-500">
              <Calculator size={14} />
              演示估算
            </div>
          </div>

          <div className="mt-5 rounded-2xl bg-zinc-50 border border-zinc-100 p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm font-black text-zinc-900">
                {form.fromCity} → {form.toCity}
              </p>
              <StatusPill tone="blue">已报价</StatusPill>
            </div>
            <p className="mt-1 text-xs font-semibold text-zinc-500">里程估算：{quote.distanceKm} km · 宠物：{form.petName}（{form.petType}）</p>

            <div className="mt-4 space-y-2 text-sm font-semibold text-zinc-700">
              <div className="flex items-center justify-between">
                <span>基础运费</span>
                <span className="font-mono">¥{quote.base}</span>
              </div>
              <div className="flex items-center justify-between">
                <span>保价/保险</span>
                <span className="font-mono">¥{quote.insurance}</span>
              </div>
              <div className="h-px bg-zinc-200 my-2"></div>
              <div className="flex items-center justify-between text-zinc-900">
                <span className="font-black">合计</span>
                <span className="font-black font-mono">¥{quote.total}</span>
              </div>
            </div>
          </div>

          <button
            type="button"
            disabled={submitting}
            onClick={onCreate}
            className="mt-5 w-full inline-flex items-center justify-center gap-2 px-4 py-3 rounded-2xl bg-orange-500 text-white font-black hover:bg-orange-600 disabled:opacity-60"
          >
            生成订单并进入我的订单
            <ArrowRight size={18} />
          </button>

          <div className="mt-4 text-xs font-semibold text-zinc-500 space-y-1">
            <p>该按钮会创建 1 条“已下单”订单，并生成 1 条交接单存证记录（hash 用于后续证据校验截图）。</p>
            <p>如需重复截图链路，可点右上角“重置演示数据”。</p>
          </div>
        </section>
      </div>
    </main>
  )
}

