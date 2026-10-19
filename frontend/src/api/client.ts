/** Тонкий клієнт API: один fetch-врапер, токен у localStorage. */

const BASE = import.meta.env.VITE_API_URL ?? '/api/v1'
const TOKEN_KEY = 'rozklad.token'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    // Приватний режим браузера може забороняти доступ до сховища.
    return null
  }
}

export function setToken(token: string | null): void {
  try {
    if (token === null) localStorage.removeItem(TOKEN_KEY)
    else localStorage.setItem(TOKEN_KEY, token)
  } catch {
    /* працюємо й без збереження: токен житиме до перезавантаження */
  }
}

type Query = Record<string, string | number | boolean | null | undefined>

export function withQuery(path: string, query?: Query): string {
  if (!query) return path
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value !== null && value !== undefined && value !== '') params.set(key, String(value))
  }
  const qs = params.toString()
  return qs ? `${path}?${qs}` : path
}

async function errorMessage(response: Response): Promise<string> {
  try {
    const body = await response.json()
    const detail = body?.detail
    if (typeof detail === 'string') return detail
    // 422 від Pydantic приходить списком помилок — показуємо першу зрозуміло.
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0]
      return typeof first?.msg === 'string' ? first.msg : JSON.stringify(first)
    }
  } catch {
    /* тіло не JSON — нижче повернемо загальний текст */
  }
  return `Помилка запиту (${response.status})`
}

interface RequestOptions {
  method?: string
  body?: unknown
  query?: Query
  auth?: boolean
}

export async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const { method = 'GET', body, query, auth = false } = options
  const headers: Record<string, string> = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (auth) {
    const token = getToken()
    if (token) headers.Authorization = `Bearer ${token}`
  }

  const response = await fetch(`${BASE}${withQuery(path, query)}`, {
    method,
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })

  if (!response.ok) throw new ApiError(response.status, await errorMessage(response))
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

/** Завантаження файлу (Excel-експорт) з тим самим токеном. */
export async function download(path: string, body: unknown): Promise<Blob> {
  const token = getToken()
  const response = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
    body: JSON.stringify(body),
  })
  if (!response.ok) throw new ApiError(response.status, await errorMessage(response))
  return response.blob()
}
