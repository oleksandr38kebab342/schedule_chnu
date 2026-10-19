import { DAY_NAMES_SHORT, isoWeekday, parseISODate, todayISO } from '../lib/dates'

interface DayStripProps {
  dates: string[]
  value: string
  onChange: (day: string) => void
  /** Дати без жодної пари показуються приглушено. */
  emptyDates?: ReadonlySet<string>
  today?: string
}

export function DayStrip({
  dates,
  value,
  onChange,
  emptyDates,
  today = todayISO(),
}: DayStripProps) {
  return (
    <nav className="daystrip" aria-label="Дні тижня">
      {dates.map((day) => {
        const classes = ['day']
        if (day === value) classes.push('day--active')
        if (day === today) classes.push('day--today')
        if (emptyDates?.has(day)) classes.push('day--empty')

        return (
          <button
            key={day}
            type="button"
            className={classes.join(' ')}
            aria-current={day === value ? 'date' : undefined}
            onClick={() => onChange(day)}
          >
            <span className="day__name">{DAY_NAMES_SHORT[isoWeekday(day) - 1]}</span>
            <span className="day__date mono">{parseISODate(day).getDate()}</span>
          </button>
        )
      })}
    </nav>
  )
}
