import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router-dom'

import { publicApi } from '../api/endpoints'
import type {
  CalendarInfo,
  DayView,
  GroupOption,
  LessonTypeOption,
  Parity,
  RoomOption,
  SubgroupOption,
  TeacherOption,
  WeekView,
} from '../api/types'
import { DayStrip } from '../components/DayStrip'
import { EmptyState, ErrorAlert, Skeletons } from '../components/Feedback'
import { Layout } from '../components/Layout'
import { LessonCard } from '../components/LessonCard'
import { Segmented } from '../components/Segmented'
import { WeekGrid } from '../components/WeekGrid'
import {
  addDays,
  formatDayMonth,
  formatLongDate,
  isoWeekday,
  mondayOf,
  todayISO,
  weekDates,
} from '../lib/dates'
import { sortLessonTypes, subgroupShort, typeToken } from '../lib/lessons'

type TargetKind = 'group' | 'teacher' | 'room'
type Scope = 'day' | 'week'

interface TargetOption {
  id: number
  label: string
  hint?: string
}

const KIND_OPTIONS = [
  { value: 'group' as const, label: 'Група' },
  { value: 'teacher' as const, label: 'Викладач' },
  { value: 'room' as const, label: 'Аудиторія' },
]

const SCOPE_OPTIONS = [
  { value: 'day' as const, label: 'Розклад на день' },
  { value: 'week' as const, label: 'На весь тиждень' },
]

const PARITY_OPTIONS = [
  { value: 'ODD' as const, label: 'I Непарний' },
  { value: 'EVEN' as const, label: 'II Парний' },
]

const STORAGE_KEY = 'rozklad.lastTarget'

function readStoredTarget(): { kind: TargetKind; id: number } | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return null
    const parsed = JSON.parse(raw) as { kind?: string; id?: number }
    if (!parsed.id || !parsed.kind) return null
    if (parsed.kind !== 'group' && parsed.kind !== 'teacher' && parsed.kind !== 'room') return null
    return { kind: parsed.kind, id: parsed.id }
  } catch {
    return null
  }
}

function storeTarget(kind: TargetKind, id: number): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ kind, id }))
  } catch {
    /* сховище може бути недоступним — тоді просто не запам'ятовуємо */
  }
}

