import { Outlet } from 'react-router-dom'
import TopNav from './TopNav'
import { useEffect } from 'react'
import { ensureSeedData } from '../lib/module6/storage'

export default function AppShell() {
  useEffect(() => {
    ensureSeedData()
  }, [])

  return (
    <div className="min-h-screen bg-zinc-50">
      <TopNav />
      <Outlet />
    </div>
  )
}
