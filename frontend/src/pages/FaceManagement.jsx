import { useState, useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'
import {
  listKnownFaces, createKnownFace, addFaceImages,
  updateKnownFace, deleteKnownFace, deleteFaceImage,
} from '../api/faceApi'
import Loading from '../components/common/Loading'

export default function FaceManagement() {
  const [faces, setFaces] = useState([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)

  const loadFaces = async () => {
    try {
      const res = await listKnownFaces()
      setFaces(res.data)
    } catch (err) {
      console.error('Failed to load faces:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadFaces() }, [])

  if (loading) return <Loading message="Loading known faces..." />

  return (
    <div className="max-w-7xl mx-auto px-4 py-8">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Known Faces</h1>
          <p className="text-gray-500">Register faces for recognition</p>
        </div>
        <button onClick={() => setShowForm(!showForm)}
          className="bg-primary-600 text-white px-5 py-2 rounded-lg hover:bg-primary-700 transition font-medium">
          {showForm ? 'Cancel' : '+ Register New Face'}
        </button>
      </div>

      {showForm && <RegistrationForm onDone={() => { setShowForm(false); loadFaces() }} />}

      {faces.length === 0 && !showForm && (
        <div className="text-center py-16 text-gray-500 bg-white rounded-xl border">
          <p className="text-lg mb-2">No known faces registered yet.</p>
          <p className="text-sm">Click "Register New Face" to get started.</p>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {faces.map((face) => (
          <PersonCard key={face.id} face={face} onDelete={() => loadFaces()} onUpdate={() => loadFaces()} />
        ))}
      </div>
    </div>
  )
}

function RegistrationForm({ onDone }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [files, setFiles] = useState([])
  const [previews, setPreviews] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')
  const fileRef = useRef(null)

  const handleFiles = (e) => {
    const selected = Array.from(e.target.files)
    const capped = selected.slice(0, 5 - files.length)
    if (selected.length > capped.length) {
      setError(`Only ${5 - files.length} more image(s) allowed (max 5).`)
    }
    setFiles((prev) => [...prev, ...capped])
    setPreviews((prev) => [
      ...prev,
      ...capped.map((f) => URL.createObjectURL(f)),
    ])
  }

  const removeFile = (idx) => {
    setFiles((prev) => prev.filter((_, i) => i !== idx))
    setPreviews((prev) => prev.filter((_, i) => i !== idx))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!name || files.length < 3) return
    setSubmitting(true)
    setError('')
    try {
      await createKnownFace(name, email, files)
      onDone()
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to register face.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
      <h2 className="font-semibold text-gray-900 mb-4">Register New Face</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input type="text" value={name} onChange={(e) => setName(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              placeholder="Person's name" required />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none"
              placeholder="person@example.com" />
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Face Photos (3-5 images required)</label>
          <input ref={fileRef} type="file" accept="image/*" multiple onChange={handleFiles}
            className="w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary-50 file:text-primary-700 hover:file:bg-primary-100" />
          {previews.length > 0 && (
            <p className={`text-xs mt-1 ${previews.length < 3 ? 'text-red-500' : previews.length > 5 ? 'text-orange-500' : 'text-green-600'}`}>
              {previews.length} of 5 images selected
              {previews.length < 3 && ` — need at least ${3 - previews.length} more`}
              {previews.length > 5 && ` — only the first 5 will be uploaded`}
            </p>
          )}
        </div>

        {previews.length > 0 && (
          <div className="flex flex-wrap gap-3">
            {previews.map((url, idx) => (
              <div key={idx} className="relative group">
                <img src={url} alt={`Preview ${idx + 1}`} className="w-24 h-24 object-cover rounded-lg border" />
                <button type="button" onClick={() => removeFile(idx)}
                  className="absolute -top-2 -right-2 w-5 h-5 bg-red-500 text-white rounded-full text-xs flex items-center justify-center opacity-0 group-hover:opacity-100 transition">x</button>
              </div>
            ))}
          </div>
        )}

        {error && <p className="text-red-500 text-sm">{error}</p>}

        <button type="submit" disabled={submitting || files.length < 3}
          className="bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 transition disabled:opacity-50 font-medium">
          {submitting ? 'Registering...' : files.length < 3 ? `Need ${3 - files.length} more image${3 - files.length !== 1 ? 's' : ''}` : `Register Face (${files.length} images)`}
        </button>
      </form>
    </div>
  )
}

function PersonCard({ face, onDelete, onUpdate }) {
  const [editing, setEditing] = useState(false)
  const [editName, setEditName] = useState(face.name)
  const [editEmail, setEditEmail] = useState(face.email || '')
  const [deleting, setDeleting] = useState(false)
  const [adding, setAdding] = useState(false)
  const fileRef = useRef(null)

  const handleAddImages = async (e) => {
    const files = Array.from(e.target.files)
    if (files.length === 0) return
    try {
      await addFaceImages(face.id, files)
      onUpdate()
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to add images.')
    }
    setAdding(false)
  }

  const handleDeleteImage = async (imageId) => {
    if (!confirm('Remove this image?')) return
    try {
      await deleteFaceImage(face.id, imageId)
      onUpdate()
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to delete image.')
    }
  }

  const handleSaveEdit = async () => {
    if (!editName.trim()) return
    try {
      await updateKnownFace(face.id, { name: editName, email: editEmail })
      setEditing(false)
      onUpdate()
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to update.')
    }
  }

  const handleCancelEdit = () => {
    setEditName(face.name)
    setEditEmail(face.email || '')
    setEditing(false)
  }

  const handleDelete = async () => {
    if (!confirm(`Delete "${face.name}" and all their images?`)) return
    setDeleting(true)
    try {
      await deleteKnownFace(face.id)
      onDelete()
    } catch (err) {
      alert(err.response?.data?.message || 'Failed to delete face.')
    } finally {
      setDeleting(false)
    }
  }

  if (editing) {
    return (
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
        <h3 className="font-semibold text-gray-900 text-lg mb-4">Edit {face.name}</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
            <input type="text" value={editName} onChange={(e) => setEditName(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input type="email" value={editEmail} onChange={(e) => setEditEmail(e.target.value)}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 outline-none" />
          </div>
          <div className="flex gap-2 pt-2">
            <button onClick={handleSaveEdit}
              className="bg-primary-600 text-white px-4 py-2 rounded-lg hover:bg-primary-700 transition text-sm font-medium">
              Save
            </button>
            <button onClick={handleCancelEdit}
              className="bg-gray-100 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-200 transition text-sm font-medium">
              Cancel
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <Link to="/reports" className="block">
        <div className="flex items-start justify-between mb-3">
          <div>
            <h3 className="font-semibold text-gray-900 text-lg hover:text-primary-600 transition">{face.name}</h3>
            {face.email && <p className="text-xs text-gray-500">{face.email}</p>}
            <p className={`text-xs ${face.image_count < 3 ? 'text-orange-500 font-medium' : 'text-gray-400'}`}>
              {face.image_count} image{face.image_count !== 1 ? 's' : ''}
              {face.image_count < 3 && ' (add more for better accuracy)'}
            </p>
          </div>
        </div>
      </Link>

      <div className="flex flex-wrap gap-2 mb-3">
        {face.face_images?.map((img) => (
          <div key={img.id} className="relative group">
            <img src={`http://localhost:8000${img.image}`} alt=""
              className="w-16 h-16 object-cover rounded-lg border" />
            {face.image_count > 3 && (
              <button onClick={() => handleDeleteImage(img.id)}
                className="absolute -top-1.5 -right-1.5 w-4 h-4 bg-red-500 text-white rounded-full text-[10px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition">x</button>
            )}
          </div>
        ))}
        <button onClick={() => setAdding(!adding)}
          className="w-16 h-16 border-2 border-dashed border-gray-300 rounded-lg flex items-center justify-center text-gray-400 hover:border-primary-400 hover:text-primary-500 transition text-lg font-light">+</button>
      </div>

      {adding && (
        <input ref={fileRef} type="file" accept="image/*" multiple onChange={handleAddImages}
          className="text-sm text-gray-500 file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:font-medium file:bg-primary-50 file:text-primary-700" />
      )}

      <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
        <p className="text-xs text-gray-400">Added {new Date(face.created_at).toLocaleDateString()}</p>
        <div className="flex gap-2">
          <button onClick={() => setEditing(true)}
            className="text-sm text-primary-600 hover:text-primary-800 font-medium">Edit</button>
          <button onClick={handleDelete} disabled={deleting}
            className="text-sm text-red-600 hover:text-red-800 font-medium">{deleting ? 'Deleting...' : 'Delete'}</button>
        </div>
      </div>
    </div>
  )
}
