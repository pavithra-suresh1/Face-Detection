import { Link } from 'react-router-dom'

export default function ForgotPassword() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-primary-50 to-blue-100 py-12 px-4">
      <div className="max-w-md w-full bg-white rounded-2xl shadow-xl p-8 text-center">
        <div className="w-16 h-16 bg-primary-600 rounded-2xl flex items-center justify-center mx-auto mb-4">
          <span className="text-white font-bold text-2xl">FR</span>
        </div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">Forgot Password</h2>
        <p className="text-gray-500 mb-6">
          Password reset is not available in the demo.
          <br />
          Please contact your administrator to reset your password.
        </p>
        <Link
          to="/login"
          className="inline-block bg-primary-600 text-white px-6 py-2 rounded-lg hover:bg-primary-700 transition font-medium"
        >
          Back to Login
        </Link>
      </div>
    </div>
  )
}
