import { useState, useCallback, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { useDropzone } from 'react-dropzone'
import { uploadImage, listImages, deleteImage } from '../api/uploadApi'
import { detectFaces } from '../api/faceApi'
import Loading from '../components/common/Loading'

export default function Upload() {
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState(null)
  const [uploading, setUploading] = useState(false)
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState('')
  const [images, setImages] = useState([])
  const [loadingImages, setLoadingImages] = useState(true)
  const navigate = useNavigate()

  const loadImages = async () => {
    try {
      const res = await listImages()
      setImages(res.data || [])
    } catch {} finally {
      setLoadingImages(false)
    }
  }

  useEffect(() => { loadImages() }, [])

  const onDrop = useCallback((acceptedFiles) => {
    const f = acceptedFiles[0]
    if (f) {
      setFile(f)
      setPreview(URL.createObjectURL(f))
      setError('')
    }
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'image/*': ['.jpeg', '.jpg', '.png', '.webp'] },
    maxSize: 10 * 1024 * 1024,
    maxFiles: 1,
  })

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError('')
    try {
      const uploadRes = await uploadImage(file)
      const imageId = uploadRes.data.id
      setProcessing(true)
      const detectRes = await detectFaces(imageId, true)
      navigate(`/detect/${imageId}`, { state: { result: detectRes } })
    } catch (err) {
      setError(err.response?.data?.message || 'Upload failed.')
    } finally {
      setUploading(false)
      setProcessing(false)
    }
  }

  const reset = () => { setFile(null); setPreview(null); setError('') }

  const handleDelete = async (id) => {
    if (!confirm('Delete this uploaded image?')) return
    try {
      await deleteImage(id)
      setImages((prev) => prev.filter((img) => img.id !== id))
    } catch {}
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">Upload Image</h1>
        <p className="text-gray-500">Upload a photo for face detection and recognition</p>
      </div>

      <div className="max-w-3xl">
        <div {...getRootProps()} className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition ${
          isDragActive ? 'border-primary-500 bg-primary-50' : 'border-gray-300 hover:border-gray-400 bg-white'
        }`}>
          <input {...getInputProps()} />
          {preview ? (
            <img src={preview} alt="Preview" className="max-h-80 mx-auto rounded-lg" />
          ) : (
            <div className="text-gray-400">
              <svg className="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <p className="text-lg font-medium mb-1">{isDragActive ? 'Drop image here' : 'Drag & drop an image'}</p>
              <p className="text-sm">or click to browse (JPEG, PNG, WebP &middot; max 10MB)</p>
            </div>
          )}
        </div>

        {file && (
          <div className="mt-6 bg-white rounded-xl shadow-sm border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-primary-100 rounded-lg flex items-center justify-center text-primary-600 font-bold text-lg">
                  {file.name.split('.').pop().toUpperCase()}
                </div>
                <div>
                  <p className="font-medium text-gray-900 truncate max-w-xs">{file.name}</p>
                  <p className="text-xs text-gray-400">{(file.size / 1024 / 1024).toFixed(2)} MB</p>
                </div>
              </div>
              <button onClick={reset} className="text-gray-400 hover:text-red-500 text-sm">Remove</button>
            </div>

            {(uploading || processing) && (
              <div className="w-full bg-gray-200 rounded-full h-2 mb-4">
                <div className={`h-2 rounded-full transition-all duration-500 ${uploading ? 'bg-blue-500 w-2/3' : 'bg-green-500 w-full'}`}></div>
              </div>
            )}

            <button onClick={handleUpload} disabled={uploading || processing}
              className="w-full bg-primary-600 text-white py-3 rounded-xl hover:bg-primary-700 transition disabled:opacity-50 font-medium text-lg shadow-sm">
              {uploading ? 'Uploading...' : processing ? 'Analyzing Faces...' : 'Upload & Analyze'}
            </button>
          </div>
        )}

        {error && <p className="mt-4 text-red-500 text-sm text-center">{error}</p>}
      </div>

      <div className="mt-12">
        <h2 className="text-xl font-bold text-gray-900 mb-4">Previously Uploaded Images</h2>

        {loadingImages ? (
          <Loading message="Loading images..." />
        ) : images.length === 0 ? (
          <div className="text-center py-16 text-gray-500 bg-white rounded-xl border">
            <p className="text-lg mb-2">No uploaded images yet.</p>
            <p className="text-sm">Upload an image above to get started.</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
            {images.map((img) => (
              <div key={img.id} className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden group">
                <Link to={`/detect/${img.id}`} className="block">
                  <div className="aspect-square bg-gray-100">
                    <img
                      src={`http://localhost:8000${img.processed_image || img.image}`}
                      alt="Uploaded"
                      className="w-full h-full object-cover"
                    />
                  </div>
                </Link>
                <div className="p-3">
                  <p className="text-[11px] text-gray-400">
                    {new Date(img.uploaded_at).toLocaleDateString()}
                  </p>
                  <div className="flex items-center justify-between mt-2">
                    <Link to={`/detect/${img.id}`}
                      className="text-xs text-primary-600 hover:text-primary-800 font-medium">
                      View
                    </Link>
                    <button onClick={() => handleDelete(img.id)}
                      className="text-xs text-red-600 hover:text-red-800 font-medium">
                      Delete
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
