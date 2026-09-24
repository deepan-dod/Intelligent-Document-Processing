from database.database import Expense


def answer_question(user_id, question):

    question = question.lower()

    expenses = Expense.query.filter_by(
        user_id=user_id
    ).all()

    if not expenses:

        return (
            "I don't have enough expense data yet. "
            "Upload a few invoices first and I'll "
            "analyze your spending."
        )

    total = sum(
        expense.amount or 0
        for expense in expenses
    )

    category_totals = {}

    for expense in expenses:

        category = (
            expense.category
            or "Other"
        )

        category_totals[category] = (
            category_totals.get(category, 0)
            + (expense.amount or 0)
        )

    highest_category = max(
        category_totals,
        key=category_totals.get
    )

    highest_amount = category_totals[
        highest_category
    ]

    if "most" in question or "highest" in question:

        return (
            f"Your highest spending category is "
            f"{highest_category}, with ₹{highest_amount:.2f}."
        )

    if "total" in question:

        return (
            f"Your total recorded spending is "
            f"₹{total:.2f}."
        )

    if "reduce" in question or "save" in question:

        return (
            f"Your largest spending category is "
            f"{highest_category}. Reviewing expenses "
            f"in this category may help identify "
            f"potential savings."
        )

    return (
        f"You currently have {len(expenses)} "
        f"recorded expenses totaling ₹{total:.2f}."
    )