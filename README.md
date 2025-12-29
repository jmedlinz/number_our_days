# Life Calendar PDF Generator

Generate a one-page PDF life calendar (52 weeks × 90 years) using ISO week arithmetic. Squares are filled for completed weeks, the current week is outlined with a thicker border, and CDC-based life-expectancy markers are outlined in red. The script supports two generation modes: `START_AT_BIRTH` (anchor on your birth week) and `START_IN_JAN` (anchor on ISO week 1 of your birth year; pre-birth weeks are invisible).

## Quickstart

```bash
poetry install
poetry run life-calendar
```

Follow the prompts for name, birth date (MM/DD/YYYY), gender (M/F), and start mode. The PDF is saved as `life_calendar_<firstname>.pdf` in the current directory.

## Development notes

- Python 3.11+
- Formatting: `black`, `isort`
- Linting: `flake8`
- Tests: `pytest`

## Contact
James Medlin <jmedlin@westervelt.com>
