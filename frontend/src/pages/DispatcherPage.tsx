import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, Navigate } from 'react-router-dom'

import { adminApi, publicApi } from '../api/endpoints'
import type {
  DayView,
  GroupOption,
  LessonTypeOption,
  LessonView,
  PairTimeOption,
  RoomOption,
  ScheduleEntry,
  SemesterOption,
  StreamOption,
  SubgroupOption,
  SubjectOption,
  TeacherOption,
} from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { DayStrip } from '../components/DayStrip'
import { EmptyState, ErrorAlert, Skeletons } from '../components/Feedback'
import { ExceptionForm } from '../components/ExceptionForm'
import { Layout } from '../components/Layout'
import { LessonCard } from '../components/LessonCard'
import { LessonForm } from '../components/LessonForm'
import { addDays, formatLongDate, isoWeekday, mondayOf, todayISO, weekDates } from '../lib/dates'
import { sortLessonTypes } from '../lib/lessons'

interface Refs {
  subjects: SubjectOption[]
  lessonTypes: LessonTypeOption[]
  times: PairTimeOption[]
  teachers: TeacherOption[]
  rooms: RoomOption[]
  groups: GroupOption[]
  streams: StreamOption[]
}

const EMPTY_REFS: Refs = {
  subjects: [],
  lessonTypes: [],
  times: [],
  teachers: [],
  rooms: [],
  groups: [],
  streams: [],
}

