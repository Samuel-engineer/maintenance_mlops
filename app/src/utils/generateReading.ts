import type { SensorReading } from '../types'

export function generateReading(prev?: SensorReading): SensorReading {
  const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v))
  const jitter = (v: number, r: number) => v + (Math.random() - 0.5) * r
  const types: SensorReading['product_type'][] = ['L', 'M', 'H']
  if (!prev) {
    return {
      product_type: types[Math.floor(Math.random() * 3)],
      air_temperature_k: +(298 + Math.random() * 4).toFixed(1),
      process_temperature_k: +(308 + Math.random() * 4).toFixed(1),
      rotational_speed_rpm: 1400 + Math.floor(Math.random() * 600),
      torque_nm: +(25 + Math.random() * 30).toFixed(1),
      tool_wear_min: Math.floor(Math.random() * 200),
    }
  }
  return {
    product_type: Math.random() < 0.02 ? types[Math.floor(Math.random() * 3)] : prev.product_type,
    air_temperature_k: clamp(+jitter(prev.air_temperature_k, 0.4).toFixed(1), 291, 319),
    process_temperature_k: clamp(+jitter(prev.process_temperature_k, 0.4).toFixed(1), 296, 324),
    rotational_speed_rpm: clamp(Math.round(jitter(prev.rotational_speed_rpm, 40)), 1000, 2900),
    torque_nm: clamp(+jitter(prev.torque_nm, 2).toFixed(1), 5, 115),
    tool_wear_min: clamp(prev.tool_wear_min + Math.floor(Math.random() * 3), 0, 300),
  }
}
