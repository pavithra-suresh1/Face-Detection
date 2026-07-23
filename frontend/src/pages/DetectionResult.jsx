import { useState, useEffect } from 'react'
import { useParams, useLocation, Link } from 'react-router-dom'
import { getImage } from '../api/uploadApi'
import Loading from '../components/common/Loading'
import FaceCard from '../components/face/FaceCard'

export default function DetectionResult() {
  const { id } = useParams()
  const location = useLocation()
  const [image, setImage] = useState(null)
  const [result, setResult] = useState(location.state?.result)
  const [loading, setLoading] = useState(!result)

  useEffect(() => {
    if (!result) {
      getImage(id).then((res) => setImage(res.data)).finally(() => setLoading(false))
    } else {
      getImage(id).then((res) => setImage(res.data)).catch(() => {})
      setLoading(false)
    }
  }, [id, result])

  if (loading) return <Loading message="Loading result..." />

  const processedUrl = image?.processed_image
    ? `http://localhost:8000${image.processed_image}`
    : null
  const originalUrl = image?.image
    ? `http://localhost:8000${image.image}`
    : null

  const faces = result?.faces || []
  const registeredCount = faces.filter(f => f.is_known === true).length
  const unregisteredCount = faces.filter(f => f.is_known === false).length

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Detection Results</h1>
          <p className="text-gray-500">{result?.face_count || 0} face(s) detected</p>
        </div>
        <Link to="/upload" className="text-primary-600 hover:text-primary-800 font-medium text-sm">Upload Another</Link>
      </div>

      {faces.length > 0 && (
        <div className="flex items-center gap-4 mb-6">
          {registeredCount > 0 && (
            <span className="flex items-center gap-1.5 text-sm text-green-700 bg-green-50 px-3 py-1.5 rounded-lg border border-green-200">
              <span className="w-2 h-2 rounded-full bg-green-500" />
              {registeredCount} registered
            </span>
          )}
          {unregisteredCount > 0 && (
            <span className="flex items-center gap-1.5 text-sm text-red-700 bg-red-50 px-3 py-1.5 rounded-lg border border-red-200">
              <span className="w-2 h-2 rounded-full bg-red-500" />
              {unregisteredCount} unregistered
            </span>
          )}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
        {originalUrl && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="text-sm font-medium text-gray-500 mb-3">Original Image</h3>
            <img src={originalUrl} alt="Original" className="w-full rounded-lg" />
          </div>
        )}
        {processedUrl && (
          <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
            <h3 className="text-sm font-medium text-gray-500 mb-3">Processed Image</h3>
            <img src={processedUrl} alt="Processed" className="w-full rounded-lg" />
          </div>
        )}
      </div>

      {result?.faces && result.faces.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Face Details</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {result.faces.map((face, idx) => (
              <FaceCard key={face.id || idx} face={face} />
            ))}
          </div>
        </div>
      )}

      {result?.face_count === 0 && (
        <div className="text-center py-12 bg-white rounded-xl border">
          <p className="text-gray-500">No faces were detected in this image.</p>
          <Link to="/upload" className="text-primary-600 hover:text-primary-800 font-medium text-sm mt-2 inline-block">Try another image</Link>
        </div>
      )}
    </div>
  )
}
