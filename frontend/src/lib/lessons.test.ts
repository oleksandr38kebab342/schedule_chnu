import { describe, expect, it } from 'vitest'

import type { LessonView } from '../api/types'
import { audienceLabel, statusBadge, statusNote, subgroupLabel, typeToken } from './lessons'

function lesson(over: Partial<LessonView> = {}): LessonView {
  return {
    entry_id: 1,
    pair_number: 2,
    pair_label: null,
    starts_at: '10:25:00',
    ends_at: '12:00:00',
    day_of_week: 3,
    week_parity: 'BOTH',
    subject_name: 'Архітектура програмного забезпечення',
    subject_short: 'Архітектура ПЗ',
    lesson_type_code: 'LEC',
    lesson_type_name: 'Лекція',
    lesson_type_short: 'Лк',
    teachers: [],
    rooms: [],
    groups: ['КН-321'],
    subgroups: [],
    streams: [],
    note: null,
    status: 'NORMAL',
    change_reason: null,
    moved_to: null,
    moved_from: null,
    ...over,
  }
}

describe('представлення заняття', () => {
  it('розпізнає типи занять і дає запасний колір невідомому', () => {
    expect(typeToken('LEC')).toBe('lec')
    expect(typeToken('lab')).toBe('lab')
    expect(typeToken('CONSULT')).toBe('other')
  })

  it('показує, кому читається пара', () => {
    expect(audienceLabel(lesson({ streams: ['КН-3'] }))).toBe('Потік КН-3')
    expect(audienceLabel(lesson({ subgroups: ['1'] }))).toBe('1-а підгрупа')
    expect(audienceLabel(lesson({ groups: ['КН-321', 'КН-322'] }))).toBe('КН-321, КН-322')
    // Одна група — підпис зайвий, він уже є у фільтрі.
    expect(audienceLabel(lesson())).toBeNull()
  })

  it('називає підгрупу природно', () => {
    expect(subgroupLabel('1')).toBe('1-а підгрупа')
    expect(subgroupLabel('Б')).toBe('Б')
  })

  it('позначає заміну викладача окремим бейджем', () => {
    const replaced = lesson({
      status: 'REPLACED',
      teachers: [
        {
          id: 2,
          full_name: 'Коваленко Оксана Миколаївна',
          short_name: 'доц. Коваленко О. М.',
          degree: null,
          position: null,
          is_substitute: true,
        },
      ],
    })
    expect(statusBadge(replaced)).toEqual({ label: 'Заміна викладача', tone: 'danger' })
    expect(statusBadge(lesson({ status: 'CANCELLED' }))?.label).toBe('Скасовано')
    expect(statusBadge(lesson())).toBeNull()
  })

  it('пояснює перенесення датою і причиною', () => {
    const moved = lesson({
      status: 'MOVED_OUT',
      moved_to: '2026-10-24',
      change_reason: 'Робоча субота',
    })
    expect(statusNote(moved, () => '24 жовтня')).toBe('перенесено на 24 жовтня · Робоча субота')
    expect(statusNote(lesson(), () => '')).toBeNull()
  })
})
