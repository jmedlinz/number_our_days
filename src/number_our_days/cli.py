from __future__ import annotations

import sys
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Constants derived from recent CDC life expectancy summaries (circa 2023)
MALE_LIFE_EXPECTANCY_YEARS = 75.8
FEMALE_LIFE_EXPECTANCY_YEARS = 81.1
WEEKS_PER_DISPLAY_YEAR = 52
DISPLAY_YEARS = 90
TOTAL_WEEKS = DISPLAY_YEARS * WEEKS_PER_DISPLAY_YEAR


@dataclass
class UserInput:
    first_name: str
    birth_date: date
    gender: str  # "M" or "F"


@dataclass
class CalendarStats:
    birth_week_start: date
    expectancy_weeks: int
    expectancy_week_index_m: int | None
    expectancy_week_index_f: int | None


def iso_week_start(value: date) -> date:
    return value - timedelta(days=value.isoweekday() - 1)


def add_years_safe(d: date, years: int) -> date:
    """Add years to a date, falling back to Feb 28 for leap day birthdays."""
    try:
        return d.replace(year=d.year + years)
    except ValueError:
        return d.replace(month=2, day=28, year=d.year + years)


def parse_birth_date(raw: str) -> date:
    try:
        parsed = datetime.strptime(raw, "%m/%d/%Y").date()
    except ValueError as exc:  # noqa: BLE001
        raise ValueError("Birth date must be in MM/DD/YYYY format and a valid date.") from exc
    return parsed


def collect_user_input(debug: bool = False) -> UserInput:
    today = date.today()

    if debug:
        first = "debug"
        birth_dt = add_years_safe(date.today(), -20)
        gender = "M"
        print(f"DEBUG MODE: Using first_name={first}, birth_date={birth_dt}, gender={gender}")
        print(f"Today: {date.today()}")
        print(f"Birth week start: {iso_week_start(birth_dt)}")
        print(f"Current week start: {iso_week_start(date.today())}")
        days_lived = (date.today() - birth_dt).days
        weeks_lived = days_lived // 7
        print(f"Days lived: {days_lived}, Weeks lived: {weeks_lived}")
        return UserInput(first_name=first, birth_date=birth_dt, gender=gender)

    first = input("Enter your first name: ").strip()
    if not first.isalpha() or len(first) < 2:
        sys.stderr.write("Error: First name must be alphabetic and at least 2 characters.\n")
        sys.exit(1)

    birth_raw = input("Enter your birth date (MM/DD/YYYY): ").strip()
    try:
        birth_dt = parse_birth_date(birth_raw)
    except ValueError as exc:
        sys.stderr.write(f"Error: {exc}\n")
        sys.exit(1)

    if birth_dt >= today:
        sys.stderr.write("Error: Birth date must be in the past.\n")
        sys.exit(1)

    gender_raw = input("Are you male or female? (M/F): ").strip().upper()
    if not gender_raw or gender_raw[0] not in {"M", "F"}:
        sys.stderr.write("Error: Gender must start with M or F.\n")
        sys.exit(1)
    gender = gender_raw[0]

    return UserInput(first_name=first, birth_date=birth_dt, gender=gender)


def compute_stats(user: UserInput) -> CalendarStats:
    birth_week_start = iso_week_start(user.birth_date)

    expectancy_years = MALE_LIFE_EXPECTANCY_YEARS if user.gender == "M" else FEMALE_LIFE_EXPECTANCY_YEARS

    # Align expectancy to grid (52 weeks/year)
    expectancy_row = int(expectancy_years)
    expectancy_col = int((expectancy_years - expectancy_row) * WEEKS_PER_DISPLAY_YEAR)
    base_expectancy_index = expectancy_row * WEEKS_PER_DISPLAY_YEAR + expectancy_col
    expectancy_weeks = base_expectancy_index

    expectancy_week_index_m = base_expectancy_index if user.gender == "M" else None
    expectancy_week_index_f = base_expectancy_index if user.gender == "F" else None

    return CalendarStats(
        birth_week_start=birth_week_start,
        expectancy_weeks=expectancy_weeks,
        expectancy_week_index_m=expectancy_week_index_m,
        expectancy_week_index_f=expectancy_week_index_f,
    )


