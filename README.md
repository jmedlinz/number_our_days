# Number Our Days - A Weekly Life Calendar PDF Generator

Generate a one-page PDF life calendar (52 weeks × 90 years) where each row represents a life year starting from your birth date. Squares are filled for completed weeks, the current week is outlined with a thicker border, and CDC-based life-expectancy markers are outlined in red.

Inspired by [Your Life in Weeks — Wait But Why](https://waitbutwhy.com/2014/05/life-weeks.html).

> "So teach us to number our days, that we may get a heart of wisdom." — Psalm 90:12 (ESV)


## Quickstart

```bash
poetry install
poetry run number-our-days
```

Follow the prompts for name, birth date (MM/DD/YYYY), and gender (M/F). The PDF is saved as `number_our_days_<firstname>.pdf` in the current directory.

## Development notes

- Python 3.11+
- Formatting: `black`, `isort`
- Linting: `flake8`
- Tests: `pytest`

## Contact
James Medlin <jmedlin@westervelt.com>
