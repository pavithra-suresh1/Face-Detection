import { useEffect } from 'react'
import Navbar from './Navbar'
import { checkHealth } from '../../api/faceApi'

export default function AppLayout({ children }) {
  useEffect(() => {
    checkHealth().catch(() => {})
  }, [])

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main>{children}</main>
    </div>
  )
}
