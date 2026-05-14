import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Activity, AlertTriangle, BarChart3,
  Play, Pause, Zap, RefreshCw, Timer,
  Wifi, WifiOff, Settings2, Sliders,
} from 'lucide-react'
import { useDashboard } from '../hooks/useDashboard'
import { FAILURE_COLORS, fmtInterval } from '../utils/constants'
import { ProbaBar, Stat } from './ui'
import { ManualForm } from './ManualForm'
import { ResultCard } from './ResultCard'


type Tab = 'auto' | 'manual'

export default function Dashboard() {
  const [tab, setTab] = useState<Tab>('auto')
  const {
    streaming, setStreaming,
    intervalS, setIntervalS,
    intervalInput, setIntervalInput,
    history, current,
    apiError, loading,
    sendAuto, sendManual, reset,
    stats, lastReading,
  } = useDashboard()
  const { total, pannes, taux, tauxColor } = stats

  return (
    <div className="h-screen bg-[#0f1117] text-white font-mono flex flex-col overflow-hidden">

      {/* ── Header ── */}
      <header className="shrink-0 border-b border-slate-800/80 px-5 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-cyan-600/20 border border-cyan-500/30 flex items-center justify-center">
            <Settings2 size={16} className="text-cyan-400" />
          </div>
          <div>
            <h1 className="font-bold text-sm tracking-wide">MLOps Maintenance Monitor</h1>
            <p className="text-xs text-slate-500 mt-0.5">Prédiction de défaillances en temps réel</p>
          </div>
        </div>
        <motion.div
          animate={{ opacity: streaming ? [1, 0.4, 1] : 1 }}
          transition={{ repeat: Infinity, duration: 1.2, ease: 'easeInOut' }}
          className={`flex items-center gap-1.5 text-xs font-semibold px-3 py-1 rounded-full border ${
            streaming
              ? 'border-cyan-500/40 bg-cyan-500/10 text-cyan-400'
              : 'border-slate-700 bg-slate-800/50 text-slate-500'
          }`}
        >
          {streaming ? <Wifi size={12} /> : <WifiOff size={12} />}
          {streaming ? 'STREAMING' : 'IDLE'}
        </motion.div>
      </header>

      {/* ── Body ── */}
      <div className="flex-1 grid grid-cols-2 min-h-0">

        {/* ══ LEFT PANEL ══ */}
        <div className="flex flex-col border-r border-slate-800 overflow-hidden">

          {/* Tab bar */}
          <div className="shrink-0 flex gap-0.5 px-4 pt-3 border-b border-slate-800 bg-slate-900/40">
            {([
              { key: 'auto'   as Tab, label: 'Automatique', icon: <Activity size={11} /> },
              { key: 'manual' as Tab, label: 'Manuel',      icon: <Sliders  size={11} /> },
            ]).map(t => (
              <button
                key={t.key}
                onClick={() => setTab(t.key)}
                className={`flex items-center gap-1.5 px-4 py-2 text-xs font-semibold rounded-t-lg border-b-2 transition-colors ${
                  tab === t.key
                    ? 'border-cyan-500 text-cyan-400 bg-slate-800/60'
                    : 'border-transparent text-slate-500 hover:text-slate-300'
                }`}
              >
                {t.icon}{t.label}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div className="flex-1 min-h-0 overflow-y-auto px-4 py-4">
            <AnimatePresence mode="wait">
              {tab === 'auto' ? (

                <motion.div key="auto"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  transition={{ duration: 0.12 }}
                  className="flex flex-col gap-3"
                >
                  {/* Intervalle */}
                  <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
                    <p className="text-xs uppercase tracking-widest text-slate-500 font-semibold flex items-center justify-between mb-3">
                      <span className="flex items-center gap-1.5"><Timer size={11} /> Intervalle d'envoi</span>
                    </p>
                    <div className="flex items-center gap-2 mb-1.5">
                      <input type="range" min="0.12" max="5" step="0.12" value={intervalS}
                        onChange={e => { const v = Number(e.target.value); setIntervalS(v); setIntervalInput(String(v)) }}
                        className="flex-1 accent-cyan-500 cursor-pointer" />
                      <input type="text" value={intervalInput}
                        onChange={e => setIntervalInput(e.target.value)}
                        onBlur={() => {
                          const v = parseFloat(intervalInput)
                          const clamped = isNaN(v) ? intervalS : Math.min(5, Math.max(0.12, v))
                          setIntervalS(clamped); setIntervalInput(String(clamped))
                        }}
                        onKeyDown={e => { if (e.key === 'Enter') (e.target as HTMLInputElement).blur() }}
                        className="w-16 bg-slate-800 border border-slate-700 rounded-lg px-2 py-1 text-xs font-mono text-cyan-400 text-center focus:outline-none focus:ring-1 focus:ring-cyan-500"
                      />
                      <span className="text-xs text-slate-500 shrink-0">s</span>
                    </div>
                    <p className="text-xs text-slate-500">{Math.round(60 / intervalS)} envois/min</p>
                  </section>

                  {/* Contrôles */}
                  <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
                    <p className="text-xs uppercase tracking-widest text-slate-500 font-semibold flex items-center gap-1.5 mb-3">
                      <Activity size={11} /> Contrôles
                    </p>
                    <div className="grid grid-cols-2 gap-2">
                      <button onClick={() => setStreaming(true)} disabled={streaming}
                        className="flex items-center justify-center gap-2 bg-cyan-600/20 hover:bg-cyan-600/30 disabled:opacity-30 disabled:cursor-not-allowed border border-cyan-500/30 rounded-lg py-2.5 text-cyan-400 text-sm font-semibold transition">
                        <Play size={14} /> Démarrer
                      </button>
                      <button onClick={() => setStreaming(false)} disabled={!streaming}
                        className="flex items-center justify-center gap-2 bg-slate-700/50 hover:bg-slate-700 disabled:opacity-30 disabled:cursor-not-allowed border border-slate-600 rounded-lg py-2.5 text-slate-300 text-sm font-semibold transition">
                        <Pause size={14} /> Arrêter
                      </button>
                      <button onClick={sendAuto} disabled={loading}
                        className="flex items-center justify-center gap-2 bg-yellow-500/10 hover:bg-yellow-500/20 disabled:opacity-40 border border-yellow-500/30 rounded-lg py-2.5 text-yellow-400 text-sm font-semibold transition">
                        <Zap size={14} className={loading ? 'animate-pulse' : ''} />
                        {loading ? 'Envoi…' : 'Déclencher'}
                      </button>
                      <button onClick={reset}
                        className="flex items-center justify-center gap-2 bg-slate-800 hover:bg-slate-700 border border-slate-700 rounded-lg py-2.5 text-slate-400 text-sm font-semibold transition">
                        <RefreshCw size={13} /> Réinit.
                      </button>
                    </div>
                  </section>

                  {/* Erreur */}
                  <AnimatePresence>
                    {apiError && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
                        className="bg-red-950/60 border border-red-700/50 rounded-xl px-4 py-3 text-red-400 text-xs flex items-start gap-2"
                      >
                        <AlertTriangle size={14} className="shrink-0 mt-0.5" />{apiError}
                      </motion.div>
                    )}
                  </AnimatePresence>

                  {/* Statistiques */}
                  <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
                    <p className="text-xs uppercase tracking-widest text-slate-500 font-semibold flex items-center gap-1.5 mb-3">
                      <BarChart3 size={11} /> Statistiques
                    </p>
                    <div className="grid grid-cols-3 gap-4">
                      <Stat label="Total"  value={total} compact />
                      <Stat label="Pannes" value={pannes} color="text-red-400" compact />
                      <Stat label="Taux"   value={`${taux}%`} color={tauxColor} compact />
                    </div>
                  </section>
                </motion.div>

              ) : (

                <motion.div key="manual"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                  transition={{ duration: 0.12 }}
                >
                  <p className="text-xs uppercase tracking-widest text-slate-500 font-semibold flex items-center gap-1.5 mb-4">
                    <Sliders size={11} /> Saisie manuelle
                  </p>
                  <ManualForm onSubmit={sendManual} loading={loading} lastReading={lastReading} />
                </motion.div>

              )}
            </AnimatePresence>
          </div>
        </div>

        {/* ══ RIGHT PANEL ══ */}
        <div className="flex flex-col overflow-hidden">

          {/* Result card — fixed height */}
          <div className="shrink-0 px-5 pt-5">
            <AnimatePresence mode="wait">
              {current ? (
                <motion.div key={current.id}
                  initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <ResultCard entry={current} />
                </motion.div>
              ) : (
                <motion.div key="empty"
                  initial={{ opacity: 0 }} animate={{ opacity: 1 }}
                  className="flex flex-col items-center justify-center h-44 text-slate-700 gap-3 border border-slate-800 rounded-xl bg-slate-900/30"
                >
                  <Activity size={32} strokeWidth={1} />
                  <p className="text-sm">En attente de données…</p>
                </motion.div>
              )}
            </AnimatePresence>
          </div>

          {/* History — fills remaining space */}
          {history.length > 0 && (
            <div className="flex-1 min-h-0 overflow-y-auto px-5 py-4">
              <section className="bg-slate-900/70 border border-slate-800 rounded-xl p-4">
                <p className="text-xs uppercase tracking-widest text-slate-500 font-semibold flex items-center gap-1.5 mb-3">
                  <BarChart3 size={11} /> Historique ({history.length})
                </p>
                <div className="flex flex-col gap-0.5">
                  {history.slice(0, 30).map(entry => (
                    <motion.div key={entry.id}
                      initial={{ opacity: 0, x: -4 }} animate={{ opacity: 1, x: 0 }}
                      className="flex items-center gap-3 py-1.5 border-b border-slate-800/40 last:border-0"
                    >
                      <span className="text-xs text-slate-600 font-mono w-16 shrink-0">{entry.ts}</span>
                      <div className="flex-1"><ProbaBar value={entry.result.failure_proba} compact /></div>
                      <span className={`text-xs font-mono font-bold w-10 text-right shrink-0 ${
                        entry.result.failure_proba > 0.65 ? 'text-red-400'
                        : entry.result.failure_proba > 0.3 ? 'text-yellow-400'
                        : 'text-emerald-400'
                      }`}>
                        {Math.round(entry.result.failure_proba * 100)}%
                        {entry.result.failure_alert && ' ⚠'}
                      </span>
                      {entry.result.failure_types.length > 0 && (
                        <div className="flex gap-1 shrink-0">
                          {entry.result.failure_types.map(ft => (
                            <span key={ft} className={`text-[10px] font-bold px-1.5 py-0.5 rounded text-white ${FAILURE_COLORS[ft] ?? 'bg-slate-600'}`}>
                              {ft}
                            </span>
                          ))}
                        </div>
                      )}
                    </motion.div>
                  ))}
                </div>
              </section>
            </div>
          )}

        </div>
      </div>
    </div>
  )
}
