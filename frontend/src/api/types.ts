/** Типи відповідей API (дзеркало Pydantic-схем бекенду). */

export type Parity = 'ODD' | 'EVEN' | 'BOTH'

export type LessonStatus =
  | 'NORMAL'
  | 'ADDED'
  | 'MOVED_IN'
  | 'MOVED_OUT'
  | 'SHIFTED'
  | 'REPLACED'
  | 'CANCELLED'

export type ExceptionAction = 'ADD' | 'MOVE' | 'CANCEL' | 'REPLACE'

export interface RoomView {
  id: number
  number: string
  building_code: string
  building_name: string
  floor: number | null
}

export interface TeacherView {
  id: number
  full_name: string
  short_name: string
  degree: string | null
  position: string | null
  is_substitute: boolean
}

export interface LessonView {
  entry_id: number
  pair_number: number
  pair_label: string | null
  starts_at: string
  ends_at: string
  day_of_week: number
  week_parity: Parity
  subject_name: string
  subject_short: string | null
  lesson_type_code: string
  lesson_type_name: string
  lesson_type_short: string | null
  teachers: TeacherView[]
  rooms: RoomView[]
  groups: string[]
  subgroups: string[]
  streams: string[]
  note: string | null
  status: LessonStatus
  change_reason: string | null
  moved_to: string | null
  moved_from: string | null
}

export interface DayView {
  day: string
  day_of_week: number
  semester_id: number | null
  semester_name: string | null
  week_number: number | null
  parity: Parity | null
  is_working: boolean
  closed_reason: string | null
  lessons: LessonView[]
}

export interface WeekView {
  starts_on: string
  ends_on: string
  semester_id: number | null
  semester_name: string | null
  week_number: number | null
  parity: Parity | null
  days: DayView[]
}

export interface GroupOption {
  id: number
  name: string
  course: number | null
  department_id: number | null
  department_name: string | null
  faculty_id: number | null
  faculty_name: string | null
  faculty_short_name: string | null
}

export interface SubgroupOption {
  id: number
  group_id: number
  name: string
}

export interface TeacherOption {
  id: number
  full_name: string
  short_name: string
  degree: string | null
  position: string | null
  department_names: string[]
}

export interface RoomOption {
  id: number
  number: string
  building_id: number
  building_code: string
  building_name: string
  floor: number | null
  capacity: number | null
}

export interface LessonTypeOption {
  id: number
  code: string
  name: string
  short_name: string | null
}

export interface PairTimeOption {
  id: number
  number: number
  starts_at: string
  ends_at: string
  label: string | null
}

export interface CalendarInfo {
  day: string
  semester_id: number | null
  semester_name: string | null
  semester_start: string | null
  semester_end: string | null
  week_number: number | null
  parity: Parity | null
  week_starts_on: string | null
  week_ends_on: string | null
  is_working: boolean
  closed_reason: string | null
}

export interface CurrentUser {
  id: number
  email: string
  full_name: string
  is_active: boolean
  roles: string[]
  permissions: string[]
}

export interface ScheduleEntry {
  id: number
  semester_id: number
  subject_id: number
  lesson_type_id: number
  pair_time_id: number
  day_of_week: number
  week_parity: Parity
  note: string | null
  teacher_ids: number[]
  room_ids: number[]
  group_ids: number[]
  subgroup_ids: number[]
  stream_ids: number[]
}

export interface ScheduleEntryPayload {
  semester_id: number
  subject_id: number
  lesson_type_id: number
  pair_time_id: number
  day_of_week: number
  week_parity: Parity
  note?: string | null
  teacher_ids: number[]
  room_ids: number[]
  group_ids: number[]
  subgroup_ids: number[]
  stream_ids: number[]
  override_reason?: string | null
}

export interface Conflict {
  kind: 'TEACHER' | 'ROOM' | 'GROUP' | 'SUBGROUP'
  severity: 'INFO' | 'WARNING' | 'ERROR'
  resource_id: number
  other_entry_id: number
  details: string
}

export interface ScheduleSaveResult {
  entry: ScheduleEntry | null
  conflicts: Conflict[]
  saved: boolean
  overridden: boolean
}

export interface ScheduleExceptionPayload {
  action: ExceptionAction
  on_date: string
  new_date?: string | null
  new_pair_time_id?: number | null
  new_room_id?: number | null
  new_teacher_id?: number | null
  reason?: string | null
}

export interface ScheduleException extends ScheduleExceptionPayload {
  id: number
  entry_id: number
}

export interface SubjectOption {
  id: number
  name: string
  code: string
  short_name: string | null
  is_active: boolean
}

export interface StreamOption {
  id: number
  name: string
  is_active: boolean
  group_ids: number[]
}

export interface SemesterOption {
  id: number
  academic_year_id: number
  ordinal: number
  name: string
  start_date: string
  end_date: string
  first_week_parity: Parity
}

export interface AuditRecord {
  id: number
  created_at: string
  user_id: number | null
  user_email: string | null
  action: string
  entity_type: string
  entity_id: number | null
  old_value: unknown
  new_value: unknown
  reason: string | null
}
