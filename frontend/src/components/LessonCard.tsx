import type { ReactNode } from 'react'

import type { LessonView } from '../api/types'
import { formatDayMonth, formatTime, isHappeningNow } from '../lib/dates'
import {
  audienceLabel,
  placeLabel,
  roomLabel,
  statusBadge,
  statusNote,
  teacherLabel,
  typeStyle,
} from '../lib/lessons'

function PersonIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <circle cx="8" cy="5" r="2.75" stroke="currentColor" strokeWidth="1.3" />
      <path d="M2.75 13.5c.6-2.6 2.7-4 5.25-4s4.65 1.4 5.25 4" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  )
}

function PinIcon() {
  return (
    <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <path d="M8 14.5s4.75-4.2 4.75-7.75a4.75 4.75 0 1 0-9.5 0C3.25 10.3 8 14.5 8 14.5Z" stroke="currentColor" strokeWidth="1.3" />
      <circle cx="8" cy="6.5" r="1.6" stroke="currentColor" strokeWidth="1.3" />
    </svg>
  )
}

interface LessonCardProps {
  lesson: LessonView
  /** Дата, на яку показано пару: потрібна, щоб визначити «зараз іде». */
  day: string
  now?: Date
  /** Дії диспетчера (редагувати, скасувати) — у публічному перегляді порожньо. */
  actions?: ReactNode
}

export function LessonCard({ lesson, day, now, actions }: LessonCardProps) {
  const live = lesson.status !== 'CANCELLED' &&
    lesson.status !== 'MOVED_OUT' &&
    isHappeningNow(day, lesson.starts_at, lesson.ends_at, now)
  const badge = statusBadge(lesson)
  const note = statusNote(lesson, formatDayMonth)
  const audience = audienceLabel(lesson)
  const room = roomLabel(lesson)
  const place = placeLabel(lesson)
  const teachers = teacherLabel(lesson)
  const substitute = lesson.teachers.some((teacher) => teacher.is_substitute)

  const classes = ['lesson']
  if (live) classes.push('lesson--now')
  if (lesson.status === 'CANCELLED' || lesson.status === 'MOVED_OUT') {
    classes.push('lesson--cancelled')
  }

  return (
    <article className={classes.join(' ')} style={typeStyle(lesson.lesson_type_code)}>
      <div className="lesson__index">
        <span className="lesson__index-number mono">{lesson.pair_number}</span>
        <span className="lesson__index-label">пара</span>
      </div>

      <div className="lesson__main">
        <div className="lesson__meta">
          <span className="lesson__time mono">
            {formatTime(lesson.starts_at)} – {formatTime(lesson.ends_at)}
          </span>
          <span className="badge badge--type">
            <span className="badge__dot" />
            {lesson.lesson_type_name}
          </span>
          {live ? (
            <span className="badge badge--now">
              <span className="badge__dot" />
              Зараз іде
            </span>
          ) : null}
          {badge ? (
            <span className={`badge badge--status badge--${badge.tone}`}>{badge.label}</span>
          ) : null}
        </div>

        <h3 className="lesson__subject">{lesson.subject_name}</h3>

        {teachers ? (
          <p className="lesson__people">
            <PersonIcon />
            {substitute ? <span className="lesson__time">заміна:</span> : null}
            <span>{teachers}</span>
          </p>
        ) : null}

        {note ? <p className="lesson__note">{note}</p> : null}
        {lesson.note ? <p className="lesson__note">{lesson.note}</p> : null}

        {actions ? <div className="lesson__actions">{actions}</div> : null}
      </div>

      <div className="lesson__side">
        {room ? (
          <span className="lesson__room mono">
            <PinIcon />
            {room}
            {lesson.rooms[0]?.building_name ? `, ${lesson.rooms[0].building_name}` : ''}
          </span>
        ) : (
          <span className="lesson__place">Аудиторію не вказано</span>
        )}
        {place ? <span className="lesson__place">{place}</span> : null}
        {audience ? (
          <span
            className={
              lesson.subgroups.length > 0
                ? 'badge badge--status badge--warning'
                : 'badge badge--muted'
            }
          >
            {audience}
          </span>
        ) : null}
      </div>
    </article>
  )
}
