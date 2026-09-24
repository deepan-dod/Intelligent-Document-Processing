from datetime import datetime, timedelta
from database.database import Expense


def get_weekly_expenses(user_id):

    today = datetime.utcnow().date()

    start_date = today - timedelta(days=6)

    expenses = Expense.query.filter(
        Expense.user_id == user_id
    ).all()

    result = {}

    for i in range(7):

        day = start_date + timedelta(days=i)

        result[str(day)] = 0

    for expense in expenses:

        if not expense.expense_date:
            continue

        try:

            date_value = datetime.strptime(
                expense.expense_date,
                "%Y-%m-%d"
            ).date()

            if date_value in [
                start_date + timedelta(days=i)
                for i in range(7)
            ]:

                result[str(date_value)] += (
                    expense.amount or 0
                )

        except ValueError:
            continue

    return result