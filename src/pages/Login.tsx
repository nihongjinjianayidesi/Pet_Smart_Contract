import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { supabase } from '../lib/supabase'
import { useAuthStore } from '../store/auth'
import { Dog, Loader2 } from 'lucide-react'

const Login: React.FC = () => {
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()
  const setUser = useAuthStore((state) => state.setUser)

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError(null)

    try {
      // 在实际项目中，这里应该调用 supabase.auth.signInWithOtp
      // 为了演示，我们这里简化逻辑
      // 注意：Supabase 的手机登录通常需要配置短信服务
      
      // 模拟登录：如果手机号不为空，则认为登录成功
      if (phone.length >= 11) {
        // 实际上这里应该验证验证码
        const { data, error: authError } = await supabase.auth.signInWithOtp({
          phone: phone,
        })
        
        if (authError) throw authError
        alert('验证码已发送（请在 Supabase 控制台查看或配置短信服务）')
      } else {
        setError('请输入正确的手机号')
      }
    } catch (err: any) {
      setError(err.message || '登录失败，请重试')
    } finally {
      setLoading(false)
    }
  }

  // 临时：点击直接进入（仅供开发调试）
  const devLogin = () => {
    navigate('/pets')
  }

  return (
    <div className="min-h-screen bg-zinc-50 flex items-center justify-center p-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8">
        <div className="flex flex-col items-center mb-8">
          <div className="w-16 h-16 bg-orange-100 rounded-full flex items-center justify-center mb-4">
            <Dog className="w-10 h-10 text-orange-500" />
          </div>
          <h1 className="text-2xl font-bold text-zinc-900">宠物托运跟踪</h1>
          <p className="text-zinc-500 mt-2">随时随地，了解宝贝动态</p>
        </div>

        <form onSubmit={handleLogin} className="space-y-6">
          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-2">
              手机号
            </label>
            <input
              type="tel"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
              placeholder="请输入手机号"
              className="w-full px-4 py-3 rounded-xl border border-zinc-200 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none transition-all"
              required
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-zinc-700 mb-2">
              验证码
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                placeholder="请输入验证码"
                className="flex-1 px-4 py-3 rounded-xl border border-zinc-200 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none transition-all"
              />
              <button
                type="button"
                className="px-4 py-2 text-sm font-medium text-orange-600 hover:text-orange-700 transition-colors"
              >
                获取验证码
              </button>
            </div>
          </div>

          {error && (
            <p className="text-red-500 text-sm bg-red-50 p-3 rounded-lg">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-orange-500 hover:bg-orange-600 text-white font-bold py-3 rounded-xl shadow-lg shadow-orange-200 transition-all flex items-center justify-center disabled:opacity-70"
          >
            {loading ? <Loader2 className="animate-spin mr-2" /> : '登录'}
          </button>
        </form>

        <div className="mt-8 pt-6 border-t border-zinc-100 text-center">
          <button 
            onClick={devLogin}
            className="text-zinc-400 text-sm hover:text-zinc-600"
          >
            开发环境：跳过登录直接查看
          </button>
        </div>
      </div>
    </div>
  )
}

export default Login
