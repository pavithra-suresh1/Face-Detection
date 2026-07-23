import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { getHistory, updateRecognitionLog, deleteRecognitionLog } from '../api/faceApi'
import Loading from '../components/common/Loading'

export default function History() {
  const [logs, setLogs] = useState([])
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [editId, setEditId] = useState(null)
  const [editIsKnown, setEditIsKnown] = useState(false)

  const loadHistory = async (p) => {
    setLoading(true)
    try {
      const res = await getHistory(p)
      setLogs(res.data)
      setTotalPages(res.pages)
      setPage(res.page)
    } catch {} finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadHistory(page) }, [page])

  const filtered = filter === 'all' ? logs : logs.filter((l) => filter === 'known' ? l.is_known : !l.is_known)

  const startEdit = (log) => {
    setEditId(log.id)
    setEditIsKnown(log.is_known)
  }

  const cancelEdit = () => {
    setEditId(null)
  }

  const saveEdit = async (id) => {
    try {
      await updateRecognitionLog(id, {
        is_known: editIsKnown,
      })
      setEditId(null)
      loadHistory(page)
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to update.')
    }
  }

  const handleDelete = async (log) => {
    if (!confirm(`Delete recognition log for "${log.matched_name || 'Unknown'}"?`)) return
    try {
      await deleteRecognitionLog(log.id)
      loadHistory(page)
    } catch {}
  }

  const getMappedPage = (p) => {
    const filtered = filter === 'all' ? logs : logs.filter((l) => filter === 'known' ? l.is_known : !l.is_known)
    return filtered.length > 0 ? p : Math.max(1, p - 1)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Recognition History</h1>
          <p className="text-gray-500">Past face recognition results</p>
        </div>
        <div className="flex gap-2">
          {['all', 'known', 'unknown'].map((f) => (
            <button key={f} onClick={() => { setFilter(f); setPage(1) }}
              className={`px-4 py-1.5 rounded-lg text-sm font-medium transition ${
                filter === f ? 'bg-primary-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}>
              {f.charAt(0).toUpperCase() + f.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading ? <Loading message="Loading history..." /> : (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
          {filtered.length === 0 ? (
            <div className="text-center py-16 text-gray-500">
              <p className="text-lg mb-1">No results found</p>
              <p className="text-sm">Upload images to see recognition history here.</p>
            </div>
          ) : (
            <>
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-50 border-b">
                    <tr>
                      <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                      <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Name</th>
                      <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Image ID</th>
                      <th className="text-left px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Time</th>
                      <th className="text-right px-6 py-3 text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {filtered.map((log) => (
                      <tr key={log.id} className="hover:bg-gray-50 transition">
                        {editId === log.id ? (
                          <>
                            <td className="px-6 py-4">
                              <select value={editIsKnown} onChange={(e) => setEditIsKnown(e.target.value === 'true')}
                                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-primary-500 outline-none">
                                <option value="true">Known</option>
                                <option value="false">Unknown</option>
                              </select>
                            </td>
                            <td className="px-6 py-4 text-sm font-medium text-gray-900">{log.matched_name || '—'}</td>
                            <td className="px-6 py-4 text-sm text-gray-400 font-mono">{log.image_id?.slice(0, 8)}...</td>
                            <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">{new Date(log.processed_at).toLocaleString()}</td>
                            <td className="px-6 py-4 text-right">
                              <div className="flex items-center justify-end gap-2">
                                <button onClick={() => saveEdit(log.id)}
                                  className="text-sm text-primary-600 hover:text-primary-800 font-medium">Save</button>
                                <button onClick={cancelEdit}
                                  className="text-sm text-gray-500 hover:text-gray-700 font-medium">Cancel</button>
                              </div>
                            </td>
                          </>
                        ) : (
                          <>
                            <td className="px-6 py-4">
                              <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${
                                log.is_known ? 'bg-green-100 text-green-800' : 'bg-yellow-100 text-yellow-800'
                              }`}>
                                <span className={`w-1.5 h-1.5 rounded-full ${log.is_known ? 'bg-green-500' : 'bg-yellow-500'}`}></span>
                                {log.is_known ? 'Known' : 'Unknown'}
                              </span>
                            </td>
                            <td className="px-6 py-4">
                              <Link to="/reports" className="text-sm font-medium text-gray-900 hover:text-primary-600 transition">
                                {log.matched_name || '—'}
                              </Link>
                            </td>
                            <td className="px-6 py-4 text-sm text-gray-400 font-mono">{log.image_id?.slice(0, 8)}...</td>
                            <td className="px-6 py-4 text-sm text-gray-500 whitespace-nowrap">{new Date(log.processed_at).toLocaleString()}</td>
                            <td className="px-6 py-4 text-right">
                              <div className="flex items-center justify-end gap-2">
                                <button onClick={() => startEdit(log)}
                                  className="text-sm text-primary-600 hover:text-primary-800 font-medium">Edit</button>
                                <button onClick={() => handleDelete(log)}
                                  className="text-sm text-red-600 hover:text-red-800 font-medium">Delete</button>
                              </div>
                            </td>
                          </>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {totalPages > 1 && (
                <div className="flex items-center justify-between px-6 py-4 border-t bg-gray-50">
                  <span className="text-sm text-gray-500">Page {page} of {totalPages}</span>
                  <div className="flex gap-2">
                    <button disabled={page <= 1} onClick={() => setPage(page - 1)}
                      className="px-4 py-2 text-sm rounded-lg border bg-white hover:bg-gray-50 disabled:opacity-40 transition font-medium">Previous</button>
                    <button disabled={page >= totalPages} onClick={() => setPage(page + 1)}
                      className="px-4 py-2 text-sm rounded-lg border bg-white hover:bg-gray-50 disabled:opacity-40 transition font-medium">Next</button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  )
}
