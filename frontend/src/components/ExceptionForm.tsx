import { useState } from 'react'

import { adminApi } from '../api/endpoints'
import type {
  ExceptionAction,
  LessonView,
  PairTimeOption,
  RoomOption,
  ScheduleExceptionPayload,
  TeacherOption,
} from '../api/types'
import { formatLongDate } from '../lib/dates'
import { Modal } from './Modal'

interface ExceptionFormProps {
  lesson: LessonView
  /** Дата, на якій діє зміна (саме цей день показано в розкладі). */
  date: string
  teachers: TeacherOption[]
  rooms: RoomOption[]
  times: PairTimeOption[]
  onClose: () => void
  onSaved: () => void
}

const ACTIONS: { value: ExceptionAction; label: string; hint: string }[] = [
  { value: 'CANCEL', label: 'Скасувати', hint: 'Пара не відбудеться лише цього дня.' },
  { value: 'REPLACE', label: 'Заміна', hint: 'Інший викладач, аудиторія або час у цей день.' },
  { value: 'MOVE', label: 'Перенести', hint: 'Пара відбудеться іншого дня або в інший час.' },
]

export function ExceptionForm({
  lesson,
  date,
  teachers,
  rooms,
  times,
  onClose,
  onSaved,
}: ExceptionFormProps) {
  const [action, setAction] = useState<ExceptionAction>('CANCEL')
  const [newDate, setNewDate] = useState('')
  const [pairId, setPairId] = useState(0)
  const [roomId, setRoomId] = useState(0)
  const [teacherId, setTeacherId] = useState(0)
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const hint = ACTIONS.find((item) => item.value === action)?.hint

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    const payload: ScheduleExceptionPayload = {
      action,
      on_date: date,
      new_date: action === 'MOVE' && newDate ? newDate : null,
      new_pair_time_id: action === 'CANCEL' || pairId === 0 ? null : pairId,
      new_room_id: action === 'CANCEL' || roomId === 0 ? null : roomId,
      new_teacher_id: action === 'REPLACE' && teacherId !== 0 ? teacherId : null,
      reason: reason.trim() ? reason.trim() : null,
    }
    try {
      await adminApi.createException(lesson.entry_id, payload)
      onSaved()
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не вдалося зберегти зміну')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal title={`Зміна: ${lesson.subject_name}`} onClose={onClose}>
      <p className="hint" style={{ marginBottom: '12px' }}>
        {formatLongDate(date)} · {lesson.pair_number} пара · {lesson.lesson_type_name}
      </p>

      <form className="form" onSubmit={submit}>
        <div className="form__row">
          <span className="label">Що робимо</span>
          <div className="seg">
            {ACTIONS.map((item) => (
              <button
                key={item.value}
                type="button"
                className={item.value === action ? 'seg__btn seg__btn--active' : 'seg__btn'}
                onClick={() => setAction(item.value)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <p className="hint">{hint}</p>
        </div>

        {action === 'MOVE' ? (
          <div className="form__row">
            <label className="label" htmlFor="new-date">
              Нова дата (можна лишити порожньою, якщо змінюється лише пара)
            </label>
            <input
              id="new-date"
              className="input"
              type="date"
              value={newDate}
              onChange={(event) => setNewDate(event.target.value)}
            />
          </div>
        ) : null}

        {action !== 'CANCEL' ? (
          <div className="form__grid">
            <div className="form__row">
              <label className="label" htmlFor="new-pair">
                Нова пара
              </label>
              <select
                id="new-pair"
                className="select"
                value={pairId}
                onChange={(event) => setPairId(Number(event.target.value))}
              >
                <option value={0}>Без змін</option>
                {times.map((time) => (
                  <option key={time.id} value={time.id}>
                    {time.number} · {time.starts_at.slice(0, 5)}–{time.ends_at.slice(0, 5)}
                  </option>
                ))}
              </select>
            </div>

            <div className="form__row">
              <label className="label" htmlFor="new-room">
                Нова аудиторія
              </label>
              <select
                id="new-room"
                className="select"
                value={roomId}
                onChange={(event) => setRoomId(Number(event.target.value))}
              >
                <option value={0}>Без змін</option>
                {rooms.map((room) => (
                  <option key={room.id} value={room.id}>
                    {room.number} · {room.building_name}
                  </option>
                ))}
              </select>
            </div>

            {action === 'REPLACE' ? (
              <div className="form__row">
                <label className="label" htmlFor="new-teacher">
                  Викладач на заміні
                </label>
                <select
                  id="new-teacher"
                  className="select"
                  value={teacherId}
                  onChange={(event) => setTeacherId(Number(event.target.value))}
                >
                  <option value={0}>Без змін</option>
                  {teachers.map((teacher) => (
                    <option key={teacher.id} value={teacher.id}>
                      {teacher.short_name}
                    </option>
                  ))}
                </select>
              </div>
            ) : null}
          </div>
        ) : null}

        <div className="form__row">
          <label className="label" htmlFor="reason">
            Причина
          </label>
          <input
            id="reason"
            className="input"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Напр. «лікарняний», «відрядження», «святковий день»"
          />
          <p className="hint">Причина зберігається в журналі аудиту й показується студентам.</p>
        </div>

        {error ? (
          <p className="alert" role="alert">
            {error}
          </p>
        ) : null}

        <div className="modal__actions">
          <button type="button" className="btn" onClick={onClose}>
            Скасувати
          </button>
          <button type="submit" className="btn btn--primary" disabled={busy}>
            Зберегти зміну
          </button>
        </div>
      </form>
    </Modal>
  )
}
