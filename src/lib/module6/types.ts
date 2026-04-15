export type PetType = '猫' | '狗'

export type OrderStatus = '已报价' | '已下单' | '运输中' | '异常处理中' | '已完成'

export interface PriceBreakdown {
  base: number
  distanceKm: number
  weightKg: number
  insurance: number
  total: number
}

export interface Order {
  id: string
  createdAt: string
  fromCity: string
  toCity: string
  petName: string
  petType: PetType
  weightKg: number
  ownerName: string
  ownerPhone: string
  ownerIdCard: string
  pickupAddress: string
  status: OrderStatus
  price: PriceBreakdown
}

export type FulfillmentStage =
  | '待揽收'
  | '已揽收'
  | '已发货'
  | '中转中'
  | '运输中'
  | '已送达'

export interface FulfillmentStep {
  stage: FulfillmentStage
  time: string
  location: string
  description: string
  completed: boolean
}

export type ExceptionStatus = '已上报' | '处理中' | '已解决' | '已赔付'

export interface ExceptionCase {
  id: string
  orderId: string
  type: '延误' | '健康异常' | '破损' | '丢失' | '争议'
  status: ExceptionStatus
  createdAt: string
  summary: string
  evidenceRecordId?: string
}

export interface EvidenceRecord {
  id: string
  orderId: string
  docType: '交接单' | '健康证明' | '照片' | '异常凭证'
  createdAt: string
  onChainHash: string
  offChainHash: string
  contentHint: string
}

