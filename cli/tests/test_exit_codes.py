"""Exit code constants — one test per code per §9.2."""

from ocmo_cli._exit import (
    AUTH_ERROR,
    CONFLICT,
    FAILURE,
    HOOK_FAILURE,
    INTERRUPTED,
    LOCKED,
    NOT_FOUND,
    SUCCESS,
    USAGE_ERROR,
    VALIDATION_ERROR,
    VERIFY_FAILURE,
)


def test_exit_codes_values() -> None:
    assert SUCCESS == 0
    assert FAILURE == 1
    assert USAGE_ERROR == 2
    assert NOT_FOUND == 3
    assert AUTH_ERROR == 4
    assert CONFLICT == 5
    assert LOCKED == 6
    assert VALIDATION_ERROR == 7
    assert HOOK_FAILURE == 8
    assert VERIFY_FAILURE == 9
    assert INTERRUPTED == 130
