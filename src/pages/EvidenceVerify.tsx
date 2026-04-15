import { useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Download, FileCheck2, FileX2, ShieldCheck } from 'lucide-react'
import MaskedText from '../components/MaskedText'
import StatusPill from '../components/StatusPill'
import { sha256HexFromFile } from '../lib/crypto'
import { SENSITIVE_FIELDS } from '../lib/privacy'
import { getEvidenceRecords, getLatestOrder, getOrderById } from '../lib/module6/storage'

type CompareTarget = 'onChain' | 'offChain'

function downloadText(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}

export default function EvidenceVerify() {
  const [sp] = useSearchParams()
  const orderIdFromQuery = sp.get('orderId')
  const evidenceAll = getEvidenceRecords()
  const defaultOrderId = orderIdFromQuery ?? getLatestOrder()?.id ?? (evidenceAll[0]?.orderId ?? '')

  const [orderId, setOrderId] = useState(defaultOrderId)
  const order = useMemo(() => (orderId ? getOrderById(orderId) : null), [orderId])
  const evidenceList = useMemo(() => evidenceAll.filter((e) => e.orderId === orderId), [evidenceAll, orderId])
  const [evidenceId, setEvidenceId] = useState(evidenceList[0]?.id ?? '')
  const evidence = useMemo(() => evidenceList.find((e) => e.id === evidenceId) ?? evidenceList[0] ?? null, [evidenceId, evidenceList])

  const [compareTarget, setCompareTarget] = useState<CompareTarget>('onChain')
  const [reveal, setReveal] = useState(false)
  const [fileName, setFileName] = useState('')
  const [fileHash, setFileHash] = useState<string>('')
  const [computing, setComputing] = useState(false)
  const expectedHash = evidence ? (compareTarget === 'onChain' ? evidence.onChainHash : evidence.offChainHash) : ''
  const passed = !!fileHash && !!expectedHash && fileHash === expectedHash

  const onPickFile = async (file: File | null) => {
    if (!file) return
    setFileName(file.name)
    setComputing(true)
    setFileHash('')
    try {
      const hash = await sha256HexFromFile(file)
      setFileHash(hash)
    } finally {
      setComputing(false)
    }
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-black text-zinc-900 tracking-tight">证据校验</h1>
          <p className="mt-2 text-sm font-semibold text-zinc-600">选择本地文件 → 计算 SHA-256 → 与记录 hash 对比 → 显示通过/失败。</p>
        </div>
        <div className="flex items-center gap-2">
          <StatusPill tone="blue">链上：hash 锚定（mock）</StatusPill>
          <StatusPill tone="zinc">链下：原文/文件 + hash</StatusPill>
        </div>
      </div>

      <section className="mt-6 bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div className="rounded-2xl bg-zinc-50 border border-zinc-100 p-5">
            <h2 className="text-base font-black text-zinc-900">1）选择校验对象</h2>
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <label className="space-y-1">
                <span className="text-xs font-black text-zinc-500">订单</span>
                <select
                  value={orderId}
                  onChange={(e) => {
                    setOrderId(e.target.value)
                    setEvidenceId('')
                    setFileHash('')
                    setFileName('')
                  }}
                  className="w-full bg-white border border-zinc-200 rounded-xl px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-orange-200"
                >
                  {Array.from(new Set(evidenceAll.map((e) => e.orderId))).map((id) => (
                    <option key={id} value={id}>
                      {id}
                    </option>
                  ))}
                </select>
              </label>

              <label className="space-y-1">
                <span className="text-xs font-black text-zinc-500">证据类型</span>
                <select
                  value={evidence?.id ?? ''}
                  onChange={(e) => {
                    setEvidenceId(e.target.value)
                    setFileHash('')
                    setFileName('')
                  }}
                  className="w-full bg-white border border-zinc-200 rounded-xl px-3 py-2 text-sm font-semibold outline-none focus:ring-2 focus:ring-orange-200"
                >
                  {evidenceList.map((ev) => (
                    <option key={ev.id} value={ev.id}>
                      {ev.docType} · {ev.createdAt.slice(0, 10)}
                    </option>
                  ))}
                </select>
              </label>
            </div>

            <div className="mt-4 flex flex-wrap items-center gap-2 text-sm font-semibold">
              <span className="text-zinc-600">对比对象：</span>
              <button
                type="button"
                onClick={() => setCompareTarget('onChain')}
                className={`px-3 py-2 rounded-xl font-black border ${
                  compareTarget === 'onChain'
                    ? 'bg-orange-500 text-white border-orange-500'
                    : 'bg-white text-zinc-800 border-zinc-200 hover:bg-zinc-50'
                }`}
              >
                链上锚定 hash
              </button>
              <button
                type="button"
                onClick={() => setCompareTarget('offChain')}
                className={`px-3 py-2 rounded-xl font-black border ${
                  compareTarget === 'offChain'
                    ? 'bg-orange-500 text-white border-orange-500'
                    : 'bg-white text-zinc-800 border-zinc-200 hover:bg-zinc-50'
                }`}
              >
                链下存证 hash
              </button>
              <label className="ml-auto inline-flex items-center gap-2 text-xs font-black text-zinc-500">
                <input
                  type="checkbox"
                  checked={reveal}
                  onChange={(e) => setReveal(e.target.checked)}
                  className="accent-orange-500"
                />
                显示完整 hash
              </label>
            </div>

            <div className="mt-4 rounded-2xl bg-white border border-zinc-100 p-4">
              <p className="text-xs font-black text-zinc-500">期望 hash（{compareTarget === 'onChain' ? '链上' : '链下'}）</p>
              <p className="mt-2 text-sm font-black text-zinc-900 break-all">
                {expectedHash ? <MaskedText value={expectedHash} kind="hash" reveal={reveal} /> : '—'}
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  disabled={!evidence}
                  onClick={() => {
                    if (!evidence) return
                    downloadText(`evidence_${evidence.orderId}.txt`, evidence.contentHint)
                  }}
                  className="inline-flex items-center gap-2 px-3 py-2 rounded-xl bg-zinc-900 text-white font-black hover:bg-zinc-800 disabled:opacity-60"
                >
                  <Download size={16} />
                  下载匹配文件（用于“通过”截图）
                </button>
                <p className="text-xs font-semibold text-zinc-500">下载后再选择该文件，可稳定得到“校验通过”。</p>
              </div>
            </div>

            {order ? (
              <div className="mt-4 rounded-2xl bg-white border border-zinc-100 p-4">
                <p className="text-xs font-black text-zinc-500">订单信息（脱敏展示）</p>
                <div className="mt-2 grid grid-cols-1 sm:grid-cols-2 gap-2 text-sm font-semibold text-zinc-700">
                  <div>
                    路线：<span className="font-black text-zinc-900">{order.fromCity} → {order.toCity}</span>
                  </div>
                  <div>
                    取件地址：<MaskedText value={order.pickupAddress} kind="address" className="text-zinc-900" />
                  </div>
                  <div>
                    手机号：<MaskedText value={order.ownerPhone} kind="phone" className="text-zinc-900" />
                  </div>
                  <div>
                    身份证：<MaskedText value={order.ownerIdCard} kind="idCard" className="text-zinc-900" />
                  </div>
                </div>
              </div>
            ) : null}
          </div>

          <div className="rounded-2xl bg-zinc-50 border border-zinc-100 p-5">
            <h2 className="text-base font-black text-zinc-900">2）选择本地文件并计算 SHA-256</h2>
            <div className="mt-4">
              <input
                type="file"
                onChange={(e) => onPickFile(e.target.files?.[0] ?? null)}
                className="block w-full text-sm font-semibold text-zinc-700 file:mr-4 file:rounded-xl file:border-0 file:bg-orange-500 file:px-4 file:py-2 file:font-black file:text-white hover:file:bg-orange-600"
              />
              <div className="mt-4 rounded-2xl bg-white border border-zinc-100 p-4">
                <p className="text-xs font-black text-zinc-500">已选择文件</p>
                <p className="mt-1 text-sm font-bold text-zinc-900">{fileName || '—'}</p>
              </div>

              <div className="mt-3 rounded-2xl bg-white border border-zinc-100 p-4">
                <p className="text-xs font-black text-zinc-500">计算结果 SHA-256</p>
                <p className="mt-2 text-sm font-black text-zinc-900 break-all">
                  {computing ? '计算中…' : fileHash ? <MaskedText value={fileHash} kind="hash" reveal={reveal} /> : '—'}
                </p>
              </div>
            </div>

            <div className={`mt-4 rounded-2xl p-5 border ${fileHash ? (passed ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200') : 'bg-white border-zinc-100'}`}>
              <div className="flex items-center gap-3">
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${fileHash ? (passed ? 'bg-green-500' : 'bg-red-500') : 'bg-zinc-200'}`}>
                  {fileHash ? (passed ? <FileCheck2 className="text-white w-6 h-6" /> : <FileX2 className="text-white w-6 h-6" />) : <ShieldCheck className="text-white w-6 h-6" />}
                </div>
                <div>
                  <p className="text-xs font-black text-zinc-500">校验结果</p>
                  <p className={`mt-1 text-base font-black ${fileHash ? (passed ? 'text-green-700' : 'text-red-700') : 'text-zinc-700'}`}>
                    {fileHash ? (passed ? '通过（hash 一致）' : '失败（hash 不一致）') : '请先选择文件'}
                  </p>
                </div>
              </div>
              <p className="mt-3 text-xs font-semibold text-zinc-600">
                建议截图两张：一次选择“下载匹配文件”（通过），一次选择任意其他文件（失败）。
              </p>
            </div>
          </div>
        </div>
      </section>

      <section className="mt-6 bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm">
        <h2 className="text-base font-black text-zinc-900">敏感字段清单（最小可用）</h2>
        <p className="mt-2 text-sm font-semibold text-zinc-600">用于论文：说明“链上不存敏感原文，只存 hash 锚定；前端默认脱敏展示”。</p>

        <div className="mt-4 overflow-x-auto">
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs font-black text-zinc-500 border-b border-zinc-100">
                <th className="py-3 pr-4">字段</th>
                <th className="py-3 pr-4 whitespace-nowrap">是否上链</th>
                <th className="py-3 pr-4">链下存什么</th>
                <th className="py-3">前端展示方式</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-100">
              {SENSITIVE_FIELDS.map((r) => (
                <tr key={r.field} className="text-sm font-semibold text-zinc-700">
                  <td className="py-3 pr-4 whitespace-nowrap">{r.field}</td>
                  <td className="py-3 pr-4">
                    <StatusPill tone={r.onChain === '是' ? 'green' : 'zinc'}>{r.onChain}</StatusPill>
                  </td>
                  <td className="py-3 pr-4 min-w-[18rem]">{r.offChainStore}</td>
                  <td className="py-3 min-w-[14rem]">{r.uiDisplay}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </main>
  )
}

