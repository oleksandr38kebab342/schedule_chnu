import { useEffect, useMemo, useState } from 'react'
import { Navigate } from 'react-router-dom'

import { adminApi, publicApi } from '../api/endpoints'
import type { GroupOption, SemesterOption } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { ErrorAlert, Skeletons } from '../components/Feedback'
import { Layout } from '../components/Layout'

export function ExportPage() {
  const { user, loading: authLoading, can } = useAuth()
  const [groups, setGroups] = useState<GroupOption[]>([])
  const [semesters, setSemesters] = useState<SemesterOption[]>([])
  const [semesterId, setSemesterId] = useState<number | null>(null)
  const [selected, setSelected] = useState<Set<number>>(new Set())
  const [search, setSearch] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    if (!user) return
    let active = true
    Promise.all([publicApi.groups(), adminApi.semesters()])
      .then(([groupList, semesterList]) => {
        if (!active) return
        setGroups(groupList)
        setSemesters(semesterList)
        setSemesterId(semesterList[semesterList.length - 1]?.id ?? null)
      })
      .catch((cause: Error) => {
        if (active) setError(cause.message)
      })
    return () => {
      active = false
    }
  }, [user])

  const visible = useMemo(() => {
    const needle = search.trim().toLowerCase()
    return needle ? groups.filter((group) => group.name.toLowerCase().includes(needle)) : groups
  }, [groups, search])

  if (authLoading) {
    return (
      <Layout>
        <Skeletons />
      </Layout>
    )
  }
  if (!user) return <Navigate to="/login" replace />

  const toggle = (id: number) => {
    setSelected((previous) => {
      const next = new Set(previous)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const download = async () => {
    if (semesterId === null || selected.size === 0) return
    setBusy(true)
    setError(null)
    setNotice(null)
    try {
      const blob = await adminApi.exportGroups(semesterId, [...selected])
      const url = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `rozklad_${semesterId}.xlsx`
      link.click()
      URL.revokeObjectURL(url)
      setNotice(`Вивантажено груп: ${selected.size}`)
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : 'Не вдалося сформувати файл')
    } finally {
      setBusy(false)
    }
  }

  return (
    <Layout>
      <div className="card" style={{ maxWidth: '720px', margin: '0 auto' }}>
        <h1 style={{ fontSize: '18px', marginBottom: '4px' }}>Експорт розкладу в Excel</h1>
        <p className="hint" style={{ marginBottom: '16px' }}>
          Файл формується у друкованому вигляді: два рядки на пару (непарний / парний тиждень),
          орієнтація Landscape, по одному аркушу на групу.
        </p>

        {!can('schedule.export') ? (
          <p className="alert alert--warning">
            Для експорту потрібне право schedule.export.
          </p>
        ) : null}

        <div className="form">
          <div className="form__grid">
            <div className="form__row">
              <label className="label" htmlFor="export-semester">
                Семестр
              </label>
              <select
                id="export-semester"
                className="select"
                value={semesterId ?? ''}
                onChange={(event) => setSemesterId(Number(event.target.value))}
              >
                {semesters.map((semester) => (
                  <option key={semester.id} value={semester.id}>
                    {semester.name} ({semester.start_date.slice(0, 4)})
                  </option>
                ))}
              </select>
            </div>

            <div className="form__row">
              <label className="label" htmlFor="export-search">
                Пошук групи
              </label>
              <input
                id="export-search"
                className="input"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Напр. КН-3"
              />
            </div>
          </div>

          <div className="form__row">
            <div className="field" style={{ gap: '8px' }}>
              <button
                type="button"
                className="btn btn--small"
                onClick={() => setSelected(new Set(visible.map((group) => group.id)))}
              >
                Обрати всі
              </button>
              <button
                type="button"
                className="btn btn--small"
                onClick={() => setSelected(new Set())}
              >
                Зняти вибір
              </button>
              <span className="hint">Вибрано: {selected.size}</span>
            </div>
          </div>

          <div
            className="form__grid"
            style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(150px, 1fr))', gap: '6px' }}
          >
            {visible.map((group) => (
              <label key={group.id} className="field" style={{ fontWeight: 600 }}>
                <input
                  type="checkbox"
                  checked={selected.has(group.id)}
                  onChange={() => toggle(group.id)}
                />
                {group.name}
              </label>
            ))}
          </div>

          {error ? <ErrorAlert message={error} /> : null}
          {notice ? <p className="alert alert--info">{notice}</p> : null}

          <div>
            <button
              type="button"
              className="btn btn--primary"
              disabled={busy || selected.size === 0 || semesterId === null}
              onClick={download}
            >
              {busy ? 'Формуємо…' : 'Експортувати (.xlsx)'}
            </button>
          </div>
        </div>
      </div>
    </Layout>
  )
}
