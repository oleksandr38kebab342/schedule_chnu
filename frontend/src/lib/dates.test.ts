import { describe, expect, it } from 'vitest'

import {
  addDays,
  formatLongDate,
  isHappeningNow,
  isoWeekday,
  mondayOf,
  toISODate,
  weekDates,
} from './dates'

describe('дати розкладу', () => {
  it('формує ISO-дату за локальним часом, а не за UTC', () => {
    // 23:30 за локальним часом: toISOString() віддав би наступну добу.
    expect(toISODate(new Date(2026, 9, 21, 23, 30))).toBe('2026-10-21')
  })

  it('рахує день тижня як 1=Пн…7=Нд', () => {
    expect(isoWeekday('2026-10-19')).toBe(1)
    expect(isoWeekday('2026-10-25')).toBe(7)
  })

  it('знаходить понеділок тижня і перелік днів', () => {
    expect(mondayOf('2026-10-21')).toBe('2026-10-19')
    expect(weekDates('2026-10-21', 5)).toEqual([
      '2026-10-19',
      '2026-10-20',
      '2026-10-21',
      '2026-10-22',
      '2026-10-23',
    ])
  })

  it('переходить через межу місяця', () => {
    expect(addDays('2026-10-31', 1)).toBe('2026-11-01')
    expect(addDays('2026-01-01', -1)).toBe('2025-12-31')
  })

  it('підписує дату українською', () => {
    expect(formatLongDate('2026-10-21')).toBe('Середа, 21 жовтня')
  })

  it('визначає, чи пара триває просто зараз', () => {
    const during = new Date(2026, 9, 21, 10, 40)
    expect(isHappeningNow('2026-10-21', '10:25:00', '12:00:00', during)).toBe(true)
    expect(isHappeningNow('2026-10-21', '12:20:00', '13:55:00', during)).toBe(false)
    // Той самий час, але інший день — пара не йде.
    expect(isHappeningNow('2026-10-22', '10:25:00', '12:00:00', during)).toBe(false)
  })

  it('не вважає пару активною рівно в момент завершення', () => {
    const atEnd = new Date(2026, 9, 21, 12, 0)
    expect(isHappeningNow('2026-10-21', '10:25:00', '12:00:00', atEnd)).toBe(false)
  })
})
