/** Робота з датами в локальному часі користувача (без UTC-зсувів). */

export const DAY_NAMES_SHORT = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Нд']
export const DAY_NAMES = [
  'Понеділок',
  'Вівторок',
  'Середа',
  'Четвер',
  "П'ятниця",
  'Субота',
  'Неділя',
]
const MONTHS_GENITIVE = [
  'січня',
  'лютого',
  'березня',
  'квітня',
  'травня',
  'червня',
  'липня',
  'серпня',
  'вересня',
  'жовтня',
  'листопада',
  'грудня',
]

/** YYYY-MM-DD за локальним часом: toISOString() зсунув би дату на межі доби. */
export function toISODate(date: Date): string {
  const month = `${date.getMonth() + 1}`.padStart(2, '0')
  const day = `${date.getDate()}`.padStart(2, '0')
  return `${date.getFullYear()}-${month}-${day}`
}

export function parseISODate(value: string): Date {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, (month ?? 1) - 1, day ?? 1)
}

export function todayISO(now: Date = new Date()): string {
  return toISODate(now)
}

export function addDays(value: string, days: number): string {
  const date = parseISODate(value)
  date.setDate(date.getDate() + days)
  return toISODate(date)
}

/** 1 = понеділок … 7 = неділя (як day_of_week у бекенді). */
export function isoWeekday(value: string): number {
  const weekday = parseISODate(value).getDay()
  return weekday === 0 ? 7 : weekday
}

export function mondayOf(value: string): string {
  return addDays(value, -(isoWeekday(value) - 1))
}

export function weekDates(value: string, length = 5): string[] {
  const monday = mondayOf(value)
  return Array.from({ length }, (_, index) => addDays(monday, index))
}

/** «15 жовтня» — як у шапці референсного макета. */
export function formatDayMonth(value: string): string {
  const date = parseISODate(value)
  return `${date.getDate()} ${MONTHS_GENITIVE[date.getMonth()]}`
}

/** «Середа, 15 жовтня» */
export function formatLongDate(value: string): string {
  return `${DAY_NAMES[isoWeekday(value) - 1]}, ${formatDayMonth(value)}`
}

export function formatShortDate(value: string): string {
  const date = parseISODate(value)
  return `${`${date.getDate()}`.padStart(2, '0')}.${`${date.getMonth() + 1}`.padStart(2, '0')}`
}

/** «08:30» з «08:30:00» — бекенд віддає час у форматі ISO. */
export function formatTime(value: string): string {
  return value.slice(0, 5)
}

export function minutesOfDay(time: string): number {
  const [hours, minutes] = time.split(':').map(Number)
  return (hours ?? 0) * 60 + (minutes ?? 0)
}

/** Чи триває пара саме зараз (однакова дата й час у межах пари). */
export function isHappeningNow(
  day: string,
  startsAt: string,
  endsAt: string,
  now: Date = new Date(),
): boolean {
  if (day !== toISODate(now)) return false
  const current = now.getHours() * 60 + now.getMinutes()
  return current >= minutesOfDay(startsAt) && current < minutesOfDay(endsAt)
}
