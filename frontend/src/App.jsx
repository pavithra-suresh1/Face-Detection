import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import ProtectedRoute from './components/common/ProtectedRoute'
import PublicRoute from './components/common/PublicRoute'
import AppLayout from './components/common/AppLayout'
import Loading from './components/common/Loading'
import Login from './pages/Login'
import Register from './pages/Register'
import ForgotPassword from './pages/ForgotPassword'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import DetectionResult from './pages/DetectionResult'
import FaceManagement from './pages/FaceManagement'
import RealtimeDetection from './pages/RealtimeDetection'
import History from './pages/History'
import Report from './pages/Report'

export default function App() {
  const { loading } = useAuth()

  if (loading) return <Loading message="Loading..." />

  return (
    <Routes>
      <Route path="/login" element={<PublicRoute><Login /></PublicRoute>} />
      <Route path="/register" element={<PublicRoute><Register /></PublicRoute>} />
      <Route path="/forgot-password" element={<PublicRoute><ForgotPassword /></PublicRoute>} />

      <Route
        path="/dashboard"
        element={
          <ProtectedRoute>
            <AppLayout><Dashboard /></AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/upload"
        element={
          <ProtectedRoute>
            <AppLayout><Upload /></AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/detect/:id"
        element={
          <ProtectedRoute>
            <AppLayout><DetectionResult /></AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/known-faces"
        element={
          <ProtectedRoute>
            <AppLayout><FaceManagement /></AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/realtime"
        element={
          <ProtectedRoute>
            <AppLayout><RealtimeDetection /></AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/history"
        element={
          <ProtectedRoute>
            <AppLayout><History /></AppLayout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/reports"
        element={
          <ProtectedRoute>
            <AppLayout><Report /></AppLayout>
          </ProtectedRoute>
        }
      />

      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  )
}
