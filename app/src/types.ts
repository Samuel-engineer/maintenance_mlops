export interface SensorReading {
  product_type: 'L' | 'M' | 'H'
  air_temperature_k: number
  process_temperature_k: number
  rotational_speed_rpm: number
  torque_nm: number
  tool_wear_min: number
}

export interface PredictionResponse {
  failure_proba: number
  failure_alert: boolean
  failure_types: string[]
  recommended_actions: string[]
}

export type ApiStatus = 'idle' | 'loading' | 'success' | 'error'

export interface HistoryEntry {
  id: number
  ts: string
  reading: SensorReading
  result: PredictionResponse
}
