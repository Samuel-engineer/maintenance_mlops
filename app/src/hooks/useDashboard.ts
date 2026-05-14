import { useState, useEffect, useRef, useCallback } from 'react'
import { predict } from '../api'
import type { SensorReading, HistoryEntry } from '../types'
import { generateReading } from '../utils/generateReading'
import { tsNow } from '../utils/constants'

export function useDashboard() {
  const [streaming, setStreaming]         = useState(false)
  const [intervalS, setIntervalS]         = useState(1.5)
  const [intervalInput, setIntervalInput] = useState('1.5')
  const [history, setHistory]             = useState<HistoryEntry[]>([])
  const [current, setCurrent]             = useState<HistoryEntry | null>(null)
  const [apiError, setApiError]           = useState<string | null>(null)
  const [loading, setLoading]             = useState(false)

  const counter        = useRef(0)
  const lastReadingRef = useRef<SensorReading | undefined>(undefined)
  const timerRef       = useRef<ReturnType<typeof setTimeout> | null>(null)

  const send = useCallback(async (reading: SensorReading) => {
    setLoading(true)
    setApiError(null)
    try {
      const result = await predict(reading)
      const entry: HistoryEntry = { id: ++counter.current, ts: tsNow(), reading, result }
      setCurrent(entry)
      setHistory(h => [entry, ...h].slice(0, 100))
    } catch (e) {
      setApiError(e instanceof Error ? e.message : 'Erreur API')
    } finally {
      setLoading(false)
    }
  }, [])

  const sendAuto = useCallback(async () => {
    const reading = generateReading(lastReadingRef.current)
    lastReadingRef.current = reading
    await send(reading)
  }, [send])

  const sendManual = useCallback(async (reading: SensorReading) => {
    lastReadingRef.current = reading
    await send(reading)
  }, [send])

  useEffect(() => {
    if (!streaming) {
      if (timerRef.current) clearTimeout(timerRef.current)
      return
    }
    const loop = async () => {
      await sendAuto()
      timerRef.current = setTimeout(loop, intervalS * 1000)
    }
    timerRef.current = setTimeout(loop, intervalS * 1000)
    return () => { if (timerRef.current) clearTimeout(timerRef.current) }
  }, [streaming, intervalS, sendAuto])

  const reset = useCallback(() => {
    setStreaming(false)
    setHistory([])
    setCurrent(null)
    setApiError(null)
    lastReadingRef.current = undefined
    counter.current = 0
  }, [])

  const total     = history.length
  const pannes    = history.filter(h => h.result.failure_alert).length
  const taux      = total > 0 ? ((pannes / total) * 100).toFixed(1) : '0.0'
  const tauxColor = Number(taux) < 10 ? 'text-emerald-400' : Number(taux) < 20 ? 'text-yellow-400' : 'text-red-400'

  return {
    streaming, setStreaming,
    intervalS, setIntervalS,
    intervalInput, setIntervalInput,
    history, current,
    apiError, loading,
    sendAuto, sendManual, reset,
    stats: { total, pannes, taux, tauxColor },
    lastReading: current?.reading,
  }
}
