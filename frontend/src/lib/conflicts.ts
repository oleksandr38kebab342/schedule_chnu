/** Людський опис конфлікту замість «спільний ресурс #id». */

import type { Conflict, GroupOption, RoomOption, SubgroupOption, TeacherOption } from '../api/types'
import { DAY_NAMES } from './dates'
import { subgroupLabel } from './lessons'

export interface ConflictNames {
  teachers: TeacherOption[]
  rooms: RoomOption[]
  groups: GroupOption[]
  subgroups: SubgroupOption[]
}

function name(conflict: Conflict, names: ConflictNames): string {
  switch (conflict.kind) {
    case 'TEACHER':
      return names.teachers.find((t) => t.id === conflict.resource_id)?.short_name ?? 'викладач'
    case 'ROOM':
      return names.rooms.find((r) => r.id === conflict.resource_id)?.number ?? 'аудиторія'
    case 'GROUP':
      return names.groups.find((g) => g.id === conflict.resource_id)?.name ?? 'група'
    case 'SUBGROUP': {
      const subgroup = names.subgroups.find((s) => s.id === conflict.resource_id)
      return subgroup ? subgroupLabel(subgroup.name) : 'підгрупа'
    }
  }
}

export function conflictText(conflict: Conflict, names: ConflictNames): string {
  const who = name(conflict, names)
  switch (conflict.kind) {
    case 'TEACHER':
      return `Викладач ${who} у цей час уже має іншу пару`
    case 'ROOM':
      return `Аудиторія ${who} у цей час уже зайнята`
    case 'GROUP':
      return `У групи ${who} у цей час уже є пара`
    case 'SUBGROUP':
      return `У ${who} у цей час уже є пара`
  }
}

/** «Пн, 2 пара» — коли саме стався збіг (дані беремо з форми). */
export function slotText(dayOfWeek: number, pairNumber: number | null): string {
  const day = DAY_NAMES[dayOfWeek - 1] ?? ''
  return pairNumber ? `${day}, ${pairNumber} пара` : day
}
