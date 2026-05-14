export const FAILURE_COLORS: Record<string, string> = {
  TWF: 'bg-orange-500', HDF: 'bg-sky-500',
  PWF: 'bg-yellow-500', OSF: 'bg-red-500', RNF: 'bg-purple-500',
}

export const tsNow = () =>
  new Date().toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit', second: '2-digit' })

export const fmtInterval = (s: number) =>
  s < 1 ? `${Math.round(s * 1000)}ms` : `${s.toFixed(2)}s`

export const SENSOR_FIELDS = [
  { key: 'air',    label: 'Air (K)',       icon: 'thermometer' },
  { key: 'proc',   label: 'Procédé (K)',   icon: 'thermometer' },
  { key: 'rpm',    label: 'Vitesse (RPM)', icon: 'rotate'      },
  { key: 'torque', label: 'Couple (Nm)',   icon: 'zap'         },
] as const