def draw_pdf(user: UserInput, stats: CalendarStats, output_path: Path) -> None:
    c = canvas.Canvas(str(output_path), pagesize=letter)
    width, height = letter
    today = date.today()

    left_margin = 36
    right_margin = 36
    top_margin = 54
    bottom_margin = 54
    legend_space = 50
    center_x = width / 2

    title_y = height - top_margin
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(center_x, title_y, "Number Our Days")
    c.setFont("Helvetica", 8)
    current_date = today.strftime("%B %d, %Y")
    date_subtitle = f"Life Calendar for {user.first_name}, created on {current_date}"
    c.drawCentredString(center_x, title_y - 18, date_subtitle)

    verse = '"So teach us to number our days, that we may get a heart of wisdom." — Psalm 90:12 (ESV)'
    c.drawCentredString(center_x, title_y - 32, verse)

    subtitle = "Each square represents one week. Each line represents one year. Each block represents a decade."
    c.drawCentredString(center_x, title_y - 46, subtitle)

    grid_top_max = title_y - 60
    grid_bottom_min = bottom_margin + legend_space

    available_height = grid_top_max - grid_bottom_min
    available_width = width - left_margin - right_margin

    cell_size = min(available_width / WEEKS_PER_DISPLAY_YEAR, available_height / DISPLAY_YEARS)
    decade_gap = cell_size * 0.35
    needed_height = DISPLAY_YEARS * cell_size + (DISPLAY_YEARS // 10 - 1) * decade_gap
    if needed_height > available_height:
        scale = available_height / needed_height
        cell_size *= scale
        decade_gap *= scale
        needed_height = DISPLAY_YEARS * cell_size + (DISPLAY_YEARS // 10 - 1) * decade_gap

    # Center the grid horizontally and vertically
    actual_grid_height = DISPLAY_YEARS * cell_size + (DISPLAY_YEARS // 10 - 1) * decade_gap
    grid_top = grid_bottom_min + actual_grid_height
    grid_width = WEEKS_PER_DISPLAY_YEAR * cell_size
    grid_left = (width - grid_width) / 2

    def row_y(row_idx: int) -> float:
        decade_jumps = row_idx // 10
        return grid_top - (row_idx + 1) * cell_size - decade_jumps * decade_gap

    expectancy_m = stats.expectancy_week_index_m
    expectancy_f = stats.expectancy_week_index_f

    # Precompute current and lived week markers
    age_years = today.year - user.birth_date.year
    if today < add_years_safe(user.birth_date, age_years):
        age_years -= 1
    life_year_start = add_years_safe(user.birth_date, age_years)
    weeks_since_life_year_start = max((today - life_year_start).days // 7, 0)
    current_row_birth = age_years
    current_col_birth = weeks_since_life_year_start
    lived_index_birth = age_years * WEEKS_PER_DISPLAY_YEAR + weeks_since_life_year_start

    for week_index in range(TOTAL_WEEKS):
        row = week_index // WEEKS_PER_DISPLAY_YEAR
        col = week_index % WEEKS_PER_DISPLAY_YEAR
        if row >= DISPLAY_YEARS:
            break

        x = grid_left + col * cell_size
        y = row_y(row)

        # Determine current/lived status
        # Current week sticks to birth-based week index until the first 7 days complete
        is_current_week = row == current_row_birth and col == current_col_birth
        is_lived = week_index < lived_index_birth

        c.setStrokeColor(colors.black)
        c.setLineWidth(1)

        if is_lived:
            c.setFillColor(HexColor("#AAAAAA"))
        else:
            c.setFillColor(colors.white)
        c.rect(x, y, cell_size, cell_size, stroke=1, fill=1)

        if is_current_week:
            c.setFillColor(colors.blue)
            c.setStrokeColor(colors.black)
            c.setLineWidth(1)
            c.rect(x, y, cell_size, cell_size, stroke=1, fill=1)
            # Draw white diamond in center
            diamond_size = cell_size * 0.3
            center_x_cell = x + cell_size / 2
            center_y_cell = y + cell_size / 2
            p = c.beginPath()
            p.moveTo(center_x_cell, center_y_cell + diamond_size)
            p.lineTo(center_x_cell + diamond_size, center_y_cell)
            p.lineTo(center_x_cell, center_y_cell - diamond_size)
            p.lineTo(center_x_cell - diamond_size, center_y_cell)
            p.close()
            c.setFillColor(colors.white)
            c.setStrokeColor(colors.white)
            c.drawPath(p, stroke=1, fill=1)

        if (expectancy_m is not None and week_index == expectancy_m) or (
            expectancy_f is not None and week_index == expectancy_f
        ):
            # Draw red X across the box
            margin = cell_size * 0.15
            c.setStrokeColor(colors.red)
            c.setLineWidth(1.5)
            # Draw diagonal lines forming an X
            c.line(x + margin, y + margin, x + cell_size - margin, y + cell_size - margin)
            c.line(x + margin, y + cell_size - margin, x + cell_size - margin, y + margin)
            c.setStrokeColor(colors.black)
            c.setLineWidth(1)

    # Draw decade labels
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 8)
    grid_right = grid_left + WEEKS_PER_DISPLAY_YEAR * cell_size
    for decade in range(10, DISPLAY_YEARS + 1, 10):
        row = decade - 1  # Show label at bottom of each decade block
        if row >= DISPLAY_YEARS:
            continue
        y = row_y(row) + cell_size / 2
        c.drawString(grid_right + 6, y - 3, str(decade))

    # Reset to black for drawing
    c.setFillColor(colors.black)
    c.setStrokeColor(colors.black)

    # Get life expectancy for legend
    expectancy_years = MALE_LIFE_EXPECTANCY_YEARS if user.gender == "M" else FEMALE_LIFE_EXPECTANCY_YEARS

    # Draw Legend to the right of grid, aligned at top
    legend_x = grid_left + WEEKS_PER_DISPLAY_YEAR * cell_size + 32
    legend_y_start = grid_top - cell_size
    box_size = 8
    box_spacing = 14
    text_x = legend_x + 12

    c.setFont("Helvetica", 7)

    # Gray box - Weeks already lived
    y1 = legend_y_start
    c.setFillColor(HexColor("#AAAAAA"))
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(legend_x, y1 - 6, box_size, box_size, stroke=1, fill=1)
    c.setFillColor(colors.black)
    c.drawString(text_x, y1 - 4, "Weeks already lived")

    # White box - Weeks to be lived
    y2 = y1 - box_spacing
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(legend_x, y2 - 6, box_size, box_size, stroke=1, fill=1)
    c.setFillColor(colors.black)
    c.drawString(text_x, y2 - 4, "Weeks to be lived")

    # Blue box with white diamond - Current week
    y3 = y2 - box_spacing
    c.setFillColor(colors.blue)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(legend_x, y3 - 6, box_size, box_size, stroke=1, fill=1)
    # Draw small white diamond
    diamond_size = box_size * 0.4
    center_x_diamond = legend_x + box_size / 2
    center_y_diamond = y3 - 2
    p = c.beginPath()
    p.moveTo(center_x_diamond, center_y_diamond + diamond_size)
    p.lineTo(center_x_diamond + diamond_size, center_y_diamond)
    p.lineTo(center_x_diamond, center_y_diamond - diamond_size)
    p.lineTo(center_x_diamond - diamond_size, center_y_diamond)
    p.close()
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.white)
    c.drawPath(p, stroke=0, fill=1)
    c.setFillColor(colors.black)
    c.drawString(text_x, y3 - 4, "Current week")

    # White box with red X - Life expectancy
    y4 = y3 - box_spacing
    c.setFillColor(colors.white)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.rect(legend_x, y4 - 6, box_size, box_size, stroke=1, fill=1)
    # Draw red X
    margin = box_size * 0.1
    c.setStrokeColor(colors.red)
    c.setLineWidth(1)
    c.line(legend_x + margin, y4 - 6 + margin, legend_x + box_size - margin, y4 - 6 + box_size - margin)
    c.line(legend_x + margin, y4 - 6 + box_size - margin, legend_x + box_size - margin, y4 - 6 + margin)
    c.setFillColor(colors.black)
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.5)
    c.drawString(text_x, y4 - 4, f"Life expectancy: {expectancy_years}")

    # Draw box around legend
    legend_padding = 6
    legend_width = text_x + 85 - (legend_x - legend_padding)
    legend_height = legend_y_start - (y4 - 6) + legend_padding * 2
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.rect(legend_x - legend_padding, y4 - 6 - legend_padding, legend_width, legend_height, stroke=1, fill=0)

    # Draw Summary below grid centered
    info_y = grid_bottom_min - 28
    summary_col_x = center_x

    # Use grid-aligned lived week count so summary matches shading
    display_weeks_lived = max(lived_index_birth, 0)

    weeks_remaining = max(stats.expectancy_weeks - display_weeks_lived, 0)
    percent_lived = (
        0.0 if stats.expectancy_weeks == 0 else min(display_weeks_lived / stats.expectancy_weeks * 100, 100.0)
    )
    days_lived_total = (today - user.birth_date).days
    age_years_exact = days_lived_total / 365.2425

    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(summary_col_x, info_y, "Summary")
    c.setFont("Helvetica", 7)
    c.drawCentredString(summary_col_x, info_y - 12, f"Weeks lived: {display_weeks_lived}")
    c.drawCentredString(summary_col_x, info_y - 22, f"Weeks remaining: {weeks_remaining}")
    c.drawCentredString(summary_col_x, info_y - 32, f"Percent of life lived: {percent_lived:.1f}%")
    c.drawCentredString(summary_col_x, info_y - 42, f"Age: {age_years_exact:.2f} years")

    # Draw box around summary
    summary_padding = 4
    summary_width = legend_width  # Same width as legend
    summary_height = info_y + summary_padding + 8 - (info_y - 42 - summary_padding)
    summary_left = summary_col_x - summary_width / 2
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.rect(summary_left, info_y - 42 - summary_padding, summary_width, summary_height, stroke=1, fill=0)

    c.showPage()
    c.save()


def main() -> None:
    debug_mode = "--debug" in sys.argv
    user = collect_user_input(debug=debug_mode)
    stats = compute_stats(user)

    filename = f"number_our_days_{user.first_name.lower()}.pdf"
    output_path = Path(filename)

    draw_pdf(user, stats, output_path)
    print(f"Created {filename}")


if __name__ == "__main__":
    main()
