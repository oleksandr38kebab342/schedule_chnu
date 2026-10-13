"""ExcelExportService — генерація розкладу у .xlsx (ТЗ, розділи 50-63).

Сервіс не залежить від HTTP чи ORM: на вхід — прості структури даних,
на вихід — байти .xlsx. Логіка розбита на validate -> build_grid ->
generate_workbook, щоб кожен крок тестувався окремо.

Ключові вимоги ТЗ:
- дворядкова структура пари: непарний тиждень зверху, парний знизу;
- однакові для obох тижнів клітинки обʼєднуються вертикально;
- накладки (кілька занять в один слот) виводяться списком, а не перезаписом;
- нестандартний час пари ніколи не губиться (get_pair_times);
- друк Landscape, шапка закріплена (freeze_panes) і повторюється на сторінках.
"""

from dataclasses import dataclass, field
from datetime import time
from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from app.models import Parity

DAY_NAMES = {
    1: "Понеділок",
    2: "Вівторок",
    3: "Середа",
    4: "Четвер",
    5: "Пʼятниця",
    6: "Субота",
    7: "Неділя",
}
WEEKDAYS = (1, 2, 3, 4, 5)  # Пн-Пт завжди присутні


@dataclass(frozen=True)
class PairSlot:
    number: int
    starts_at: time | None = None
    ends_at: time | None = None

    def time_label(self) -> str:
        if self.starts_at and self.ends_at:
            return f"{self.starts_at:%H:%M}–{self.ends_at:%H:%M}"
        return ""  # нестандартний/незаданий час — лишаємо порожнім, але слот не зникає


@dataclass(frozen=True)
class Lesson:
    day_of_week: int
    pair_number: int
    parity: Parity
    text: str


@dataclass
class Grid:
    pairs: list[PairSlot]
    days: list[int]
    # cells[(pair_number, day, parity)] -> список рядків (накладки)
    cells: dict[tuple[int, int, Parity], list[str]] = field(default_factory=dict)

    def cell(self, pair_number: int, day: int, parity: Parity) -> list[str]:
        return self.cells.get((pair_number, day, parity), [])


def build_grid(lessons: list[Lesson], pairs: list[PairSlot]) -> Grid:
    """Розкладає заняття по сітці; Сб/Нд додаються лише за наявності занять."""
    used_days = {lesson.day_of_week for lesson in lessons}
    days = list(WEEKDAYS) + [d for d in (6, 7) if d in used_days]

    grid = Grid(pairs=sorted(pairs, key=lambda p: p.number), days=days)
    for lesson in lessons:
        targets = (
            [Parity.ODD, Parity.EVEN] if lesson.parity is Parity.BOTH else [lesson.parity]
        )
        for parity in targets:
            key = (lesson.pair_number, lesson.day_of_week, parity)
            grid.cells.setdefault(key, []).append(lesson.text)
    return grid


_THIN = Side(style="thin", color="B0B0B0")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)
_HEADER_FILL = PatternFill("solid", fgColor="234573")
_ODD_FILL = PatternFill("solid", fgColor="EEF3F9")
_WRAP = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _write_sheet(ws: Worksheet, title: str, grid: Grid) -> None:
    ws.title = title[:31] or "Розклад"  # Excel обмежує назву аркуша 31 символом

    ws.cell(row=1, column=1, value=title)
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=2 + len(grid.days))

    header_row = 2
    ws.cell(row=header_row, column=1, value="Пара")
    ws.cell(row=header_row, column=2, value="Час")
    for col, day in enumerate(grid.days, start=3):
        ws.cell(row=header_row, column=col, value=DAY_NAMES[day])
    for col in range(1, 3 + len(grid.days)):
        c = ws.cell(row=header_row, column=col)
        c.fill = _HEADER_FILL
        c.font = Font(bold=True, color="FFFFFF")
        c.alignment = _WRAP
        c.border = _BORDER

    row = header_row + 1
    for pair in grid.pairs:
        odd_row, even_row = row, row + 1
        # Пара й час обʼєднані на два підрядки (odd/even).
        for col, value in ((1, pair.number), (2, pair.time_label())):
            ws.merge_cells(start_row=odd_row, start_column=col, end_row=even_row, end_column=col)
            c = ws.cell(row=odd_row, column=col, value=value)
            c.alignment = _WRAP
            c.border = _BORDER
            ws.cell(row=even_row, column=col).border = _BORDER

        for col, day in enumerate(grid.days, start=3):
            odd = grid.cell(pair.number, day, Parity.ODD)
            even = grid.cell(pair.number, day, Parity.EVEN)
            odd_text = "\n— — —\n".join(odd)  # накладки через розділювач, не перезапис
            even_text = "\n— — —\n".join(even)

            if odd_text and odd_text == even_text:
                # Однаково для обох тижнів — обʼєднуємо вертикально.
                ws.merge_cells(
                    start_row=odd_row, start_column=col, end_row=even_row, end_column=col
                )
                c = ws.cell(row=odd_row, column=col, value=odd_text)
                c.alignment = _WRAP
                c.border = _BORDER
                ws.cell(row=even_row, column=col).border = _BORDER
            else:
                oc = ws.cell(row=odd_row, column=col, value=odd_text)
                oc.alignment = _WRAP
                oc.border = _BORDER
                oc.fill = _ODD_FILL
                ec = ws.cell(row=even_row, column=col, value=even_text)
                ec.alignment = _WRAP
                ec.border = _BORDER
        row += 2

    ws.column_dimensions[get_column_letter(1)].width = 6
    ws.column_dimensions[get_column_letter(2)].width = 13
    for col in range(3, 3 + len(grid.days)):
        ws.column_dimensions[get_column_letter(col)].width = 22

    ws.freeze_panes = "C3"
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.print_title_rows = "1:2"  # шапка повторюється на кожній друкованій сторінці


def generate_workbook(sheets: list[tuple[str, Grid]]) -> bytes:
    """Збирає книгу з одного або кількох аркушів (title, grid) і повертає байти."""
    if not sheets:
        raise ValueError("Немає даних для експорту")

    wb = Workbook()
    wb.remove(wb.active)
    for title, grid in sheets:
        _write_sheet(wb.create_sheet(), title, grid)

    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
