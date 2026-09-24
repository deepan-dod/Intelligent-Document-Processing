def validate_invoice(data):

    subtotal = data.get("subtotal") or 0
    tax = data.get("tax") or 0
    total = data.get("total") or 0

    problems = []

    if total <= 0:
        problems.append(
            "Total amount could not be detected."
        )

    if subtotal > 0 and total > 0 and tax > 0:

        expected = subtotal + tax

        if abs(expected - total) > 1:
            problems.append(
                "Subtotal + tax does not match total."
            )

    if problems:
        return {
            "valid": False,
            "message": " ".join(problems)
        }

    return {
        "valid": True,
        "message": "Invoice passed basic validation."
    }