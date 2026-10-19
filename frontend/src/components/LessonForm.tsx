import { useEffect, useRef, useState } from 'react'

import { adminApi } from '../api/endpoints'
import type {
  Conflict,
  GroupOption,
  LessonTypeOption,
  PairTimeOption,
  Parity,
  RoomOption,
  ScheduleEntry,
  ScheduleEntryPayload,
  SubgroupOption,
  SubjectOption,
  TeacherOption,
} from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { conflictText, slotText } from '../lib/conflicts'
import { DAY_NAMES } from '../lib/dates'
import { Modal } from './Modal'
import { subgroupLabel } from '../lib/lessons'

export interface LessonFormRefs {
  subjects: SubjectOption[]
  lessonTypes: LessonTypeOption[]
  times: PairTimeOption[]
  teachers: TeacherOption[]
  rooms: RoomOption[]
  groups: GroupOption[]
  subgroups: SubgroupOption[]
  streams: { id: number; name: string }[]
}

interface LessonFormProps {
  refs: LessonFormRefs
  semesterId: number
  /** Заняття для редагування; порожньо — створюємо нове. */
  entry?: ScheduleEntry | null
  defaults?: { dayOfWeek: number; groupId: number | null }
  onClose: () => void
  onSaved: () => void
}

const PARITIES: { value: Parity; label: string }[] = [
  { value: 'BOTH', label: 'Щотижня' },
  { value: 'ODD', label: 'Непарний' },
  { value: 'EVEN', label: 'Парний' },
]

function numbers(values: readonly string[]): number[] {
  return values.map(Number).filter((value) => Number.isFinite(value) && value > 0)
}

function selected(event: React.ChangeEvent<HTMLSelectElement>): number[] {
  return numbers([...event.target.selectedOptions].map((option) => option.value))
}

