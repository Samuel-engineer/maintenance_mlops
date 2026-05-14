import { motion } from 'framer-motion'

// ── ProbaBar ──────────────────────────────────────────────────────────────────

interface ProbaBarProps { value: number; compact?: boolean }

export function ProbaBar({ value, compact = false }: ProbaBarProps) {
  const pct = Math.round(value * 100)
  const color = pct < 30 ? 'from-emerald-500 to-emerald-400'
    : pct < 65 ? 'from-yellow-400 to-orange-400'
    : 'from-orange-500 to-red-500'
  const textColor = pct < 30 ? 'text-emerald-400' : pct < 65 ? 'text-yellow-400' : 'text-red-400'
  return (
    <div className="w-full">
      {!compact && (
        <div className="flex justify-between text-xs mb-1 font-mono">
          <span className="text-slate-500">Confiance de panne</span>
          <span className={`font-bold ${textColor}`}>{pct}%</span>
        </div>
      )}
      <div className="h-2 rounded-full bg-slate-800 overflow-hidden">
        <motion.div
          className={`h-full rounded-full bg-linear-to-r ${color}`}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.5, ease: 'easeOut' }}
        />
      </div>
    </div>
  )
}

// ── Stat ──────────────────────────────────────────────────────────────────────

interface StatProps { label: string; value: string | number; color?: string; compact?: boolean }

export function Stat({ label, value, color = 'text-white', compact = false }: StatProps) {
  return (
    <div>
      <p className="text-xs uppercase tracking-widest text-slate-500 font-semibold mb-0.5">{label}</p>
      <motion.p
        key={String(value)}
        initial={{ opacity: 0, y: -4 }}
        animate={{ opacity: 1, y: 0 }}
        className={`font-mono font-bold ${compact ? 'text-2xl' : 'text-3xl'} ${color}`}
      >
        {value}
      </motion.p>
    </div>
  )
}
