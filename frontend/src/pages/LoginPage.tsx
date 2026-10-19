import { useState } from 'react'
import { useNavigate } from 'react-router-dom'

import { useAuth } from '../auth/AuthContext'
import { ErrorAlert } from '../components/Feedback'
import { Layout } from '../components/Layout'

export function LoginPage() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      await login(email.trim(), password)
      navigate('/dispatcher')
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не вдалося увійти')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Layout>
      <div className="card" style={{ maxWidth: '420px', margin: '40px auto' }}>
        <h1 style={{ fontSize: '18px', marginBottom: '6px' }}>Вхід до кабінету</h1>
        <p className="hint" style={{ marginBottom: '16px' }}>
          Розклад можна дивитися без входу. Вхід потрібен диспетчерам і адміністраторам.
        </p>

        <form className="form" onSubmit={submit}>
          <div className="form__row">
            <label className="label" htmlFor="email">
              Email
            </label>
            <input
              id="email"
              className="input"
              type="email"
              autoComplete="username"
              required
              value={email}
              onChange={(event) => setEmail(event.target.value)}
            />
          </div>

          <div className="form__row">
            <label className="label" htmlFor="password">
              Пароль
            </label>
            <input
              id="password"
              className="input"
              type="password"
              autoComplete="current-password"
              required
              value={password}
              onChange={(event) => setPassword(event.target.value)}
            />
          </div>

          {error ? <ErrorAlert message={error} /> : null}

          <button type="submit" className="btn btn--primary" disabled={busy}>
            {busy ? 'Вхід…' : 'Увійти'}
          </button>
        </form>
      </div>
    </Layout>
  )
}
