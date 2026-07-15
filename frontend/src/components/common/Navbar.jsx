import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function Navbar() {
  const { user, logoutUser } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logoutUser()
    navigate('/login', { replace: true })
  }

  if (!user) return null

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16 items-center">
          <div className="flex items-center space-x-8">
            <Link to="/dashboard" className="flex items-center space-x-2">
              <div className="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">FR</span>
              </div>
              <span className="text-xl font-bold text-gray-900">FaceRecog AI</span>
            </Link>
            <div className="hidden md:flex space-x-4">
              <Link to="/dashboard" className="text-gray-600 hover:text-gray-900 px-3 py-2 text-sm font-medium">Dashboard</Link>
              <Link to="/upload" className="text-gray-600 hover:text-gray-900 px-3 py-2 text-sm font-medium">Upload</Link>
              <Link to="/known-faces" className="text-gray-600 hover:text-gray-900 px-3 py-2 text-sm font-medium">Known Faces</Link>
              <Link to="/history" className="text-gray-600 hover:text-gray-900 px-3 py-2 text-sm font-medium">History</Link>
              <Link to="/reports" className="text-gray-600 hover:text-gray-900 px-3 py-2 text-sm font-medium">Reports</Link>
              <Link to="/realtime" className="text-gray-600 hover:text-gray-900 px-3 py-2 text-sm font-medium">Live</Link>
            </div>
          </div>
          <div className="flex items-center space-x-4">
            <span className="text-sm text-gray-500">{user.username}</span>
            <button
              onClick={handleLogout}
              className="text-sm text-red-600 hover:text-red-800 font-medium"
            >
              Logout
            </button>
          </div>
        </div>
      </div>
    </nav>
  )
}
