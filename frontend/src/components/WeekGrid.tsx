import type { DayView } from '../api/types'
import { DAY_NAMES_SHORT, formatShortDate, formatTime, todayISO } from '../lib/dates'
import { audienceLabel, roomLabel, statusBadge, teacherLabel, typeStyle } from '../lib/lessons'

interface WeekGridProps {
  days: DayView[]
  today?: string
  onPickDay?: (day: string) => void
}

/** Тиждень колонками по днях: читається і на телефоні, і на проєкторі. */
export function WeekGrid({ days, today = todayISO(), onPickDay }: WeekGridProps) {
  return (
    <div className="week">
      {days.map((day) => (
        <section
          key={day.day}
          className={day.day === today ? 'weekday weekday--today' : 'weekday'}
        >
          <header className="weekday__head">
            {onPickDay ? (
              <button
                type="button"
                className="weekday__link"
                onClick={() => onPickDay(day.day)}
                title="Відкрити цей день"
              >
                {DAY_NAMES_SHORT[day.day_of_week - 1]}
              </button>
            ) : (
              <span>{DAY_NAMES_SHORT[day.day_of_week - 1]}</span>
            )}
            <span className="weekday__date mono">{formatShortDate(day.day)}</span>
          </header>

          <div className="weekday__body">
            {!day.is_working ? (
              <p className="slot__meta">{day.closed_reason ?? 'Занять немає'}</p>
            ) : day.lessons.length === 0 ? (
              <p className="slot__meta">Пар немає</p>
            ) : (
              day.lessons.map((lesson) => {
                const badge = statusBadge(lesson)
                const audience = audienceLabel(lesson)
                const classes = ['slot']
                if (lesson.status === 'CANCELLED' || lesson.status === 'MOVED_OUT') {
                  classes.push('slot--cancelled')
                }
                return (
                  <article
                    key={`${lesson.entry_id}-${lesson.pair_number}`}
                    className={classes.join(' ')}
                    style={typeStyle(lesson.lesson_type_code)}
                  >
                    <span className="slot__time mono">
                      {lesson.pair_number} · {formatTime(lesson.starts_at)}–
                      {formatTime(lesson.ends_at)}
                    </span>
                    <span className="slot__subject">
                      {lesson.subject_short ?? lesson.subject_name}
                    </span>
                    <span className="slot__meta">
                      {[lesson.lesson_type_short ?? lesson.lesson_type_name, roomLabel(lesson), teacherLabel(lesson)]
                        .filter(Boolean)
                        .join(' · ')}
                    </span>
                    {audience ? <span className="slot__meta">{audience}</span> : null}
                    {badge ? (
                      <span
                        className={`badge badge--status badge--${badge.tone}`}
                        style={{ justifySelf: 'start' }}
                      >
                        {badge.label}
                      </span>
                    ) : null}
                  </article>
                )
              })
            )}
          </div>
        </section>
      ))}
    </div>
  )
}
