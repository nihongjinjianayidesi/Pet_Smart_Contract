import { Link } from 'react-router-dom'

export default function Home() {
  return (
    <main className="max-w-5xl mx-auto px-4 py-8">
      <section className="bg-gradient-to-br from-orange-500 to-amber-500 rounded-3xl p-8 text-white shadow-xl">
        <h1 className="text-3xl sm:text-4xl font-black tracking-tight">PetSC 宠物托运系统</h1>
        <p className="mt-2 text-white/90 font-semibold">面向宠物托运业务的订单创建、运输跟踪与状态展示（前端基线页）</p>
        <div className="mt-6 flex flex-wrap gap-3">
          <Link
            to="/quote"
            className="bg-white text-zinc-900 px-4 py-2 rounded-xl font-black hover:bg-zinc-50 transition-colors"
          >
            开始报价下单
          </Link>
          <Link
            to="/orders"
            className="bg-white/20 px-4 py-2 rounded-xl font-black hover:bg-white/25 transition-colors"
          >
            查看我的订单
          </Link>
          <Link
            to="/evidence"
            className="bg-white/20 px-4 py-2 rounded-xl font-black hover:bg-white/25 transition-colors"
          >
            证据校验演示
          </Link>
        </div>
      </section>

      <section className="mt-8 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white rounded-2xl p-5 border border-zinc-100 shadow-sm">
          <p className="text-xs font-bold text-zinc-400">今日在途</p>
          <p className="mt-1 text-2xl font-black text-zinc-900">1</p>
          <p className="mt-1 text-sm font-semibold text-zinc-600">展示“运输中”订单的状态与节点</p>
        </div>
        <div className="bg-white rounded-2xl p-5 border border-zinc-100 shadow-sm">
          <p className="text-xs font-bold text-zinc-400">今日送达</p>
          <p className="mt-1 text-2xl font-black text-zinc-900">1</p>
          <p className="mt-1 text-sm font-semibold text-zinc-600">展示“已送达”订单的完成状态</p>
        </div>
        <div className="bg-white rounded-2xl p-5 border border-zinc-100 shadow-sm">
          <p className="text-xs font-bold text-zinc-400">数据来源</p>
          <p className="mt-1 text-2xl font-black text-zinc-900">Mock</p>
          <p className="mt-1 text-sm font-semibold text-zinc-600">后端未联通时用本地模拟数据跑通页面</p>
        </div>
      </section>

      <section className="mt-8 bg-white rounded-2xl p-6 border border-zinc-100 shadow-sm">
        <h2 className="text-lg font-black text-zinc-900">截图建议</h2>
        <div className="mt-3 space-y-2 text-sm font-semibold text-zinc-700">
          <p>推荐打开“首页”或“宠物列表”页截图：顶部能看到系统名称与导航栏。</p>
          <p>如需展示流程：从“宠物列表”点进“运单跟踪”页再截图时间轴。</p>
        </div>
      </section>
    </main>
  )
}
