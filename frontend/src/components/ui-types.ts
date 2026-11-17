export type SlateTone = 'amber' | 'green' | 'red'

export interface SlateRow {
  label: string
  value: string
  tone?: SlateTone
}

export interface StatItem {
  label: string
  value: string | number
  unit?: string
  tone?: SlateTone
}

export type SegValue = string | number
