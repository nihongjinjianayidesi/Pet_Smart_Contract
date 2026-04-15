import clsx from 'clsx'
import { Home, LogIn, ClipboardList, BadgeDollarSign, MapPinned, TriangleAlert, FileCheck2 } from 'lucide-react'
import { NavLink } from 'react-router-dom'

const navItems = [
  { to: '/', label: '首页', Icon: Home, end: true },
  { to: '/quote', label: '托运报价', Icon: BadgeDollarSign, end: false },
  { to: '/orders', label: '我的订单', Icon: ClipboardList, end: false },
  { to: '/fulfillment', label: '履约追踪', Icon: MapPinned, end: false },
  { to: '/exceptions', label: '异常处理', Icon: TriangleAlert, end: false },
  { to: '/evidence', label: '证据校验', Icon: FileCheck2, end: false },
  { to: '/login', label: '登录', Icon: LogIn, end: false }
] as const

export default function TopNav() {
  return (
    <header className="sticky top-0 z-30 bg-white/90 backdrop-blur border-b border-zinc-100">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-4">
        <NavLink to="/" className="font-black text-zinc-900 tracking-tight">
          PetSC 宠物托运系统
        </NavLink>
        <nav className="ml-auto flex items-center gap-2 overflow-x-auto no-scrollbar">
          {navItems.map(({ to, label, Icon, end }) => (
            <NavLink
              key={to}
              to={to}
              end={end}
              className={({ isActive }) =>
                clsx(
                  'flex items-center gap-2 px-3 py-2 rounded-xl text-sm font-bold transition-colors whitespace-nowrap',
                  isActive ? 'bg-orange-500 text-white' : 'text-zinc-600 hover:bg-zinc-100'
                )
              }
            >
              <Icon size={16} />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
    </header>
  )
}
