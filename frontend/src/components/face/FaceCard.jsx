export default function FaceCard({ face }) {
  const { bounding_box, is_known, label } = face

  const displayLabel = is_known ? (label || 'Known') : 'Unknown'
  const statusColor = is_known
    ? 'bg-green-100 text-green-800'
    : 'bg-red-100 text-red-800'

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-2">
        <span className={`px-3 py-1 rounded-full text-xs font-semibold tracking-wide ${statusColor}`}>
          {displayLabel}
        </span>
      </div>
      <div className="flex items-center justify-between mt-1">
        <span className={`text-[10px] font-bold tracking-wider uppercase px-1.5 py-0.5 rounded ${
          is_known ? 'bg-green-50 text-green-600' : 'bg-red-50 text-red-600'
        }`}>
          {is_known ? 'KNOWN' : 'UNKNOWN'}
        </span>
        <span className="text-xs text-gray-400">
          ({bounding_box.x}, {bounding_box.y}) &middot; {bounding_box.w}&times;{bounding_box.h}px
        </span>
      </div>
    </div>
  )
}
