import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { LessonView } from '../api/types'
import { LessonCard } from './LessonCard'

const DAY = '2026-10-21'

function lesson(over: Partial<LessonView> = {}): LessonView {
  return {
    entry_id: 7,
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
    teachers: [
      {
        id: 1,
        full_name: 'Мельник Василь Петрович',
        short_name: 'проф. Мельник В. П.',
        degree: null,
        position: null,
        is_substitute: false,
      },
    ],
    rooms: [
      {
        id: 1,
        number: 'А.402',
        building_code: 'A',
        building_name: 'Головний корпус',
        floor: 4,
      },
    ],
    groups: ['КН-321'],
    subgroups: [],
    streams: ['КН-3'],
    note: null,
    status: 'NORMAL',
    change_reason: null,
    moved_to: null,
    moved_from: null,
    ...over,
  }
}

describe('картка пари', () => {
  it('показує час, тип, викладача, аудиторію і потік', () => {
    render(<LessonCard lesson={lesson()} day={DAY} now={new Date(2026, 9, 21, 9, 0)} />)

    expect(screen.getByText('Архітектура програмного забезпечення')).toBeInTheDocument()
    expect(screen.getByText('10:25 – 12:00')).toBeInTheDocument()
    expect(screen.getByText('Лекція')).toBeInTheDocument()
    expect(screen.getByText('проф. Мельник В. П.')).toBeInTheDocument()
    expect(screen.getByText(/ауд\. А\.402/)).toBeInTheDocument()
    expect(screen.getByText('4 поверх')).toBeInTheDocument()
    expect(screen.getByText('Потік КН-3')).toBeInTheDocument()
  })

  it('підсвічує пару, яка триває просто зараз', () => {
    const { container } = render(
      <LessonCard lesson={lesson()} day={DAY} now={new Date(2026, 9, 21, 11, 0)} />,
    )
    expect(screen.getByText('Зараз іде')).toBeInTheDocument()
    expect(container.querySelector('.lesson--now')).not.toBeNull()
  })

  it('не підсвічує скасовану пару навіть у її час', () => {
    const { container } = render(
      <LessonCard
        lesson={lesson({ status: 'CANCELLED', change_reason: 'Карантин' })}
        day={DAY}
        now={new Date(2026, 9, 21, 11, 0)}
      />,
    )
    expect(screen.queryByText('Зараз іде')).toBeNull()
    expect(screen.getByText('Скасовано')).toBeInTheDocument()
    expect(screen.getByText('Карантин')).toBeInTheDocument()
    expect(container.querySelector('.lesson--cancelled')).not.toBeNull()
  })

  it('позначає заміну викладача', () => {
    render(
      <LessonCard
        lesson={lesson({
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
        })}
        day={DAY}
      />,
    )
    expect(screen.getByText('Заміна викладача')).toBeInTheDocument()
    expect(screen.getByText('заміна:')).toBeInTheDocument()
    expect(screen.getByText('доц. Коваленко О. М.')).toBeInTheDocument()
  })
})
