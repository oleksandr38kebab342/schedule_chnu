import { useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'

import { adminApi } from '../api/endpoints'
import type { AuditRecord } from '../api/types'
import { useAuth } from '../auth/AuthContext'
import { EmptyState, ErrorAlert, Skeletons } from '../components/Feedback'
import { Layout } from '../components/Layout'

const ACTION_LABELS: Record<string, string> = {
  'schedule.create': 'Створення заняття',
  'schedule.edit': 'Редагування заняття',
  'schedule.delete': 'Видалення заняття',
  'schedule.export': 'Експорт у Excel',
  'schedule.override_conflict': 'Збереження попри конфлікт',
  'schedule.exception.cancel': 'Скасування на дату',
  'schedule.exception.move': 'Перенесення',
  'schedule.exception.replace': 'Заміна',
  'schedule.exception.add': 'Додаткове заняття',
  'schedule.exception.delete': 'Скасовано точкову зміну',
}

function formatMoment(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('uk-UA')
}

export function AuditPage() {
  const { user, loading: authLoading, can } = useAuth()
  const [records, setRecords] = useState<AuditRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!user) return
    let active = true
    adminApi
      .audit(200)
      .then((loaded) => {
        if (active) setRecords(loaded)
      })
      .catch((cause: Error) => {
        if (active) setError(cause.message)
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => {
      active = false
    }
  }, [user])

  if (authLoading) {
    return (
      <Layout>
        <Skeletons />
      </Layout>
    )
  }
  if (!user) return <Navigate to="/login" replace />

  return (
    <Layout>
      <div className="content__head">
        <p className="content__title">
          <strong>Журнал аудиту</strong>
        </p>
        <p>Хто, коли і що змінив у розкладі</p>
      </div>

      {!can('audit.view') ? (
        <p className="alert alert--warning">Для перегляду журналу потрібне право audit.view.</p>
      ) : null}
      {error ? <ErrorAlert message={error} /> : null}

      {loading ? (
        <Skeletons />
      ) : records.length === 0 ? (
        <EmptyState title="Записів ще немає" />
      ) : (
        <div className="card table__scroll">
          <table className="table">
            <thead>
              <tr>
                <th>Коли</th>
                <th>Хто</th>
                <th>Дія</th>
                <th>Обʼєкт</th>
                <th>Причина</th>
              </tr>
            </thead>
            <tbody>
              {records.map((record) => (
                <tr key={record.id}>
                  <td className="mono">{formatMoment(record.created_at)}</td>
                  <td>{record.user_email ?? '—'}</td>
                  <td>{ACTION_LABELS[record.action] ?? record.action}</td>
                  <td className="mono">
                    {record.entity_type}
                    {record.entity_id !== null ? ` #${record.entity_id}` : ''}
                  </td>
                  <td>{record.reason ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Layout>
  )
}
