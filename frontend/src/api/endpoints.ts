/** Виклики API, згруповані за призначенням. */

import { download, request } from './client'
import type {
  AuditRecord,
  CalendarInfo,
  CurrentUser,
  DayView,
  GroupOption,
  LessonTypeOption,
  PairTimeOption,
  RoomOption,
  ScheduleEntry,
  ScheduleException,
  ScheduleExceptionPayload,
  ScheduleEntryPayload,
  ScheduleSaveResult,
  SemesterOption,
  StreamOption,
  SubgroupOption,
  SubjectOption,
  TeacherOption,
  WeekView,
} from './types'

export type ViewScope = 'day' | 'week'

/** Читання опублікованого розкладу — без входу. */
export const publicApi = {
  groups: (search?: string) => request<GroupOption[]>('/public/groups', { query: { search } }),
  subgroups: (groupId: number) =>
    request<SubgroupOption[]>(`/public/groups/${groupId}/subgroups`),
  teachers: (search?: string) =>
    request<TeacherOption[]>('/public/teachers', { query: { search } }),
  rooms: (search?: string) => request<RoomOption[]>('/public/rooms', { query: { search } }),
  lessonTypes: () => request<LessonTypeOption[]>('/public/lesson-types'),
  times: () => request<PairTimeOption[]>('/public/times'),
  calendar: (date?: string, semesterId?: number) =>
    request<CalendarInfo>('/public/calendar', { query: { date, semester_id: semesterId } }),

  groupDay: (groupId: number, date: string, subgroupId?: number | null) =>
    request<DayView>(`/public/schedule/group/${groupId}/day`, {
      query: { date, subgroup_id: subgroupId ?? undefined },
    }),
  groupWeek: (groupId: number, date: string, subgroupId?: number | null) =>
    request<WeekView>(`/public/schedule/group/${groupId}/week`, {
      query: { date, subgroup_id: subgroupId ?? undefined },
    }),
  teacherDay: (teacherId: number, date: string) =>
    request<DayView>(`/public/schedule/teacher/${teacherId}/day`, { query: { date } }),
  teacherWeek: (teacherId: number, date: string) =>
    request<WeekView>(`/public/schedule/teacher/${teacherId}/week`, { query: { date } }),
  roomDay: (roomId: number, date: string) =>
    request<DayView>(`/public/schedule/room/${roomId}/day`, { query: { date } }),
  roomWeek: (roomId: number, date: string) =>
    request<WeekView>(`/public/schedule/room/${roomId}/week`, { query: { date } }),
}

export const authApi = {
  login: (email: string, password: string) =>
    request<{ access_token: string; token_type: string }>('/auth/login', {
      method: 'POST',
      body: { email, password },
    }),
  me: () => request<CurrentUser>('/auth/me', { auth: true }),
}

/** Усе, що потребує входу й прав: редагування розкладу, експорт, аудит. */
export const adminApi = {
  semesters: () => request<SemesterOption[]>('/semesters', { auth: true }),
  subjects: () => request<SubjectOption[]>('/subjects', { auth: true }),
  streams: () => request<StreamOption[]>('/streams', { auth: true }),

  entry: (entryId: number) => request<ScheduleEntry>(`/schedule/${entryId}`, { auth: true }),
  createEntry: (payload: ScheduleEntryPayload) =>
    request<ScheduleSaveResult>('/schedule', { method: 'POST', body: payload, auth: true }),
  updateEntry: (entryId: number, payload: ScheduleEntryPayload) =>
    request<ScheduleSaveResult>(`/schedule/${entryId}`, {
      method: 'PUT',
      body: payload,
      auth: true,
    }),
  deleteEntry: (entryId: number) =>
    request<void>(`/schedule/${entryId}`, { method: 'DELETE', auth: true }),

  exceptions: (entryId: number) =>
    request<ScheduleException[]>(`/schedule/${entryId}/exceptions`, { auth: true }),
  createException: (entryId: number, payload: ScheduleExceptionPayload) =>
    request<ScheduleException>(`/schedule/${entryId}/exceptions`, {
      method: 'POST',
      body: payload,
      auth: true,
    }),
  deleteException: (exceptionId: number) =>
    request<void>(`/schedule/exceptions/${exceptionId}`, { method: 'DELETE', auth: true }),

  exportGroups: (semesterId: number, groupIds: number[]) =>
    download('/export', { semester_id: semesterId, group_ids: groupIds }),

  audit: (limit = 100) => request<AuditRecord[]>('/audit', { query: { limit }, auth: true }),
}
