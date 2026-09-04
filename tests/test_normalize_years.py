# tests/test_normalize_years.py
import math
import pytest
from utils.normalize_years import (
    parse_year_value,
    normalize_years,
    YearParseError,
    YearEmptyError,
)


# --- parse_year_value --------------------------------------------------------

class TestParseYearValueHappyPath:

    def test_single_year_string(self):
        assert parse_year_value("1765") == [1765]

    def test_single_year_int(self):
        assert parse_year_value(1765) == [1765]

    def test_two_digit_range(self):
        assert parse_year_value("1654-55") == [1654, 1655]

    def test_four_digit_range(self):
        assert parse_year_value("1910-1924") == list(range(1910, 1925))

    def test_century_wraparound(self):
        assert parse_year_value("1998-01") == [1998, 1999, 2000, 2001]

    def test_list_input(self):
        assert parse_year_value(["1900", "1901"]) == [1900, 1901]

    def test_list_deduplication(self):
        assert parse_year_value(["1900", "1900"]) == [1900]

    def test_whitespace_around_year(self):
        assert parse_year_value("  1800  ") == [1800]

    def test_whitespace_around_range(self):
        assert parse_year_value("  1800 - 05  ") == list(range(1800, 1806))

    def test_slash_separator(self):
        assert parse_year_value("1852/1876") == [1852, 1876]

    def test_comma_separator(self):
        assert parse_year_value("1954,1955") == [1954, 1955]

    def test_comma_separator_with_spaces(self):
        assert parse_year_value("1954, 1955") == [1954, 1955]

    def test_two_digit_second_year(self):
        assert parse_year_value("1933,35") == [1933, 1935]

    def test_two_digit_century_wraparound(self):
        assert parse_year_value("1998,01") == [1998, 2001]

class TestParseYearValueErrorCases:

    def test_none_raises_empty_error(self):
        with pytest.raises(YearEmptyError):
            parse_year_value(None)

    def test_nan_raises_empty_error(self):
        with pytest.raises(YearEmptyError):
            parse_year_value(float("nan"))

    def test_descending_range_raises(self):
        with pytest.raises(YearParseError):
            parse_year_value("1900-1850")

    def test_negative_year_raises(self):
        with pytest.raises(YearParseError):
            parse_year_value(-1765)

    def test_garbage_string_raises(self):
        with pytest.raises(YearParseError):
            parse_year_value("circa 1900")

    def test_empty_string_raises(self):
        with pytest.raises(YearParseError):
            parse_year_value("")

    def test_unsupported_type_raises(self):
        with pytest.raises(YearParseError):
            parse_year_value({"year": 1900})


# --- normalize_years (safe wrapper) ------------------------------------------

class TestNormalizeYears:

    def test_valid_year_returns_ok(self):
        result = normalize_years("1900")
        assert result["ok"] is True
        assert result["years"] == [1900]
        assert result["error"] is None

    def test_none_returns_empty(self):
        result = normalize_years(None)
        assert result["ok"] is False
        assert result["empty"] is True
        assert result["years"] == []

    def test_nan_returns_empty(self):
        result = normalize_years(float("nan"))
        assert result["ok"] is False
        assert result["empty"] is True

    def test_garbage_returns_not_empty(self):
        result = normalize_years("circa 1900")
        assert result["ok"] is False
        assert result["empty"] is False
        assert result["error"] is not None

    def test_never_raises(self):
        # Should never propagate an exception regardless of input
        for bad in [None, float("nan"), "", "???", -1, {"x": 1}]:
            result = normalize_years(bad)
            assert isinstance(result, dict)
            assert "ok" in result