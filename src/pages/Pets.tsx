import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Dog, Cat, MapPin, ChevronRight, LogOut, Search, Filter } from 'lucide-react'
import { useAuthStore } from '../store/auth'

interface PetCardProps {
  id: string
  name: string
  type: 'dog' | 'cat'
  status: string
  lastUpdate: string
  location: string
  imageUrl: string
}

const PetCard: React.FC<PetCardProps> = ({ id, name, type, status, lastUpdate, location, imageUrl }) => {
  const navigate = useNavigate()
  
  return (
    <div 
      onClick={() => navigate(`/tracking/${id}`)}
      className="bg-white rounded-2xl p-4 mb-4 shadow-sm border border-zinc-100 active:scale-[0.98] transition-all cursor-pointer hover:shadow-md"
    >
      <div className="flex gap-4">
        <div className="w-20 h-20 rounded-xl overflow-hidden bg-zinc-100 flex-shrink-0">
          <img src={imageUrl} alt={name} className="w-full h-full object-cover" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-lg font-bold text-zinc-900 truncate">{name}</h3>
            <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${
              status === '运输中' ? 'bg-orange-100 text-orange-600' : 'bg-green-100 text-green-600'
            }`}>
              {status}
            </span>
          </div>
          <div className="flex items-center gap-1 text-zinc-500 text-xs mb-2">
            <MapPin size={12} />
            <span className="truncate">{location}</span>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-zinc-400 text-[10px]">{lastUpdate} 更新</span>
            <div className="flex items-center text-orange-500 font-bold text-xs">
              查看详情 <ChevronRight size={14} />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

const Pets: React.FC = () => {
  const [filter, setFilter] = useState('全部')
  const { signOut } = useAuthStore()
  const navigate = useNavigate()

  // 模拟数据
  const mockPets: PetCardProps[] = [
    {
      id: '1',
      name: '小白',
      type: 'cat',
      status: '运输中',
      lastUpdate: '10分钟前',
      location: '北京中转站',
      imageUrl: 'https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=cute+white+cat+profile&image_size=square'
    },
    {
      id: '2',
      name: '大黄',
      type: 'dog',
      status: '已送达',
      lastUpdate: '2小时前',
      location: '上海徐汇区',
      imageUrl: 'https://coresg-normal.trae.ai/api/ide/v1/text_to_image?prompt=friendly+golden+retriever+dog+profile&image_size=square'
    }
  ]

  const handleLogout = async () => {
    await signOut()
    navigate('/login')
  }

  return (
    <div className="min-h-screen bg-zinc-50 pb-20">
      {/* 顶部导航 */}
      <header className="bg-white px-6 py-6 rounded-b-[2rem] shadow-sm mb-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-zinc-900">我的宠物</h1>
            <p className="text-zinc-400 text-sm">共有 2 只宠物正在托运</p>
          </div>
          <button 
            onClick={handleLogout}
            className="p-2 bg-zinc-50 rounded-full text-zinc-400 hover:text-red-500 transition-colors"
          >
            <LogOut size={20} />
          </button>
        </div>

        {/* 搜索和筛选 */}
        <div className="flex gap-3">
          <div className="flex-1 bg-zinc-50 rounded-xl px-4 py-2 flex items-center gap-2 border border-zinc-100">
            <Search size={18} className="text-zinc-400" />
            <input 
              type="text" 
              placeholder="搜索宠物名" 
              className="bg-transparent border-none outline-none text-sm w-full"
            />
          </div>
          <button className="p-2 bg-orange-500 rounded-xl text-white">
            <Filter size={20} />
          </button>
        </div>
      </header>

      {/* 状态筛选标签 */}
      <div className="px-6 mb-6 flex gap-4 overflow-x-auto no-scrollbar">
        {['全部', '运输中', '已送达', '待揽收'].map((tab) => (
          <button
            key={tab}
            onClick={() => setFilter(tab)}
            className={`whitespace-nowrap px-4 py-2 rounded-full text-sm font-medium transition-all ${
              filter === tab 
                ? 'bg-orange-500 text-white shadow-lg shadow-orange-200' 
                : 'bg-white text-zinc-500 border border-zinc-100'
            }`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* 列表内容 */}
      <div className="px-6">
        {mockPets
          .filter(p => filter === '全部' || p.status === filter)
          .map(pet => (
            <PetCard key={pet.id} {...pet} />
          ))
        }
      </div>

      {/* 底部悬浮按钮 */}
      <div className="fixed bottom-6 left-1/2 -translate-x-1/2 bg-zinc-900 text-white px-6 py-3 rounded-full shadow-2xl flex items-center gap-2 active:scale-95 transition-all">
        <div className="w-6 h-6 bg-orange-500 rounded-full flex items-center justify-center">
          <span className="text-lg font-bold leading-none">+</span>
        </div>
        <span className="text-sm font-bold">新增托运订单</span>
      </div>
    </div>
  )
}

export default Pets
