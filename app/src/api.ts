import type { SensorReading, PredictionResponse } from './types'

export async function predict(reading: SensorReading): Promise<PredictionResponse> {
  const res = await fetch('/api/predict', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(reading),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? 'Erreur API')
  }
  return res.json()
}
