import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { supabase } from './lib/supabase'
import { useAuthStore } from './store/auth'
import AppShell from './components/AppShell'
import Home from './pages/Home'
import Login from './pages/Login'
import Pets from './pages/Pets'
import Tracking from './pages/Tracking'
import Quote from './pages/Quote'
import Orders from './pages/Orders'
import Fulfillment from './pages/Fulfillment'
import Exceptions from './pages/Exceptions'
import EvidenceVerify from './pages/EvidenceVerify'

function App() {
  const { setUser, loading } = useAuthStore()

  useEffect(() => {
    // 检查当前会话
    supabase.auth.getSession().then(({ data: { session } }) => {
      setUser(session?.user ?? null)
    })

    // 监听认证状态变化
    const { data: { subscription } } = supabase.auth.onAuthStateChange((_event, session) => {
      setUser(session?.user ?? null)
    })

    return () => subscription.unsubscribe()
  }, [setUser])

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-zinc-50">
        <div className="w-10 h-10 border-4 border-orange-500 border-t-transparent rounded-full animate-spin"></div>
      </div>
    )
  }

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route element={<AppShell />}>
          <Route path="/" element={<Home />} />
          <Route path="/quote" element={<Quote />} />
          <Route path="/orders" element={<Orders />} />
          <Route path="/fulfillment" element={<Fulfillment />} />
          <Route path="/fulfillment/:orderId" element={<Fulfillment />} />
          <Route path="/exceptions" element={<Exceptions />} />
          <Route path="/evidence" element={<EvidenceVerify />} />
          <Route path="/pets" element={<Pets />} />
          <Route path="/tracking/:petId" element={<Tracking />} />
        </Route>
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
