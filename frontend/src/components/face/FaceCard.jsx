export default function FaceCard({ face }) {
  const { bounding_box, is_known, label, confidence } = face

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className={`px-3 py-1 rounded-full text-xs font-semibold tracking-wide ${
          is_known ? 'bg-green-100 text-green-800' :
          is_known === false ? 'bg-yellow-100 text-yellow-800' :
          'bg-blue-100 text-blue-800'
        }`}>
          {label || 'Face Detected'}
        </span>
        {confidence != null && is_known != null && (
          <span className="text-xs font-medium text-gray-500">
            {confidence.toFixed(1)}% match
          </span>
        )}
      </div>
      <div className="text-xs text-gray-400">
        Position: ({bounding_box.x}, {bounding_box.y}) &middot; {bounding_box.w}&times;{bounding_box.h}px
      </div>
    </div>
  )
}
