import secrets
import string


AMBIGUOUS_CHARS = set("0O1lI|`'\"{}[]()/\\")
SYMBOLS = "!@#$%^&*-_=+.,:;?"


def _clean_charset(chars: str, avoid_ambiguous: bool) -> str:
    if not avoid_ambiguous:
        return chars
    return "".join(ch for ch in chars if ch not in AMBIGUOUS_CHARS)


def generate_password(
    length: int = 20,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
    avoid_ambiguous: bool = True,
) -> str:
    groups = []
    if use_upper:
        groups.append(_clean_charset(string.ascii_uppercase, avoid_ambiguous))
    if use_lower:
        groups.append(_clean_charset(string.ascii_lowercase, avoid_ambiguous))
    if use_digits:
        groups.append(_clean_charset(string.digits, avoid_ambiguous))
    if use_symbols:
        groups.append(_clean_charset(SYMBOLS, avoid_ambiguous))

    groups = [group for group in groups if group]
    if not groups:
        raise ValueError("At least one character group must be enabled.")
    if length < len(groups):
        raise ValueError("Password length is too short for the selected character groups.")

    password_chars = [secrets.choice(group) for group in groups]
    all_chars = "".join(groups)
    password_chars.extend(secrets.choice(all_chars) for _ in range(length - len(password_chars)))
    secrets.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)
