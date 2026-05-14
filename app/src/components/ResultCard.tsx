import { motion } from 'framer-motion'
import { AlertTriangle, CheckCircle2, ChevronRight } from 'lucide-react'
import type { HistoryEntry } from '../types'
import { FAILURE_COLORS } from '../utils/constants'
import { ProbaBar } from './ui'
import { SensorGrid } from './SensorGrid'

export function ResultCard({ entry }: { entry: HistoryEntry }) {
  const { result, reading, ts } = entry
  return (
    <div className={`border rounded-xl p-4 ${
      result.failure_alert
        ? 'bg-red-950/40 border-red-700/50'
        : 'bg-emerald-950/30 border-emerald-700/40'
    }`}>
      {/* Header */}
      <div className="flex items-center gap-3 mb-3">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 400 }}
          className={`w-9 h-9 rounded-full flex items-center justify-center shrink-0 ${
            result.failure_alert ? 'bg-red-500/80' : 'bg-emerald-500/80'
          }`}
        >
          {result.failure_alert
            ? <AlertTriangle size={16} />
            : <CheckCircle2  size={16} />
          }
        </motion.div>
        <div className="flex-1 min-w-0">
          <p className={`font-bold text-sm ${result.failure_alert ? 'text-red-300' : 'text-emerald-300'}`}>
            {result.failure_alert ? 'Panne détectée' : 'Machine normale'}
          </p>
          <p className="text-xs text-slate-500">{ts}</p>
        </div>
        <span className="text-xs font-mono bg-slate-800 border border-slate-700 px-2 py-0.5 rounded text-slate-400 shrink-0">
          Type {reading.product_type}
        </span>
      </div>

      {/* Probability bar */}
      <ProbaBar value={result.failure_proba} />

      {/* Sensor data */}
      <SensorGrid reading={reading} />

      {/* Failure details */}
      {result.failure_alert && (
        <div className="mt-3 flex flex-col gap-2">
          {result.failure_types.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {result.failure_types.map(ft => (
                <span
                  key={ft}
                  className={`px-2 py-0.5 rounded text-xs font-bold text-white ${FAILURE_COLORS[ft] ?? 'bg-slate-600'}`}
                >
                  {ft}
                </span>
              ))}
            </div>
          )}
          {result.recommended_actions.map((a, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -6 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: i * 0.08 }}
              className="flex gap-2 text-xs bg-slate-900/60 rounded-lg px-3 py-2 text-slate-300"
            >
              <ChevronRight size={12} className="text-orange-400 shrink-0 mt-0.5" />
              {a}
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}
