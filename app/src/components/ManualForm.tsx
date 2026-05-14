import { useState } from 'react'
import { motion } from 'framer-motion'
import { Send, Download } from 'lucide-react'
import type { SensorReading } from '../types'

const DEFAULT: SensorReading = {
  product_type: 'M',
  air_temperature_k: 300.0,
  process_temperature_k: 310.0,
  rotational_speed_rpm: 1500,
  torque_nm: 40.0,
  tool_wear_min: 100,
}

const FIELDS = [
  { key: 'air_temperature_k'     as const, label: 'Température air (K)',     min: 291,  max: 319,  step: 0.1 },
  { key: 'process_temperature_k' as const, label: 'Température procédé (K)', min: 296,  max: 324,  step: 0.1 },
  { key: 'rotational_speed_rpm'  as const, label: 'Vitesse rotation (RPM)',  min: 1000, max: 2900, step: 10  },
  { key: 'torque_nm'             as const, label: 'Couple (Nm)',             min: 5,    max: 115,  step: 0.5 },
  { key: 'tool_wear_min'         as const, label: 'Usure outil (min)',       min: 0,    max: 300,  step: 1   },
] as const

interface Props {
  onSubmit: (r: SensorReading) => void
  loading: boolean
  lastReading?: SensorReading
}

export function ManualForm({ onSubmit, loading, lastReading }: Props) {
  const [vals, setVals] = useState<SensorReading>(DEFAULT)

  const set = (key: keyof SensorReading, v: string | number) =>
    setVals(prev => ({ ...prev, [key]: v }))

  const handleSubmit = () =>
    onSubmit({
      product_type:           vals.product_type,
      air_temperature_k:      +Number(vals.air_temperature_k).toFixed(1),
      process_temperature_k:  +Number(vals.process_temperature_k).toFixed(1),
      rotational_speed_rpm:   Math.round(Number(vals.rotational_speed_rpm)),
      torque_nm:              +Number(vals.torque_nm).toFixed(1),
      tool_wear_min:          Math.round(Number(vals.tool_wear_min)),
    })

  return (
    <div className="flex flex-col gap-3">

      {/* Product type */}
      <div>
        <p className="text-xs text-slate-500 mb-1.5">Type produit</p>
        <div className="flex gap-1.5">
          {(['L', 'M', 'H'] as const).map(t => (
            <button
              key={t}
              onClick={() => set('product_type', t)}
              className={`flex-1 py-1.5 rounded-lg text-sm font-bold border transition ${
                vals.product_type === t
                  ? 'bg-cyan-600/30 border-cyan-500/50 text-cyan-400'
                  : 'bg-slate-800/80 border-slate-700 text-slate-400 hover:border-slate-500'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* Numeric fields with slider */}
      {FIELDS.map(f => (
        <div key={f.key} className="bg-slate-800/40 rounded-lg px-2.5 py-2">
          <div className="flex items-center justify-between mb-1.5">
            <span className="text-xs text-slate-400">{f.label}</span>
            <input
              type="number"
              value={vals[f.key]}
              min={f.min}
              max={f.max}
              step={f.step}
              onChange={e => set(f.key, e.target.value)}
              className="w-20 bg-transparent border-b border-slate-600 focus:border-cyan-500 text-xs font-mono text-cyan-400 text-right outline-none"
            />
          </div>
          <input
            type="range"
            min={f.min}
            max={f.max}
            step={f.step}
            value={Number(vals[f.key])}
            onChange={e => set(f.key, Number(e.target.value))}
            className="w-full accent-cyan-500 cursor-pointer"
          />
        </div>
      ))}

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        {lastReading && (
          <button
            onClick={() => setVals(lastReading)}
            className="flex items-center gap-1.5 px-3 py-2 bg-slate-800/80 hover:bg-slate-700 border border-slate-700 rounded-lg text-xs text-slate-400 transition shrink-0"
          >
            <Download size={11} /> Dernier
          </button>
        )}
        <motion.button
          whileTap={{ scale: 0.97 }}
          onClick={handleSubmit}
          disabled={loading}
          className="flex-1 flex items-center justify-center gap-2 bg-cyan-600/20 hover:bg-cyan-600/30 disabled:opacity-40 border border-cyan-500/30 rounded-lg py-2.5 text-cyan-400 text-sm font-semibold transition"
        >
          <Send size={13} className={loading ? 'animate-pulse' : ''} />
          {loading ? 'Envoi…' : 'Envoyer'}
        </motion.button>
      </div>

    </div>
  )
}
