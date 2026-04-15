export type MaskKind = 'idCard' | 'phone' | 'address' | 'certificate' | 'hash'

function repeat(ch: string, count: number) {
  if (count <= 0) return ''
  return Array.from({ length: count }).fill(ch).join('')
}

export function truncateMiddle(value: string, head: number, tail: number, maskChar = '*') {
  const v = String(value ?? '')
  if (!v) return ''
  if (v.length <= head + tail) return v
  return `${v.slice(0, head)}${repeat(maskChar, Math.min(12, v.length - head - tail))}${v.slice(-tail)}`
}

export function maskValue(value: string, kind: MaskKind) {
  const v = String(value ?? '')
  if (!v) return ''

  if (kind === 'phone') return truncateMiddle(v, 3, 4)
  if (kind === 'idCard') return truncateMiddle(v, 6, 4)
  if (kind === 'certificate') return truncateMiddle(v, 4, 4)
  if (kind === 'hash') {
    if (v.length <= 12) return v
    return `${v.slice(0, 6)}…${v.slice(-6)}`
  }
  if (kind === 'address') {
    if (v.length <= 6) return `${v.slice(0, 1)}***`
    return `${v.slice(0, 6)}…`
  }

  return v
}

export interface SensitiveFieldRow {
  field: string
  onChain: '是' | '否'
  offChainStore: string
  uiDisplay: string
}

export const SENSITIVE_FIELDS: SensitiveFieldRow[] = [
  { field: 'owner_name（托运人姓名）', onChain: '否', offChainStore: '订单基本信息（链下 DB / JSON）', uiDisplay: '姓名全显或仅首字（可选）' },
  { field: 'owner_id_card（身份证号）', onChain: '否', offChainStore: '原文或加密存储；链上仅锚定 hash', uiDisplay: '脱敏：前6后4' },
  { field: 'owner_phone（手机号）', onChain: '否', offChainStore: '原文或加密存储；链上仅锚定 hash', uiDisplay: '脱敏：前3后4' },
  { field: 'pickup_address（取件地址）', onChain: '否', offChainStore: '原文地址；链上仅锚定 hash', uiDisplay: '脱敏：保留前6字符' },
  { field: 'health_cert_no（检疫/健康证书号）', onChain: '否', offChainStore: '证书号原文；链上仅锚定 hash', uiDisplay: '脱敏：前4后4' },
  { field: 'handover_doc（交接单文件）', onChain: '否', offChainStore: '文件本体存链下；链上记录文件 hash（锚定）', uiDisplay: '展示 hash：前6后6' },
  { field: 'pet_photo（宠物照片）', onChain: '否', offChainStore: '图片文件链下存储；链上记录 hash', uiDisplay: '展示缩略图或 hash（演示用）' },
  { field: 'order_public_meta（订单公开元数据）', onChain: '是', offChainStore: '链下缓存一份用于查询', uiDisplay: '可全显（不含个人敏感字段）' }
]
