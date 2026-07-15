import { useState, useEffect } from 'react'
import { getStats, getHistory } from '../api/faceApi'
import { listImages } from '../api/uploadApi'
import Loading from '../components/common/Loading'

const FILTERS = {
  total_images: { label: 'Total Images', api: 'images' },
  total_faces: { label: 'Faces Detected', api: 'history' },
  known_faces: { label: 'Registered People', api: 'known-faces' },
  known_matches: { label: 'Known Matches', api: 'history', knownOnly: true },
  unknown_matches: { label: 'Unknown', api: 'history', unknownOnly: true },
  today_detections: { label: "Today's Detections", api: 'history', today: true },
  known_pct: { label: 'Known Rate', api: 'history', knownOnly: true },
  unknown_pct: { label: 'Unknown Rate', api: 'history', unknownOnly: true },
}

export default function Report() {
  const [stats, setStats] = useState(null)
  const [recent, setRecent] = useState([])
  const [loading, setLoading] = useState(true)
  const [detail, setDetail] = useState(null)
  const [detailData, setDetailData] = useState([])
  const [detailLoading, setDetailLoading] = useState(false)

  useEffect(() => {
    Promise.all([getStats(), getHistory(1)])
      .then(([s, h]) => {
        setStats(s.data)
        setRecent(h.data || [])
      })
      .finally(() => setLoading(false))
  }, [])

  const loadDetail = async (filter) => {
    setDetail(filter)
    setDetailLoading(true)
    setDetailData([])
    try {
      if (filter.api === 'history') {
        const res = await getHistory(1)
        let data = res.data || []
        if (filter.knownOnly) data = data.filter((l) => l.is_known)
        if (filter.unknownOnly) data = data.filter((l) => !l.is_known)
        if (filter.today) {
          const today = new Date().toDateString()
          data = data.filter((l) => new Date(l.processed_at).toDateString() === today)
        }
        setDetailData(data)
      } else if (filter.api === 'images') {
        const res = await listImages(1)
        setDetailData(res.data || [])
      } else if (filter.api === 'known-faces') {
        const { listKnownFaces } = await import('../api/faceApi')
        const res = await listKnownFaces()
        setDetailData(res.data || [])
      }
    } catch {} finally {
      setDetailLoading(false)
    }
  }

  if (loading) return <Loading message="Loading reports..." />

  const summaryCards = [
    { key: 'total_images', label: 'Total Images', value: stats?.total_images || 0, color: 'from-blue-500 to-blue-600', filter: FILTERS.total_images },
    { key: 'total_faces', label: 'Faces Detected', value: stats?.total_faces || 0, color: 'from-indigo-500 to-indigo-600', filter: FILTERS.total_faces },
    { key: 'known_faces', label: 'Registered People', value: stats?.known_faces || 0, color: 'from-purple-500 to-purple-600', filter: FILTERS.known_faces },
    { key: 'known_matches', label: 'Known Matches', value: stats?.known_matches || 0, color: 'from-green-500 to-green-600', filter: FILTERS.known_matches },
    { key: 'unknown_matches', label: 'Unknown', value: stats?.unknown_matches || 0, color: 'from-orange-500 to-orange-600', filter: FILTERS.unknown_matches },
    { key: 'today_detections', label: "Today's Detections", value: stats?.today_detections || 0, color: 'from-cyan-500 to-cyan-600', filter: FILTERS.today_detections },
  ]

  const knownPct = stats?.total_recognitions > 0
    ? ((stats.known_matches / stats.total_recognitions) * 100).toFixed(1)
    : '0.0'
  const unknownPct = stats?.total_recognitions > 0
    ? ((stats.unknown_matches / stats.total_recognitions) * 100).toFixed(1)
    : '0.0'

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Reports & Analytics</h1>
        <p className="text-gray-500">Face recognition performance overview</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-8">
        {summaryCards.map((card) => (
          <button key={card.key} onClick={() => loadDetail(card.filter)}
            className={`bg-white rounded-xl shadow-sm border border-gray-200 p-4 text-center hover:shadow-md hover:border-primary-300 transition text-left w-full ${
              detail?.label === card.label ? 'ring-2 ring-primary-500 border-primary-500' : ''
            }`}>
            <p className="text-2xl font-bold text-gray-900">{card.value}</p>
            <p className="text-xs text-gray-500 mt-1">{card.label}</p>
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Recognition Rate</h3>
          {stats?.total_recognitions > 0 ? (
            <div className="space-y-4">
              <button onClick={() => loadDetail(FILTERS.known_pct)}
                className={`w-full text-left p-2 rounded-lg hover:bg-gray-50 transition ${
                  detail?.label === 'Known Rate' ? 'bg-green-50 ring-2 ring-green-500' : ''
                }`}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-green-600 font-medium">Known ({knownPct}%)</span>
                  <span className="text-gray-500">{stats.known_matches} faces</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div className="bg-green-500 h-3 rounded-full" style={{ width: `${knownPct}%` }}></div>
                </div>
              </button>
              <button onClick={() => loadDetail(FILTERS.unknown_pct)}
                className={`w-full text-left p-2 rounded-lg hover:bg-gray-50 transition ${
                  detail?.label === 'Unknown Rate' ? 'bg-orange-50 ring-2 ring-orange-500' : ''
                }`}>
                <div className="flex justify-between text-sm mb-1">
                  <span className="text-orange-600 font-medium">Unknown ({unknownPct}%)</span>
                  <span className="text-gray-500">{stats.unknown_matches} faces</span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-3">
                  <div className="bg-orange-400 h-3 rounded-full" style={{ width: `${unknownPct}%` }}></div>
                </div>
              </button>
            </div>
          ) : (
            <p className="text-gray-400 text-sm text-center py-8">No recognition data yet. Upload images and register faces to see statistics.</p>
          )}
        </div>

        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Recent Recognitions</h3>
          {recent.length > 0 ? (
            <div className="space-y-3">
              {recent.slice(0, 6).map((log) => (
                <button key={log.id} onClick={() => {
                  setDetail({ label: log.matched_name || 'Unknown', api: 'history' })
                  setDetailData([log])
                }}
                  className={`w-full flex items-center justify-between py-2 border-b border-gray-100 last:border-0 hover:bg-gray-50 px-2 rounded transition text-left ${
                    detail?.label === (log.matched_name || 'Unknown') ? 'bg-gray-50 ring-2 ring-primary-500' : ''
                  }`}>
                  <div className="flex items-center gap-2">
                    <span className={`w-2 h-2 rounded-full ${log.is_known ? 'bg-green-500' : 'bg-yellow-500'}`}></span>
                    <span className="text-sm font-medium text-gray-800">{log.matched_name || 'Unknown'}</span>
                  </div>
                  <span className="text-xs text-gray-400">{new Date(log.processed_at).toLocaleTimeString()}</span>
                </button>
              ))}
            </div>
          ) : (
            <p className="text-gray-400 text-sm text-center py-8">No recognitions yet.</p>
          )}
        </div>
      </div>

      {detail && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900 text-lg">{detail.label}</h3>
            <button onClick={() => setDetail(null)}
              className="text-sm text-gray-500 hover:text-gray-700 font-medium">Clear</button>
          </div>
          {detailLoading ? (
            <Loading message="Loading details..." />
          ) : detailData.length === 0 ? (
            <p className="text-gray-400 text-sm text-center py-8">No data found.</p>
          ) : detail.api === 'images' ? (
            <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {detailData.map((img) => (
                <div key={img.id} className="border rounded-lg overflow-hidden">
                  <img src={`http://localhost:8000${img.image}`} alt=""
                    className="w-full h-24 object-cover" />
                  <p className="text-xs text-gray-500 p-2 truncate">{img.filename || img.id?.slice(0, 8)}</p>
                </div>
              ))}
            </div>
          ) : detail.api === 'known-faces' ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
              {detailData.map((face) => (
                <div key={face.id} className="border rounded-lg p-3 flex items-center gap-3">
                  {face.face_images?.[0] && (
                    <img src={`http://localhost:8000${face.face_images[0].image}`} alt=""
                      className="w-12 h-12 rounded-full object-cover" />
                  )}
                  <div>
                    <p className="text-sm font-medium text-gray-900">{face.name}</p>
                    {face.email && <p className="text-xs text-gray-500">{face.email}</p>}
                    <p className="text-xs text-gray-400">{face.image_count} image{face.image_count !== 1 ? 's' : ''}</p>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Status</th>
                    <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Name</th>
                    <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Confidence</th>
                    <th className="text-left px-4 py-2 text-xs font-medium text-gray-500 uppercase">Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {detailData.map((log) => (
                    <tr key={log.id} className="hover:bg-gray-50">
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${
                          log.is_known ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                        }`}>
                          {log.is_known ? 'Known' : 'Unknown'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-900">{log.matched_name || '—'}</td>
                      <td className="px-4 py-3 text-sm text-gray-500">
                        {log.confidence != null ? `${log.confidence.toFixed(1)}%` : '—'}
                      </td>
                      <td className="px-4 py-3 text-sm text-gray-500 whitespace-nowrap">
                        {new Date(log.processed_at).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
