import { motion } from 'framer-motion'
import { Thermometer, RotateCcw, Zap, Timer } from 'lucide-react'
import type { SensorReading } from '../types'
import { SENSOR_FIELDS } from '../utils/constants'

const ICONS = [
  <Thermometer size={11} />,
  <Thermometer size={11} />,
  <RotateCcw   size={11} />,
  <Zap         size={11} />,
]

export function SensorGrid({ reading }: { reading: SensorReading }) {
  const wearPct = (reading.tool_wear_min / 300) * 100
  const wearColor = wearPct < 40 ? 'from-emerald-500 to-emerald-400'
    : wearPct < 70 ? 'from-yellow-400 to-orange-400'
    : 'from-orange-500 to-red-500'
  const vals = [
    reading.air_temperature_k.toFixed(1),
    reading.process_temperature_k.toFixed(1),
    reading.rotational_speed_rpm.toLocaleString('fr-FR'),
    reading.torque_nm.toFixed(1),
  ]
  return (
    <div className="grid grid-cols-2 gap-2 mt-3">
      {SENSOR_FIELDS.map((f, i) => (
        <div key={f.key} className="bg-slate-800/60 rounded-lg px-3 py-2">
          <p className="flex items-center gap-1 text-xs text-slate-500 mb-0.5">{ICONS[i]}{f.label}</p>
          <p className="font-mono font-bold text-sm text-slate-100">{vals[i]}</p>
        </div>
      ))}
      <div className="col-span-2 bg-slate-800/60 rounded-lg px-3 py-2">
        <p className="flex items-center gap-1 text-xs text-slate-500 mb-1.5">
          <Timer size={11} />Usure outil — {reading.tool_wear_min} min
        </p>
        <div className="h-1.5 rounded-full bg-slate-700 overflow-hidden">
          <motion.div
            className={`h-full rounded-full bg-linear-to-r ${wearColor}`}
            animate={{ width: `${wearPct}%` }}
            transition={{ duration: 0.4 }}
          />
        </div>
      </div>
    </div>
  )
}
