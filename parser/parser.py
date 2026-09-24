import re


def extract_amount(value):

    if not value:
        return None

    value = value.replace(",", "")

    match = re.search(
        r"\d+(?:\.\d{1,2})?",
        value
    )

    if match:
        try:
            return float(match.group())
        except ValueError:
            return None

    return None


def parse_invoice(text):

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    result = {
        "invoice_number": None,
        "vendor": None,
        "invoice_date": None,
        "subtotal": None,
        "tax": None,
        "total": None
    }

    # -------------------------
    # Invoice Number
    # -------------------------

    patterns = [
        r"(?:invoice|inv)[\s:#-]*(?:no|number)?[\s:#-]*([A-Za-z0-9/-]+)",
        r"order[\s:#-]*(\w+)"
    ]

    for pattern in patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            result["invoice_number"] = match.group(1)
            break

    # -------------------------
    # Date
    # -------------------------

    date_patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b"
    ]

    for pattern in date_patterns:

        match = re.search(
            pattern,
            text
        )

        if match:
            result["invoice_date"] = match.group()
            break

    # -------------------------
    # Total
    # -------------------------

    total_patterns = [
        r"total\s*[:\-]?\s*[₹$]?\s*([\d,]+(?:\.\d{1,2})?)",
        r"grand\s+total\s*[:\-]?\s*[₹$]?\s*([\d,]+(?:\.\d{1,2})?)"
    ]

    for pattern in total_patterns:

        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            result["total"] = extract_amount(
                match.group(1)
            )
            break

    # -------------------------
    # Subtotal
    # -------------------------

    match = re.search(
        r"subtotal\s*[:\-]?\s*[₹$]?\s*([\d,]+(?:\.\d{1,2})?)",
        text,
        re.IGNORECASE
    )

    if match:
        result["subtotal"] = extract_amount(
            match.group(1)
        )

    # -------------------------
    # Tax
    # -------------------------

    match = re.search(
        r"(?:tax|gst|cgst|sgst)\s*[:\-]?\s*[₹$]?\s*([\d,]+(?:\.\d{1,2})?)",
        text,
        re.IGNORECASE
    )

    if match:
        result["tax"] = extract_amount(
            match.group(1)
        )

    # -------------------------
    # Vendor
    # -------------------------

    ignored_words = [
        "invoice",
        "total",
        "subtotal",
        "tax",
        "gst",
        "order",
        "date",
        "amount"
    ]

    for line in lines[:6]:

        lower = line.lower()

        if (
            len(line) >= 3
            and not any(word in lower for word in ignored_words)
            and not re.search(r"\d{3,}", line)
        ):
            result["vendor"] = line
            break

    return result