export function LessonForm({
  refs,
  semesterId,
  entry,
  defaults,
  onClose,
  onSaved,
}: LessonFormProps) {
  const { can } = useAuth()
  const [form, setForm] = useState<ScheduleEntryPayload>(() => ({
    semester_id: semesterId,
    subject_id: entry?.subject_id ?? refs.subjects[0]?.id ?? 0,
    lesson_type_id: entry?.lesson_type_id ?? refs.lessonTypes[0]?.id ?? 0,
    pair_time_id: entry?.pair_time_id ?? refs.times[0]?.id ?? 0,
    day_of_week: entry?.day_of_week ?? defaults?.dayOfWeek ?? 1,
    week_parity: entry?.week_parity ?? 'BOTH',
    note: entry?.note ?? '',
    teacher_ids: entry?.teacher_ids ?? [],
    room_ids: entry?.room_ids ?? [],
    group_ids: entry?.group_ids ?? (defaults?.groupId ? [defaults.groupId] : []),
    subgroup_ids: entry?.subgroup_ids ?? [],
    stream_ids: entry?.stream_ids ?? [],
  }))
  const [conflicts, setConflicts] = useState<Conflict[]>([])
  const [overrideReason, setOverrideReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const conflictsRef = useRef<HTMLDivElement>(null)

  // Конфлікти зʼявляються внизу довгої форми — підводимо їх до очей.
  useEffect(() => {
    if (conflicts.length > 0) {
      conflictsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }, [conflicts])

  const blocking = conflicts.filter((conflict) => conflict.severity === 'ERROR')
  const canOverride = can('schedule.override_conflict')
  const slot = slotText(
    form.day_of_week,
    refs.times.find((time) => time.id === form.pair_time_id)?.number ?? null,
  )

  const patch = (changes: Partial<ScheduleEntryPayload>) =>
    setForm((previous) => ({ ...previous, ...changes }))

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const payload: ScheduleEntryPayload = {
        ...form,
        note: form.note?.trim() ? form.note.trim() : null,
        override_reason: overrideReason.trim() ? overrideReason.trim() : null,
      }
      const result = entry
        ? await adminApi.updateEntry(entry.id, payload)
        : await adminApi.createEntry(payload)

      setConflicts(result.conflicts)
      if (result.saved) {
        onSaved()
        return
      }
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не вдалося зберегти заняття')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={entry ? 'Редагування заняття' : 'Нове заняття'} onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <div className="form__grid">
          <div className="form__row">
            <label className="label" htmlFor="subject">
              Дисципліна
            </label>
            <select
              id="subject"
              className="select"
              value={form.subject_id}
              onChange={(event) => patch({ subject_id: Number(event.target.value) })}
            >
              {refs.subjects.map((subject) => (
                <option key={subject.id} value={subject.id}>
                  {subject.name}
                </option>
              ))}
            </select>
          </div>

          <div className="form__row">
            <label className="label" htmlFor="lesson-type">
              Тип заняття
            </label>
            <select
              id="lesson-type"
              className="select"
              value={form.lesson_type_id}
              onChange={(event) => patch({ lesson_type_id: Number(event.target.value) })}
            >
              {refs.lessonTypes.map((type) => (
                <option key={type.id} value={type.id}>
                  {type.name}
                </option>
              ))}
            </select>
          </div>

          <div className="form__row">
            <label className="label" htmlFor="day">
              День тижня
            </label>
            <select
              id="day"
              className="select"
              value={form.day_of_week}
              onChange={(event) => patch({ day_of_week: Number(event.target.value) })}
            >
              {DAY_NAMES.map((name, index) => (
                <option key={name} value={index + 1}>
                  {name}
                </option>
              ))}
            </select>
          </div>

          <div className="form__row">
            <label className="label" htmlFor="pair">
              Пара
            </label>
            <select
              id="pair"
              className="select"
              value={form.pair_time_id}
              onChange={(event) => patch({ pair_time_id: Number(event.target.value) })}
            >
              {refs.times.map((time) => (
                <option key={time.id} value={time.id}>
                  {time.number} · {time.starts_at.slice(0, 5)}–{time.ends_at.slice(0, 5)}
                </option>
              ))}
            </select>
          </div>

          <div className="form__row">
            <label className="label" htmlFor="parity">
              Тижні
            </label>
            <select
              id="parity"
              className="select"
              value={form.week_parity}
              onChange={(event) => patch({ week_parity: event.target.value as Parity })}
            >
              {PARITIES.map((parity) => (
                <option key={parity.value} value={parity.value}>
                  {parity.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="form__grid">
          <div className="form__row">
            <label className="label" htmlFor="teachers">
              Викладачі
            </label>
            <select
              id="teachers"
              className="select"
              multiple
              size={4}
              value={form.teacher_ids.map(String)}
              onChange={(event) => patch({ teacher_ids: selected(event) })}
            >
              {refs.teachers.map((teacher) => (
                <option key={teacher.id} value={teacher.id}>
                  {teacher.short_name}
                </option>
              ))}
            </select>
          </div>

          <div className="form__row">
            <label className="label" htmlFor="rooms">
              Аудиторії
            </label>
            <select
              id="rooms"
              className="select"
              multiple
              size={4}
              value={form.room_ids.map(String)}
              onChange={(event) => patch({ room_ids: selected(event) })}
            >
              {refs.rooms.map((room) => (
                <option key={room.id} value={room.id}>
                  {room.number} · {room.building_name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="form__grid">
          <div className="form__row">
            <label className="label" htmlFor="groups">
              Групи
            </label>
            <select
              id="groups"
              className="select"
              multiple
              size={4}
              value={form.group_ids.map(String)}
              onChange={(event) => patch({ group_ids: selected(event) })}
            >
              {refs.groups.map((group) => (
                <option key={group.id} value={group.id}>
                  {group.name}
                </option>
              ))}
            </select>
          </div>

          <div className="form__row">
            <label className="label" htmlFor="subgroups">
              Підгрупи
            </label>
            <select
              id="subgroups"
              className="select"
              multiple
              size={4}
              value={form.subgroup_ids.map(String)}
              onChange={(event) => patch({ subgroup_ids: selected(event) })}
            >
              {refs.subgroups.map((subgroup) => (
                <option key={subgroup.id} value={subgroup.id}>
                  {subgroupLabel(subgroup.name)}
                </option>
              ))}
            </select>
          </div>

          <div className="form__row">
            <label className="label" htmlFor="streams">
              Потоки
            </label>
            <select
              id="streams"
              className="select"
              multiple
              size={4}
              value={form.stream_ids.map(String)}
              onChange={(event) => patch({ stream_ids: selected(event) })}
            >
              {refs.streams.map((stream) => (
                <option key={stream.id} value={stream.id}>
                  {stream.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div className="form__row">
          <label className="label" htmlFor="note">
            Примітка
          </label>
          <input
            id="note"
            className="input"
            value={form.note ?? ''}
            onChange={(event) => patch({ note: event.target.value })}
            placeholder="Напр. «дистанційно» або «спільно з ПЗ-321»"
          />
        </div>

        {conflicts.length > 0 ? (
          <div
            ref={conflictsRef}
            className={blocking.length > 0 ? 'alert' : 'alert alert--warning'}
            role="alert"
          >
            <p style={{ marginBottom: '6px' }}>
              {blocking.length > 0
                ? `Конфлікти, які блокують збереження (${slot}):`
                : `Попередження (${slot}):`}
            </p>
            <ul style={{ margin: 0, paddingLeft: '18px' }}>
              {conflicts.map((conflict, index) => (
                <li key={`${conflict.other_entry_id}-${index}`}>
                  {conflictText(conflict, {
                    teachers: refs.teachers,
                    rooms: refs.rooms,
                    groups: refs.groups,
                    subgroups: refs.subgroups,
                  })}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        {blocking.length > 0 ? (
          canOverride ? (
            <div className="form__row">
              <label className="label" htmlFor="override">
                Причина збереження попри конфлікт (обовʼязково)
              </label>
              <input
                id="override"
                className="input"
                value={overrideReason}
                onChange={(event) => setOverrideReason(event.target.value)}
                placeholder="Напр. «погоджено з деканатом, аудиторія ділиться»"
              />
              <p className="hint">Причина потрапить у журнал аудиту разом з вашим обліковим записом.</p>
            </div>
          ) : (
            <p className="hint">
              Щоб зберегти попри конфлікт, потрібне право schedule.override_conflict.
            </p>
          )
        ) : null}

        {error ? (
          <p className="alert" role="alert">
            {error}
          </p>
        ) : null}

        <div className="modal__actions">
          <button type="button" className="btn" onClick={onClose}>
            Скасувати
          </button>
          <button
            type="submit"
            className="btn btn--primary"
            disabled={busy || (blocking.length > 0 && (!canOverride || overrideReason.trim() === ''))}
          >
            {blocking.length > 0 ? 'Зберегти попри конфлікт' : 'Зберегти'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
