import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ChevronLeft, MapPin, Phone, MessageSquare, Clock, CheckCircle2, Circle } from 'lucide-react'

interface TrackingStep {
  status: string
  time: string
  location: string
  description: string
  isCompleted: boolean
}

const Tracking: React.FC = () => {
  const { petId } = useParams()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)

  const steps: TrackingStep[] = [
    {
      status: '运输中',
      time: '2026-04-02 10:30',
      location: '北京中转站',
      description: '宠物正在进行健康检查，准备进入下一阶段运输',
      isCompleted: false
    },
    {
      status: '中转中',
      time: '2026-04-02 05:00',
      location: '济南分拣中心',
      description: '宠物已到达济南分拣中心，状态良好',
      isCompleted: true
    },
    {
      status: '已发货',
      time: '2026-04-01 22:00',
      location: '上海分拨中心',
      description: '宠物已离开上海，发往北京方向',
      isCompleted: true
    },
    {
      status: '已揽收',
      time: '2026-04-01 18:00',
      location: '上海徐汇营业部',
      description: '宠物已安全接收，完成初步检查',
      isCompleted: true
    }
  ]

  useEffect(() => {
    setTimeout(() => setLoading(false), 800)
  }, [])

  return (
    <div className="min-h-screen bg-zinc-50 pb-24">
      <header className="bg-white px-4 py-4 shadow-sm flex items-center gap-3 sticky top-0 z-20">
        <button onClick={() => navigate(-1)} className="p-2 hover:bg-zinc-100 rounded-full transition-colors">
          <ChevronLeft size={24} className="text-zinc-900" />
        </button>
        <div>
          <h1 className="text-lg font-bold text-zinc-900">运单详情</h1>
          <p className="text-zinc-400 text-xs font-mono">NO. PET2026040201</p>
        </div>
      </header>

      <main className="max-w-2xl mx-auto">
        {/* 模拟地图区域 */}
        <div className="w-full h-64 bg-zinc-200 relative overflow-hidden">
          <img 
            src="https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=simple+minimalist+map+showing+a+route+from+shanghai+to+beijing+with+a+pet+icon&image_size=landscape_16_9" 
            alt="Tracking Map"
            className="w-full h-full object-cover opacity-80"
          />
          <div className="absolute inset-0 flex items-center justify-center">
            <div className="relative">
              <div className="absolute -inset-4 bg-orange-500/20 rounded-full animate-ping"></div>
              <div className="bg-orange-500 p-2 rounded-full shadow-lg relative z-10">
                <MapPin className="text-white w-6 h-6" />
              </div>
            </div>
          </div>
          <div className="absolute bottom-4 left-4 right-4 bg-white/90 backdrop-blur-sm p-3 rounded-xl shadow-lg flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-orange-100 flex items-center justify-center">
              <Clock className="text-orange-600 w-5 h-5" />
            </div>
            <div>
              <p className="text-xs text-zinc-500">预计到达时间</p>
              <p className="text-sm font-bold text-zinc-900">2026-04-03 15:00</p>
            </div>
          </div>
        </div>

        {/* 宠物简要信息卡片 */}
        <div className="mx-4 -mt-6 relative z-10 bg-white rounded-2xl p-4 shadow-xl border border-zinc-100 flex items-center gap-4">
          <div className="w-16 h-16 rounded-xl overflow-hidden bg-zinc-100">
            <img 
              src="https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=cute+white+cat+profile&image_size=square" 
              alt="Pet"
              className="w-full h-full object-cover"
            />
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h2 className="text-lg font-bold text-zinc-900">小白</h2>
              <span className="bg-orange-100 text-orange-600 px-2 py-0.5 rounded text-[10px] font-bold">运输中</span>
            </div>
            <p className="text-zinc-500 text-sm">英短 · 2岁 · 4.5kg</p>
          </div>
          <div className="flex gap-2">
            <button className="p-3 bg-zinc-50 rounded-full text-zinc-600 hover:bg-zinc-100 transition-colors">
              <Phone size={20} />
            </button>
            <button className="p-3 bg-zinc-50 rounded-full text-zinc-600 hover:bg-zinc-100 transition-colors">
              <MessageSquare size={20} />
            </button>
          </div>
        </div>

        {/* 状态时间轴 */}
        <div className="m-4 bg-white rounded-2xl p-6 shadow-md border border-zinc-100">
          <h3 className="text-base font-bold text-zinc-900 mb-6">运输状态</h3>
          <div className="space-y-8">
            {steps.map((step, index) => (
              <div key={index} className="relative flex gap-4">
                {/* 连线 */}
                {index !== steps.length - 1 && (
                  <div className="absolute left-3 top-7 bottom-[-20px] w-0.5 bg-zinc-100"></div>
                )}
                
                {/* 节点图标 */}
                <div className="relative z-10">
                  {index === 0 ? (
                    <div className="w-6 h-6 bg-orange-500 rounded-full flex items-center justify-center ring-4 ring-orange-100">
                      <div className="w-2 h-2 bg-white rounded-full"></div>
                    </div>
                  ) : (
                    <div className="w-6 h-6 bg-white border-2 border-zinc-200 rounded-full flex items-center justify-center">
                      <CheckCircle2 className="w-4 h-4 text-zinc-300" />
                    </div>
                  )}
                </div>

                {/* 内容 */}
                <div className="flex-1">
                  <div className="flex items-center justify-between mb-1">
                    <h4 className={`text-sm font-bold ${index === 0 ? 'text-orange-600' : 'text-zinc-900'}`}>
                      {step.status}
                    </h4>
                    <span className="text-xs text-zinc-400">{step.time}</span>
                  </div>
                  <p className="text-sm font-medium text-zinc-600 mb-1">{step.location}</p>
                  <p className="text-xs text-zinc-400 leading-relaxed">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 客服热线 */}
        <div className="m-4 text-center">
          <p className="text-xs text-zinc-400">如有疑问，请拨打客服热线</p>
          <p className="text-sm font-bold text-orange-500 mt-1">400-123-4567</p>
        </div>
      </main>
    </div>
  )
}

export default Tracking
