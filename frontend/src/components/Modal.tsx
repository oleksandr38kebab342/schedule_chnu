import { useEffect } from 'react'
import type { ReactNode } from 'react'

interface ModalProps {
  title: string
  onClose: () => void
  children: ReactNode
  footer?: ReactNode
}

export function Modal({ title, onClose, children, footer }: ModalProps) {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [onClose])

  return (
    <div
      className="modal"
      role="presentation"
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose()
      }}
    >
      <div className="modal__box" role="dialog" aria-modal="true" aria-label={title}>
        <div className="modal__head">
          <h2 style={{ fontSize: '16px' }}>{title}</h2>
          <button type="button" className="btn btn--small btn--ghost" onClick={onClose}>
            Закрити
          </button>
        </div>
        {children}
        {footer ? <div className="modal__actions">{footer}</div> : null}
      </div>
    </div>
  )
}
