def validate_deposit_settings(
        deposit_required: bool,
        deposit_amount: int | None,
) -> int | None:
    """Returns the amount to actually persist — enforces that a
    required deposit needs a positive amount, and a non-required one
    never carries a stale amount."""
    if deposit_required:
        if deposit_amount is None or deposit_amount <= 0:
            raise ValueError(
                "deposit_amount must be a positive number when deposit_required is true"
            )
        return deposit_amount

    return None
