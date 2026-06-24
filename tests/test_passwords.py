import pytest

from src.passwords import AMBIGUOUS_CHARS, generate_password


def test_generate_password_length_and_groups():
    password = generate_password(length=24)

    assert len(password) == 24
    assert any(ch.isupper() for ch in password)
    assert any(ch.islower() for ch in password)
    assert any(ch.isdigit() for ch in password)
    assert any(not ch.isalnum() for ch in password)
    assert not any(ch in AMBIGUOUS_CHARS for ch in password)


def test_generate_password_rejects_impossible_length():
    with pytest.raises(ValueError):
        generate_password(length=3, use_upper=True, use_lower=True, use_digits=True, use_symbols=True)


def test_generate_password_rejects_empty_charset():
    with pytest.raises(ValueError):
        generate_password(use_upper=False, use_lower=False, use_digits=False, use_symbols=False)