export function DispatcherPage() {
  const { user, loading: authLoading, can } = useAuth()

  const [refs, setRefs] = useState<Refs>(EMPTY_REFS)
  const [subgroups, setSubgroups] = useState<SubgroupOption[]>([])
  const [semesters, setSemesters] = useState<SemesterOption[]>([])
  const [semesterId, setSemesterId] = useState<number | null>(null)
  const [groupId, setGroupId] = useState<number | null>(null)
  const [date, setDate] = useState(todayISO())
  const [day, setDay] = useState<DayView | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [reloadToken, setReloadToken] = useState(0)

  const [editing, setEditing] = useState<ScheduleEntry | null | 'new'>(null)
  const [changing, setChanging] = useState<LessonView | null>(null)

  const reload = useCallback(() => setReloadToken((value) => value + 1), [])

  useEffect(() => {
    if (!user) return
    let active = true
    Promise.all([
      adminApi.subjects(),
      publicApi.lessonTypes(),
      publicApi.times(),
      publicApi.teachers(),
      publicApi.rooms(),
      publicApi.groups(),
      adminApi.streams(),
      adminApi.semesters(),
    ])
      .then(([subjects, lessonTypes, times, teachers, rooms, groups, streams, semesterList]) => {
        if (!active) return
        setRefs({
          subjects,
          lessonTypes: sortLessonTypes(lessonTypes),
          times,
          teachers,
          rooms,
          groups,
          streams,
        })
        setSemesters(semesterList)
        setGroupId((current) => current ?? groups[0]?.id ?? null)
        setSemesterId((current) => current ?? semesterList[semesterList.length - 1]?.id ?? null)
      })
      .catch((cause: Error) => {
        if (active) setError(cause.message)
      })
    return () => {
      active = false
    }
  }, [user])

  useEffect(() => {
    if (groupId === null) {
      setSubgroups([])
      return
    }
    let active = true
    publicApi
      .subgroups(groupId)
      .then((loaded) => {
        if (active) setSubgroups(loaded)
      })
      .catch(() => {
        if (active) setSubgroups([])
      })
    return () => {
      active = false
    }
  }, [groupId])

  useEffect(() => {
    if (groupId === null) return
    let active = true
    setLoading(true)
    setError(null)
    publicApi
      .groupDay(groupId, date)
      .then((loaded) => {
        if (active) setDay(loaded)
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
  }, [groupId, date, reloadToken])

  const weekdays = useMemo(() => weekDates(date, 6), [date])
  const canEdit = can('schedule.edit')
  const canCreate = can('schedule.create')
  const canDelete = can('schedule.delete')
  const canChange = can('schedule.cancel') || can('schedule.move') || canEdit

  /** Семестр і дата мають збігатися, інакше диспетчер редагує «не той» тиждень. */
  const pickSemester = (nextId: number) => {
    setSemesterId(nextId)
    const semester = semesters.find((item) => item.id === nextId)
    if (!semester) return
    if (date < semester.start_date || date > semester.end_date) {
      const today = todayISO()
      const inside = today >= semester.start_date && today <= semester.end_date
      setDate(inside ? today : semester.start_date)
    }
  }

  const removeEntry = async (entryId: number) => {
    if (!window.confirm('Видалити заняття з розкладу? Дію буде записано в журнал.')) return
    try {
      await adminApi.deleteEntry(entryId)
      setNotice('Заняття видалено')
      reload()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не вдалося видалити заняття')
    }
  }

  const openEditor = async (entryId: number) => {
    try {
      setEditing(await adminApi.entry(entryId))
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не вдалося відкрити заняття')
    }
  }

  if (authLoading) {
    return (
      <Layout>
        <Skeletons />
      </Layout>
    )
  }

  if (!user) return <Navigate to="/login" replace />

  const toolbar = (
    <>
      <div className="page toolbar__row">
        <div className="field">
          <label className="field" htmlFor="semester">
            Семестр:
            <select
              id="semester"
              className="select"
              value={semesterId ?? ''}
              onChange={(event) => pickSemester(Number(event.target.value))}
            >
              {semesters.length === 0 ? <option value="">—</option> : null}
              {semesters.map((semester) => (
                <option key={semester.id} value={semester.id}>
                  {semester.name} ({semester.start_date.slice(0, 4)})
                </option>
              ))}
            </select>
          </label>

          <label className="field" htmlFor="group">
            Група:
            <select
              id="group"
              className="select"
              value={groupId ?? ''}
              onChange={(event) => setGroupId(Number(event.target.value))}
            >
              {refs.groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
          </label>
        </div>

        <div className="field">
          <Link className="btn btn--small" to="/export">
            Експорт Excel
          </Link>
          {can('audit.view') ? (
            <Link className="btn btn--small" to="/audit">
              Журнал аудиту
            </Link>
          ) : null}
          <button
            type="button"
            className="btn btn--small btn--primary"
            disabled={!canCreate || semesterId === null}
            onClick={() => setEditing('new')}
          >
            + Заняття
          </button>
        </div>
      </div>

      <div className="page toolbar__row">
        <div className="field">
          <button type="button" className="btn btn--small" onClick={() => setDate(todayISO())}>
            Сьогодні
          </button>
          <button
            type="button"
            className="btn btn--small"
            title="Попередній тиждень"
            onClick={() => setDate(addDays(mondayOf(date), -7))}
          >
            ←
          </button>
          <button
            type="button"
            className="btn btn--small"
            title="Наступний тиждень"
            onClick={() => setDate(addDays(mondayOf(date), 7))}
          >
            →
          </button>
        </div>
      </div>

      <div className="page">
        <DayStrip dates={weekdays} value={date} onChange={setDate} />
      </div>
    </>
  )

  return (
    <Layout
      toolbar={toolbar}
      headerRight={<span className="chip chip--muted">{user.full_name}</span>}
    >
      <div className="content__head">
        <p className="content__title">
          Редагування: <strong>{formatLongDate(date)}</strong>
        </p>
        <p>
          {day?.week_number ? `${day.week_number}-й тиждень · ` : ''}
          {day?.parity === 'EVEN' ? 'II Парний' : day?.parity === 'ODD' ? 'I Непарний' : ''}
          {day?.semester_name ? ` · ${day.semester_name}` : ''}
        </p>
      </div>

      {error ? <ErrorAlert message={error} /> : null}
      {notice ? <p className="alert alert--info">{notice}</p> : null}
      {!canCreate && !canEdit ? (
        <p className="alert alert--warning">
          У вашій ролі немає прав на зміну розкладу — доступний лише перегляд.
        </p>
      ) : null}

      {loading ? (
        <Skeletons />
      ) : day && !day.is_working ? (
        <EmptyState title={day.closed_reason ?? 'Навчання немає'} />
      ) : day && day.lessons.length > 0 ? (
        <div className="lessons">
          {day.lessons.map((lesson) => (
            <LessonCard
              key={`${lesson.entry_id}-${lesson.pair_number}-${lesson.status}`}
              lesson={lesson}
              day={day.day}
              actions={
                <>
                  <button
                    type="button"
                    className="btn btn--small"
                    disabled={!canEdit}
                    onClick={() => openEditor(lesson.entry_id)}
                  >
                    Редагувати
                  </button>
                  <button
                    type="button"
                    className="btn btn--small"
                    disabled={!canChange}
                    onClick={() => setChanging(lesson)}
                  >
                    Заміна / перенесення
                  </button>
                  <button
                    type="button"
                    className="btn btn--small btn--danger"
                    disabled={!canDelete}
                    onClick={() => removeEntry(lesson.entry_id)}
                  >
                    Видалити
                  </button>
                </>
              }
            />
          ))}
        </div>
      ) : (
        <EmptyState
          title="Цього дня пар немає"
          description="Додайте заняття кнопкою «+ Заняття» або оберіть інший день."
        />
      )}

      {editing !== null && semesterId !== null ? (
        <LessonForm
          refs={{ ...refs, subgroups }}
          semesterId={semesterId}
          entry={editing === 'new' ? null : editing}
          defaults={{ dayOfWeek: isoWeekday(date), groupId }}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null)
            setNotice('Зміни збережено')
            reload()
          }}
        />
      ) : null}

      {changing !== null ? (
        <ExceptionForm
          lesson={changing}
          date={date}
          teachers={refs.teachers}
          rooms={refs.rooms}
          times={refs.times}
          onClose={() => setChanging(null)}
          onSaved={() => {
            setChanging(null)
            setNotice('Зміну збережено')
            reload()
          }}
        />
      ) : null}
    </Layout>
  )
}
