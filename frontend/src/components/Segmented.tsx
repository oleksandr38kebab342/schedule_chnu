export interface SegmentedOption<T extends string | number> {
  value: T
  label: string
  title?: string
}

interface SegmentedProps<T extends string | number> {
  options: SegmentedOption<T>[]
  value: T
  onChange: (value: T) => void
  /** Темний акцент активної кнопки — як у перемикача тижня на макеті. */
  dark?: boolean
  ariaLabel: string
}

export function Segmented<T extends string | number>({
  options,
  value,
  onChange,
  dark = false,
  ariaLabel,
}: SegmentedProps<T>) {
  return (
    <div className={dark ? 'seg seg--dark' : 'seg'} role="group" aria-label={ariaLabel}>
      {options.map((option) => (
        <button
          key={String(option.value)}
          type="button"
          title={option.title}
          aria-pressed={option.value === value}
          className={option.value === value ? 'seg__btn seg__btn--active' : 'seg__btn'}
          onClick={() => onChange(option.value)}
        >
          {option.label}
        </button>
      ))}
    </div>
  )
}
