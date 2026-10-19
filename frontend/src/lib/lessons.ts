/** Представлення заняття: кольори типів, підписи статусів, аудиторія. */

import type { LessonStatus, LessonTypeOption, LessonView, Parity } from '../api/types'

/** Колір типу заняття. Невідомий код отримує нейтральний сірий. */
const TYPE_TOKENS: Record<string, string> = {
  LEC: 'lec',
  LECTURE: 'lec',
  ЛК: 'lec',
  LAB: 'lab',
  ЛБ: 'lab',
  PRACT: 'pract',
  PRACTICE: 'pract',
  ПЗ: 'pract',
  SEM: 'pract',
  ELECT: 'elect',
  ELECTIVE: 'elect',
  ФК: 'elect',
}

export function typeToken(code: string): string {
  return TYPE_TOKENS[code.toUpperCase()] ?? 'other'
}

/** CSS-змінні картки: колір рамки й фон бейджа типу заняття. */
export function typeStyle(code: string): Record<string, string> {
  const token = typeToken(code)
  return {
    ['--type']: `var(--type-${token})`,
    ['--type-soft']: `var(--type-${token}-soft)`,
  }
}

// Звичний для розкладу порядок, а не алфавітний за кодом типу.
const TYPE_ORDER = ['lec', 'lab', 'pract', 'elect', 'other']

export function sortLessonTypes(types: LessonTypeOption[]): LessonTypeOption[] {
  return [...types].sort(
    (left, right) =>
      TYPE_ORDER.indexOf(typeToken(left.code)) - TYPE_ORDER.indexOf(typeToken(right.code)),
  )
}

export const PARITY_LABEL: Record<Parity, string> = {
  ODD: 'I Непарний',
  EVEN: 'II Парний',
  BOTH: 'Щотижня',
}

interface StatusBadge {
  label: string
  tone: 'danger' | 'warning' | 'info'
}

/** Короткий бейдж зміни: заміна, перенесення, скасування. */
export function statusBadge(lesson: LessonView): StatusBadge | null {
  const map: Partial<Record<LessonStatus, StatusBadge>> = {
    CANCELLED: { label: 'Скасовано', tone: 'danger' },
    REPLACED: {
      label: lesson.teachers.some((t) => t.is_substitute) ? 'Заміна викладача' : 'Заміна',
      tone: 'danger',
    },
    MOVED_OUT: { label: 'Перенесено', tone: 'warning' },
    MOVED_IN: { label: 'Перенесене заняття', tone: 'warning' },
    SHIFTED: { label: 'Змінено час', tone: 'warning' },
    ADDED: { label: 'Додаткове заняття', tone: 'info' },
  }
  return map[lesson.status] ?? null
}

/** Пояснення під карткою: причина й куди/звідки перенесено. */
export function statusNote(lesson: LessonView, formatDate: (value: string) => string): string | null {
  const parts: string[] = []
  if (lesson.status === 'MOVED_OUT' && lesson.moved_to) {
    parts.push(`перенесено на ${formatDate(lesson.moved_to)}`)
  }
  if (lesson.status === 'MOVED_IN' && lesson.moved_from) {
    parts.push(`перенесено з ${formatDate(lesson.moved_from)}`)
  }
  if (lesson.change_reason) parts.push(lesson.change_reason)
  return parts.length > 0 ? parts.join(' · ') : null
}

/** «1-а підгрупа» для числових назв, інакше назва як є. */
export function subgroupLabel(name: string): string {
  return /^\d+$/.test(name) ? `${name}-а підгрупа` : name
}

export function subgroupShort(name: string): string {
  return /^\d+$/.test(name) ? `${name} підгр.` : name
}

/** Кому читається пара: потік, підгрупа або перелік груп. */
export function audienceLabel(lesson: LessonView): string | null {
  if (lesson.streams.length > 0) {
    return `Потік ${lesson.streams.join(', ')}`
  }
  if (lesson.subgroups.length > 0) {
    return lesson.subgroups.map(subgroupLabel).join(', ')
  }
  if (lesson.groups.length > 1) return lesson.groups.join(', ')
  return null
}

export function roomLabel(lesson: LessonView): string | null {
  if (lesson.rooms.length === 0) return null
  return lesson.rooms.map((room) => `ауд. ${room.number}`).join(', ')
}

/** Другий рядок біля аудиторії: поверх (корпус уже стоїть у першому рядку). */
export function placeLabel(lesson: LessonView): string | null {
  const room = lesson.rooms[0]
  if (!room || room.floor === null) return null
  return `${room.floor} поверх`
}

export function teacherLabel(lesson: LessonView): string | null {
  if (lesson.teachers.length === 0) return null
  return lesson.teachers.map((teacher) => teacher.short_name).join(', ')
}
