import type { ReactNode } from 'react'

export function Skeletons({ count = 3 }: { count?: number }) {
  return (
    <div className="lessons" aria-busy="true" aria-live="polite">
      {Array.from({ length: count }, (_, index) => (
        <div key={index} className="skeleton" />
      ))}
    </div>
  )
}

interface EmptyStateProps {
  title: string
  description?: ReactNode
}

export function EmptyState({ title, description }: EmptyStateProps) {
  return (
    <div className="empty">
      <p className="empty__title">{title}</p>
      {description ? <p>{description}</p> : null}
    </div>
  )
}

export function ErrorAlert({ message }: { message: string }) {
  return (
    <p className="alert" role="alert">
      {message}
    </p>
  )
}
