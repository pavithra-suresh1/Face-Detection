import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getStats } from '../api/faceApi'
import Loading from '../components/common/Loading'

const quickActions = [
  { label: 'Upload Image', desc: 'Analyze stored photos and detect faces instantly', to: '/upload', icon: '📷', color: 'bg-blue-50 border-blue-200' },
  { label: 'Register Face', desc: 'Enroll known people for accurate recognition', to: '/known-faces', icon: '👤', color: 'bg-purple-50 border-purple-200' },
  { label: 'Live Detection', desc: 'Monitor the camera stream in real time', to: '/realtime', icon: '🎥', color: 'bg-green-50 border-green-200' },
  { label: 'Reports', desc: 'Review recognition activity and analytics', to: '/reports', icon: '📊', color: 'bg-orange-50 border-orange-200' },
]

export default function Dashboard() {
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getStats().then((res) => setStats(res.data)).finally(() => setLoading(false))
  }, [])

  if (loading) return <Loading message="Loading dashboard..." />

  const recent = stats?.recent_activity || []

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Face Detection Intelligence</h1>
        <p className="text-gray-500">Monitor detections, manage known faces, and review recognition results from one place.</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Images" value={stats?.total_images || 0} sub="Uploaded" color="from-blue-500 to-blue-600" to="/upload" />
        <StatCard label="Faces" value={stats?.total_faces || 0} sub="Detected" color="from-indigo-500 to-indigo-600" to="/history" />
        <StatCard label="Known" value={stats?.known_faces || 0} sub="Registered" color="from-purple-500 to-purple-600" to="/known-faces" />
        <StatCard label="Recognitions" value={stats?.total_recognitions || 0} sub="Total" color="from-cyan-500 to-cyan-600" to="/reports" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <MiniStat label="Known Matches" value={stats?.known_matches || 0} color="text-green-600" to="/reports" />
        <MiniStat label="Unknown" value={stats?.unknown_matches || 0} color="text-orange-600" to="/reports" />
        <MiniStat label="Today Detections" value={stats?.today_detections || 0} color="text-blue-600" to="/history" />
        <MiniStat label="Today Recognitions" value={stats?.today_recognitions || 0} color="text-indigo-600" to="/reports" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
        {quickActions.map((a) => (
          <Link key={a.label} to={a.to}
            className={`${a.color} border rounded-xl p-5 hover:shadow-md transition`}>
            <span className="text-2xl mb-2 block">{a.icon}</span>
            <h3 className="font-semibold text-gray-900">{a.label}</h3>
            <p className="text-sm text-gray-500">{a.desc}</p>
          </Link>
        ))}
      </div>

      {recent.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Recent Activity</h3>
          <div className="space-y-3">
            {recent.map((r) => (
              <Link key={r.id} to="/reports"
                className="flex items-center justify-between py-2 border-b border-gray-100 last:border-0 hover:bg-gray-50 px-2 rounded transition">
                <div className="flex items-center gap-3">
                  <span className={`w-2 h-2 rounded-full ${r.type === 'known' ? 'bg-green-500' : 'bg-yellow-500'}`}></span>
                  <span className="text-sm text-gray-800">{r.name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs text-gray-400">{new Date(r.time).toLocaleTimeString()}</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function StatCard({ label, value, sub, color, to }) {
  return (
    <Link to={to}
      className={`bg-gradient-to-br ${color} rounded-xl p-5 text-white shadow-sm hover:opacity-90 transition block`}>
      <p className="text-3xl font-bold">{value}</p>
      <p className="text-sm opacity-90">{label}</p>
      <p className="text-xs opacity-70">{sub}</p>
    </Link>
  )
}

function MiniStat({ label, value, color, to }) {
  return (
    <Link to={to}
      className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center hover:shadow-md transition block">
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      <p className="text-xs text-gray-500">{label}</p>
    </Link>
  )
}
