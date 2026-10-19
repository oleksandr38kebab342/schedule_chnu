import { render, screen, waitFor, within } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { AuthProvider } from '../auth/AuthContext'
import { SchedulePage } from './SchedulePage'

const DAY = '2026-10-21'

const dayPayload = {
  day: DAY,
  day_of_week: 3,
  semester_id: 1,
  semester_name: 'I семестр',
  week_number: 8,
  parity: 'EVEN',
  is_working: true,
  closed_reason: null,
  lessons: [
    {
      entry_id: 1,
      pair_number: 1,
      pair_label: null,
      starts_at: '08:30:00',
      ends_at: '10:05:00',
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
        { id: 1, number: 'А.402', building_code: 'A', building_name: 'Головний корпус', floor: 4 },
      ],
      groups: [],
      subgroups: [],
      streams: ['КН-3'],
      note: null,
      status: 'NORMAL',
      change_reason: null,
      moved_to: null,
      moved_from: null,
    },
  ],
}

const routes: Record<string, unknown> = {
  '/public/groups': [
    {
      id: 1,
      name: 'КН-321',
      course: 3,
      department_id: 1,
      department_name: "Кафедра комп'ютерних наук",
      faculty_id: 1,
      faculty_name: 'ФМІ',
      faculty_short_name: 'ФМІ',
    },
  ],
  '/public/groups/1/subgroups': [
    { id: 1, group_id: 1, name: '1' },
    { id: 2, group_id: 1, name: '2' },
  ],
  '/public/lesson-types': [{ id: 1, code: 'LEC', name: 'Лекція', short_name: 'Лк' }],
  '/public/calendar': {
    day: DAY,
    semester_id: 1,
    semester_name: 'I семестр',
    semester_start: '2026-09-01',
    semester_end: '2027-01-10',
    week_number: 8,
    parity: 'EVEN',
    week_starts_on: '2026-10-19',
    week_ends_on: '2026-10-25',
    is_working: true,
    closed_reason: null,
  },
  '/public/schedule/group/1/day': dayPayload,
}

function mockFetch() {
  return vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(String(input), 'http://localhost')
    const body = routes[url.pathname.replace('/api/v1', '')]
    if (body === undefined) {
      return new Response(JSON.stringify({ detail: `Немає мока для ${url.pathname}` }), {
        status: 404,
        headers: { 'Content-Type': 'application/json' },
      })
    }
    return new Response(JSON.stringify(body), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  })
}

function renderPage() {
  return render(
    <MemoryRouter initialEntries={[`/?kind=group&id=1&date=${DAY}&scope=day`]}>
      <AuthProvider>
        <SchedulePage />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('сторінка розкладу', () => {
  beforeEach(() => {
    vi.stubGlobal('fetch', mockFetch())
    localStorage.clear()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('показує пари обраного дня з даними з API', async () => {
    renderPage()

    expect(await screen.findByText('Архітектура програмного забезпечення')).toBeInTheDocument()
    expect(screen.getByText('08:30 – 10:05')).toBeInTheDocument()
    expect(screen.getByText('Потік КН-3')).toBeInTheDocument()
  })

  it('виводить у шапці дату, номер тижня і парність', async () => {
    renderPage()

    // Дата є і в шапці, і в заголовку списку — звужуємо пошук до шапки.
    const header = within(await screen.findByRole('banner'))
    await waitFor(() => expect(header.getByText(/Середа, 21 жовтня/)).toBeInTheDocument())
    expect(header.getByText(/8-й тижд\./)).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Парність тижня' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'II Парний' })).toHaveAttribute(
      'aria-pressed',
      'true',
    )
  })

  it('дає перемкнути підгрупу й показує дні тижня', async () => {
    renderPage()

    await screen.findByText('Архітектура програмного забезпечення')
    expect(screen.getByRole('button', { name: '1 підгр.' })).toBeInTheDocument()
    expect(screen.getByRole('group', { name: 'Підгрупа' })).toBeInTheDocument()
    expect(screen.getAllByRole('button', { name: /Ср/ })).toHaveLength(1)
  })
})
