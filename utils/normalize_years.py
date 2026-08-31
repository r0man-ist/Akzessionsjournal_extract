from __future__ import annotations
import math
import re
from typing import Any, Dict, List, Union


_YEAR_RE = re.compile(r"^\s*(\d{4})\s*$")
_RANGE_RE = re.compile(r"^\s*(\d{4})\s*[-–—]\s*(\d{2}|\d{4})\s*$")


class YearParseError(ValueError):
    """Raised when a year value cannot be parsed."""

class YearEmptyError(YearParseError):
    """Raised specifically when a year value is missing/empty."""

def _expand_range(start_year: int, end_token: str) -> List[int]:
    """
    Expand a year range.

    Examples:
        1654-55   -> 1654..1655
        1910-1924 -> 1910..1924
    """
    if len(end_token) == 4:
        end_year = int(end_token)
    else:
        # Two-digit end year, infer the century from the start year.
        end_year = (start_year // 100) * 100 + int(end_token)
        # Handle wraparound like 1998-01 -> 2001
        if end_year < start_year:
            end_year += 100

    if end_year < start_year:
        raise YearParseError(f"Invalid descending range: {start_year}-{end_year}")

    return list(range(start_year, end_year + 1))


def parse_year_value(value: Any) -> List[int]:
    """
    Parse one value into a list of years.

    Accepted inputs:
      - int: 1765
      - str: "1765", "1654-55", "1910-1924"
      - list/tuple/set of the above, which will be flattened

    Raises:
      YearParseError for unparsable values.
    """
    if value is None:
        raise YearEmptyError("Year value is empty (None)")

    if isinstance(value, float) and math.isnan(value):
        raise YearEmptyError("Year value is empty (NaN)")

    # Already numeric
    if isinstance(value, int):
        if value < 0:
            raise YearParseError(f"Negative year is not allowed: {value}")
        return [value]

    # Flatten list-like inputs
    if isinstance(value, (list, tuple, set)):
        years: List[int] = []
        seen = set()

        for idx, item in enumerate(value):
            try:
                parsed = parse_year_value(item)
            except YearParseError as e:
                raise YearParseError(f"Error at index {idx}: {e}") from e

            for y in parsed:
                if y not in seen:
                    seen.add(y)
                    years.append(y)

        return years

    # Strings: either a single year or a range
    if isinstance(value, str):
        m = _YEAR_RE.match(value)
        if m:
            return [int(m.group(1))]

        m = _RANGE_RE.match(value)
        if m:
            start_year = int(m.group(1))
            end_token = m.group(2)
            return _expand_range(start_year, end_token)

        raise YearParseError(f"Unparsable year value: {value!r}")

    raise YearParseError(f"Unsupported type: {type(value).__name__}")


def normalize_years(value: Any) -> Dict[str, Any]:
    """
    Safe wrapper that never raises.
    Returns:
      {
        "ok": bool,
        "years": list[int],
        "error": str | None,
      }
    """
    try:
        years = parse_year_value(value)
        return {"ok": True, "years": years, "error": None, "empty": False}
    except YearEmptyError as e:
        return {"ok": False, "years": [], "error": str(e), "empty": True}
    except YearParseError as e:
        return {"ok": False, "years": [], "error": str(e), "empty": False}