import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

import { getToken, setToken } from '../api/client'
import { authApi } from '../api/endpoints'
import type { CurrentUser } from '../api/types'

interface AuthState {
  user: CurrentUser | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  /** Права перевіряються й на бекенді; тут — лише щоб не показувати зайвих кнопок. */
  can: (permission: string) => boolean
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [loading, setLoading] = useState(getToken() !== null)

  useEffect(() => {
    if (getToken() === null) return
    let active = true
    authApi
      .me()
      .then((me) => {
        if (active) setUser(me)
      })
      .catch(() => {
        // Протермінований або зіпсований токен — повертаємось до гостя.
        setToken(null)
        if (active) setUser(null)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const { access_token } = await authApi.login(email, password)
    setToken(access_token)
    setUser(await authApi.me())
  }, [])

  const logout = useCallback(() => {
    setToken(null)
    setUser(null)
  }, [])

  const can = useCallback(
    (permission: string) => user?.permissions.includes(permission) ?? false,
    [user],
  )

  const value = useMemo<AuthState>(
    () => ({ user, loading, login, logout, can }),
    [user, loading, login, logout, can],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext)
  if (context === null) throw new Error('useAuth доступний лише всередині AuthProvider')
  return context
}
