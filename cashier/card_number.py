"""Card-number checks for card payments (the cashier types the number in Order Entry)."""

CARD_METHOD = "Card"        # the PaymentFactory name that needs a card number
MIN_DIGITS, MAX_DIGITS = 13, 19
REQUIRE_LUHN = False         # set False if you want to accept any 13-19 digit number (e.g. for a demo)


def clean_card_number(text):
    """Digits only (spaces and dashes the cashier typed are dropped)."""
    return "".join(ch for ch in (text or "") if ch.isascii() and ch.isdigit())


def _passes_luhn(digits):
    total = 0
    for position, ch in enumerate(reversed(digits)):
        value = int(ch)
        if position % 2 == 1:
            value *= 2
            if value > 9:
                value -= 9
        total += value
    return total % 10 == 0


def card_number_problem(text):
    """None when the number is acceptable, otherwise a message safe to show the cashier."""
    digits = clean_card_number(text)
    if not digits:
        return "Enter the customer's card number first."
    if not MIN_DIGITS <= len(digits) <= MAX_DIGITS:
        return f"A card number has {MIN_DIGITS} to {MAX_DIGITS} digits."
    if REQUIRE_LUHN and not _passes_luhn(digits):
        return "That card number does not look valid. Please check the digits."
    return None


def last_four(text):
    """The last 4 digits, the only part of the number that is ever saved."""
    return clean_card_number(text)[-4:]
