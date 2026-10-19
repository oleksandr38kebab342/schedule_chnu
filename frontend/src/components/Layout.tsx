import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'

function CalendarMark() {
  return (
    <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden="true">
      <rect x="1.75" y="3" width="12.5" height="11.25" rx="2.5" stroke="currentColor" strokeWidth="1.4" />
      <path d="M1.75 6.5h12.5M5.25 1.75v2.5M10.75 1.75v2.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
    </svg>
  )
}

interface LayoutProps {
  children: ReactNode
  /** Правий бік шапки: чип з датою й тижнем на сторінці розкладу. */
  headerRight?: ReactNode
  /** Панель фільтрів, прикріплена під шапкою. */
  toolbar?: ReactNode
}

export function Layout({ children, headerRight, toolbar }: LayoutProps) {
  const { user, logout } = useAuth()

  return (
    <div className="app">
      <header className="topbar">
        <div className="page topbar__inner">
          <NavLink to="/" className="brand">
            <span className="brand__mark">
              <CalendarMark />
            </span>
            <span className="brand__title">Розклад занять</span>
            <span className="brand__sub">· ФМІ ЧНУ</span>
          </NavLink>

          <div className="topbar__right">
            {headerRight}
            <nav className="navlinks">
              {user ? (
                <>
                  <NavLink
                    to="/dispatcher"
                    className={({ isActive }) =>
                      isActive ? 'navlink navlink--active' : 'navlink'
                    }
                  >
                    Кабінет
                  </NavLink>
                  <button type="button" className="btn btn--small btn--ghost" onClick={logout}>
                    Вийти
                  </button>
                </>
              ) : (
                <NavLink
                  to="/login"
                  className={({ isActive }) => (isActive ? 'navlink navlink--active' : 'navlink')}
                >
                  Вхід
                </NavLink>
              )}
            </nav>
          </div>
        </div>
      </header>

      {toolbar ? <div className="toolbar">{toolbar}</div> : null}

      <main className="content">
        <div className="page">{children}</div>
      </main>

      <footer className="footer">
        <div className="page footer__inner">
          <span>Офіційний розклад занять · ФМІ ЧНУ</span>
          <span>Синхронізовано з навчальною базою даних</span>
        </div>
      </footer>
    </div>
  )
}