export function SchedulePage() {
  const [params, setParams] = useSearchParams()

  const stored = useMemo(() => readStoredTarget(), [])
  const kind = (params.get('kind') as TargetKind | null) ?? stored?.kind ?? 'group'
  const targetId = Number(params.get('id') ?? 0) || null
  const date = params.get('date') ?? todayISO()
  const scope = (params.get('scope') as Scope | null) ?? 'day'
  const subgroupId = Number(params.get('subgroup') ?? 0) || null

  const [options, setOptions] = useState<TargetOption[]>([])
  const [optionsError, setOptionsError] = useState<string | null>(null)
  const [subgroups, setSubgroups] = useState<SubgroupOption[]>([])
  const [lessonTypes, setLessonTypes] = useState<LessonTypeOption[]>([])
  const [calendar, setCalendar] = useState<CalendarInfo | null>(null)
  const [day, setDay] = useState<DayView | null>(null)
  const [week, setWeek] = useState<WeekView | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const updateParams = useCallback(
    (patch: Record<string, string | null>) => {
      const next = new URLSearchParams(params)
      for (const [key, value] of Object.entries(patch)) {
        if (value === null) next.delete(key)
        else next.set(key, value)
      }
      setParams(next, { replace: true })
    },
    [params, setParams],
  )

  // Довідник для селектора залежно від того, чий розклад дивляться.
  useEffect(() => {
    let active = true
    setOptionsError(null)

    const load = async (): Promise<TargetOption[]> => {
      if (kind === 'teacher') {
        const teachers: TeacherOption[] = await publicApi.teachers()
        return teachers.map((teacher) => ({
          id: teacher.id,
          label: teacher.short_name,
          hint: teacher.department_names[0],
        }))
      }
      if (kind === 'room') {
        const rooms: RoomOption[] = await publicApi.rooms()
        return rooms.map((room) => ({
          id: room.id,
          label: room.number,
          hint: room.building_name,
        }))
      }
      const groups: GroupOption[] = await publicApi.groups()
      return groups.map((group) => ({ id: group.id, label: group.name }))
    }

    load()
      .then((loaded) => {
        if (active) setOptions(loaded)
      })
      .catch((cause: Error) => {
        if (active) setOptionsError(cause.message)
      })

    return () => {
      active = false
    }
  }, [kind])

  // Якщо в адресі немає (або є неіснуючий) обʼєкт — беремо запамʼятований або перший.
  useEffect(() => {
    if (options.length === 0) return
    if (options.some((option) => option.id === targetId)) return
    const preferred = stored?.kind === kind ? stored.id : null
    const next = options.find((option) => option.id === preferred)?.id ?? options[0].id
    updateParams({ id: String(next) })
  }, [options, targetId, kind, stored, updateParams])

  useEffect(() => {
    publicApi
      .lessonTypes()
      .then((types) => setLessonTypes(sortLessonTypes(types)))
      .catch(() => setLessonTypes([]))
  }, [])

  useEffect(() => {
    if (kind !== 'group' || targetId === null) {
      setSubgroups([])
      return
    }
    let active = true
    publicApi
      .subgroups(targetId)
      .then((loaded) => {
        if (active) setSubgroups(loaded)
      })
      .catch(() => {
        if (active) setSubgroups([])
      })
    return () => {
      active = false
    }
  }, [kind, targetId])

  useEffect(() => {
    let active = true
    publicApi
      .calendar(date)
      .then((info) => {
        if (active) setCalendar(info)
      })
      .catch(() => {
        if (active) setCalendar(null)
      })
    return () => {
      active = false
    }
  }, [date])

  useEffect(() => {
    if (targetId === null) {
      setLoading(false)
      return
    }
    let active = true
    setLoading(true)
    setError(null)

    const load = async (): Promise<{ day: DayView | null; week: WeekView | null }> => {
      if (scope === 'week') {
        const loaded =
          kind === 'teacher'
            ? await publicApi.teacherWeek(targetId, date)
            : kind === 'room'
              ? await publicApi.roomWeek(targetId, date)
              : await publicApi.groupWeek(targetId, date, subgroupId)
        return { day: null, week: loaded }
      }
      const loaded =
        kind === 'teacher'
          ? await publicApi.teacherDay(targetId, date)
          : kind === 'room'
            ? await publicApi.roomDay(targetId, date)
            : await publicApi.groupDay(targetId, date, subgroupId)
      return { day: loaded, week: null }
    }

    load()
      .then((result) => {
        if (!active) return
        setDay(result.day)
        setWeek(result.week)
        storeTarget(kind, targetId)
      })
      .catch((cause: Error) => {
        if (active) setError(cause.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [kind, targetId, date, scope, subgroupId])

  const parity: Parity | null = calendar?.parity ?? null

  // Пн-Пт завжди; субота й неділя — лише якщо того дня справді є пари
  // (робоча субота, перенесення) або користувач саме на них дивиться.
  const weekdays = useMemo(() => {
    const base = weekDates(date, 5)
    const weekend = (week?.days ?? [])
      .filter((item) => item.day_of_week > 5 && item.lessons.length > 0)
      .map((item) => item.day)
    const current = isoWeekday(date) > 5 ? [date] : []
    return [...new Set([...base, ...weekend, ...current])].sort()
  }, [date, week])
  const currentTarget = options.find((option) => option.id === targetId)

  const emptyDates = useMemo(() => {
    const empty = new Set<string>()
    for (const item of week?.days ?? []) {
      if (item.lessons.length === 0) empty.add(item.day)
    }
    return empty
  }, [week])

  /** Парність — властивість тижня, тож перемикач зсуває дату на сусідній тиждень. */
  const switchParity = (next: Parity) => {
    if (parity === null || next === parity) return
    const forward = addDays(date, 7)
    const backward = addDays(date, -7)
    const semesterEnd = calendar?.semester_end
    const withinSemester = semesterEnd === null || semesterEnd === undefined || forward <= semesterEnd
    updateParams({ date: withinSemester ? forward : backward })
  }

  const subgroupOptions = [
    { value: 0, label: 'Вся' },
    ...subgroups.map((subgroup) => ({ value: subgroup.id, label: subgroupShort(subgroup.name) })),
  ]

  const headerRight = (
    <span className="chip">
      {calendar?.is_working ? <span className="dot" /> : null}
      {formatLongDate(date)}
      {calendar?.week_number ? ` • ${calendar.week_number}-й тижд.` : ''}
    </span>
  )

  const toolbar = (
    <>
      <div className="page toolbar__row">
        <div className="field">
          <Segmented
            options={KIND_OPTIONS}
            value={kind}
            ariaLabel="Чий розклад"
            onChange={(next) => updateParams({ kind: next, id: null, subgroup: null })}
          />
          <label className="field" htmlFor="target-select">
            {kind === 'group' ? 'Група:' : kind === 'teacher' ? 'Викладач:' : 'Аудиторія:'}
            <select
              id="target-select"
              className="select"
              value={targetId ?? ''}
              onChange={(event) => updateParams({ id: event.target.value, subgroup: null })}
            >
              {options.length === 0 ? <option value="">—</option> : null}
              {options.map((option) => (
                <option key={option.id} value={option.id}>
                  {option.label}
                  {option.hint ? ` · ${option.hint}` : ''}
                </option>
              ))}
            </select>
          </label>

          {kind === 'group' && subgroups.length > 0 ? (
            <Segmented
              options={subgroupOptions}
              value={subgroupId ?? 0}
              ariaLabel="Підгрупа"
              onChange={(next) => updateParams({ subgroup: next === 0 ? null : String(next) })}
            />
          ) : null}
        </div>

        <div className="field">
          Тиждень:
          <Segmented
            options={PARITY_OPTIONS}
            value={parity === 'EVEN' ? 'EVEN' : 'ODD'}
            ariaLabel="Парність тижня"
            dark
            onChange={switchParity}
          />
        </div>
      </div>

      <div className="page toolbar__row">
        <div className="field">
          <Segmented
            options={SCOPE_OPTIONS}
            value={scope}
            ariaLabel="Режим перегляду"
            onChange={(next) => updateParams({ scope: next })}
          />
          <button
            type="button"
            className="btn btn--small"
            onClick={() => updateParams({ date: todayISO() })}
          >
            Сьогодні
          </button>
          <button
            type="button"
            className="btn btn--small"
            onClick={() => updateParams({ date: addDays(mondayOf(date), -7) })}
            title="Попередній тиждень"
          >
            ←
          </button>
          <button
            type="button"
            className="btn btn--small"
            onClick={() => updateParams({ date: addDays(mondayOf(date), 7) })}
            title="Наступний тиждень"
          >
            →
          </button>
        </div>

        <div className="legend">
          {lessonTypes.map((type) => (
            <span key={type.id} className="legend__item">
              <span
                className="legend__dot"
                style={{ background: `var(--type-${typeToken(type.code)})` }}
              />
              {type.name}
            </span>
          ))}
        </div>
      </div>

      <div className="page">
        <DayStrip
          dates={weekdays}
          value={date}
          emptyDates={scope === 'week' ? emptyDates : undefined}
          onChange={(next) => updateParams({ date: next, scope: 'day' })}
        />
      </div>
    </>
  )

  return (
    <Layout headerRight={headerRight} toolbar={toolbar}>
      <div className="content__head">
        <p className="content__title">
          {scope === 'day' ? 'Розклад: ' : 'Тиждень: '}
          <strong>
            {scope === 'day'
              ? formatLongDate(date)
              : `${formatDayMonth(weekdays[0])} – ${formatDayMonth(weekdays[weekdays.length - 1])}`}
          </strong>
        </p>
        <p>
          {currentTarget ? <strong>{currentTarget.label}</strong> : '—'}
          {parity ? ` · ${parity === 'ODD' ? 'I Непарний' : 'II Парний'}` : ''}
          {calendar?.semester_name ? ` · ${calendar.semester_name}` : ''}
        </p>
      </div>

      {optionsError ? <ErrorAlert message={optionsError} /> : null}
      {error ? <ErrorAlert message={error} /> : null}

      {loading ? (
        <Skeletons />
      ) : scope === 'week' ? (
        week && week.days.length > 0 ? (
          <WeekGrid
            days={week.days}
            onPickDay={(picked) => updateParams({ date: picked, scope: 'day' })}
          />
        ) : (
          <EmptyState
            title="Розкладу на цей тиждень немає"
            description="Можливо, тиждень поза межами семестру або заняття ще не внесені."
          />
        )
      ) : day && !day.is_working ? (
        <EmptyState
          title={day.closed_reason ?? 'Навчання немає'}
          description="Цього дня занять не заплановано."
        />
      ) : day && day.lessons.length > 0 ? (
        <div className="lessons">
          {day.lessons.map((lesson) => (
            <LessonCard
              key={`${lesson.entry_id}-${lesson.pair_number}-${lesson.status}`}
              lesson={lesson}
              day={day.day}
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title="Пар немає"
          description={
            currentTarget
              ? `Для «${currentTarget.label}» цього дня занять не знайдено.`
              : 'Оберіть групу, викладача або аудиторію.'
          }
        />
      )}
    </Layout>
  )
}
