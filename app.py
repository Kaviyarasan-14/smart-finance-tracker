from flask import Flask, render_template, request, session, redirect, send_file
import mysql.connector

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from datetime import date


app = Flask(__name__)
app.secret_key = "smartfinancekey"

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="9788",
    database="smart_finance_tracker"
)

cursor = connection.cursor()

# ALWAYS OPEN LOGIN PAGE FIRST

@app.route("/")
def main():

    return redirect("/login")

# DASHBOARD

@app.route("/dashboard")
def home():

    if "user" not in session:
        return redirect("/login")

    # TOTAL EXPENSE

    expense_query = """
    SELECT SUM(amount)
    FROM expenses
    WHERE user_id=%s
    """

    cursor.execute(
        expense_query,
        (session["user_id"],)
    )

    total_expense = cursor.fetchone()[0]

    if total_expense is None:
        total_expense = 0

    # TOTAL INCOME

    income_query = """
    SELECT SUM(amount)
    FROM user_income
    WHERE user_id=%s
    """

    cursor.execute(
        income_query,
        (session["user_id"],)
    )

    total_income = cursor.fetchone()[0]

    if total_income is None:
        total_income = 0

    # BALANCE

    remaining_balance = total_income - total_expense

    # PIE CHART

    chart_query = """
    SELECT category, SUM(amount)
    FROM expenses
    WHERE user_id=%s
    GROUP BY category
    """

    cursor.execute(
        chart_query,
        (session["user_id"],)
    )

    chart_data = cursor.fetchall()

    categories = []
    amounts = []

    for row in chart_data:

        categories.append(row[0])
        amounts.append(float(row[1]))

    # MONTHLY CHART

    monthly_query = """
    SELECT 
        MONTHNAME(expense_date),
        SUM(amount)
    FROM expenses
    WHERE user_id=%s
    GROUP BY MONTH(expense_date), MONTHNAME(expense_date)
    ORDER BY MONTH(expense_date)
    """

    cursor.execute(
        monthly_query,
        (session["user_id"],)
    )

    monthly_data = cursor.fetchall()

    months = []
    monthly_amounts = []

    for row in monthly_data:

        months.append(row[0])
        monthly_amounts.append(float(row[1]))

    # BUDGET WARNING

    warning_messages = []

    budget_query = """
    SELECT 
        budgets.category,
        budgets.budget_amount,
        SUM(expenses.amount)
    FROM budgets
    JOIN expenses
    ON budgets.category = expenses.category
    WHERE budgets.user_id=%s
    AND expenses.user_id=%s
    GROUP BY budgets.category, budgets.budget_amount
    """

    cursor.execute(
        budget_query,
        (session["user_id"], session["user_id"])
    )

    budget_data = cursor.fetchall()

    for row in budget_data:

        category = row[0]
        budget_limit = float(row[1])
        spent_amount = float(row[2])

        if spent_amount > budget_limit:

            warning_messages.append(
                f"⚠ {category} budget exceeded!"
            )
                # TOTAL TRANSACTIONS

    transaction_query = """
    SELECT COUNT(*)
    FROM expenses
    WHERE user_id=%s
    """

    cursor.execute(
        transaction_query,
        (session["user_id"],)
    )

    total_transactions = cursor.fetchone()[0]

    # TOP SPENDING CATEGORY

    top_category_query = """
    SELECT category, SUM(amount) as total
    FROM expenses
    WHERE user_id=%s
    GROUP BY category
    ORDER BY total DESC
    LIMIT 1
    """

    cursor.execute(
        top_category_query,
        (session["user_id"],)
    )

    top_category_data = cursor.fetchone()

    if top_category_data:

        top_category = top_category_data[0]
        top_amount = float(top_category_data[1])

    else:

        top_category = "None"
        top_amount = 0

    return render_template(
        "index.html",
        total_expense=total_expense,
        total_income=total_income,
        remaining_balance=remaining_balance,
        categories=categories,
        amounts=amounts,
        months=months,
        monthly_amounts=monthly_amounts,
        warning_messages=warning_messages,
        total_transactions=total_transactions,
        top_category=top_category,
        top_amount=top_amount
    )

# ADD EXPENSE

@app.route("/add-expense", methods=["GET", "POST"])
def add_expense():

    if "user" not in session:
        return redirect("/login")

    # DEFAULT DATE

    if "selected_date" not in session:
        session["selected_date"] = str(date.today())

    if request.method == "POST":

        title = request.form["title"]
        category = request.form["category"]
        amount = request.form["amount"]
        expense_date = request.form["expense_date"]

        # SAVE DATE IN SESSION

        session["selected_date"] = expense_date

        user_id = session["user_id"]

        query = """
        INSERT INTO expenses(
            title,
            category,
            amount,
            expense_date,
            user_id
        )
        VALUES(%s, %s, %s, %s, %s)
        """

        values = (
            title,
            category,
            amount,
            expense_date,
            user_id
        )

        cursor.execute(query, values)

        connection.commit()

        return render_template(
            "add_expense.html",
            success="Expense Added!",
            selected_date=session["selected_date"]
        )

    return render_template(
        "add_expense.html",
        selected_date=session["selected_date"]
    )
# HISTORY

@app.route("/history")
def history():

    if "user" not in session:
        return redirect("/login")

    search = request.args.get("search")

    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")

    # DATE FILTER

    if from_date and to_date:

        query = """
        SELECT * FROM expenses
        WHERE user_id=%s
        AND expense_date BETWEEN %s AND %s
        """

        cursor.execute(
            query,
            (
                session["user_id"],
                from_date,
                to_date
            )
        )

    # SEARCH FILTER

    elif search:

        query = """
        SELECT * FROM expenses
        WHERE user_id=%s
        AND (
            title LIKE %s
            OR category LIKE %s
        )
        """

        search_value = f"%{search}%"

        cursor.execute(
            query,
            (
                session["user_id"],
                search_value,
                search_value
            )
        )

    # NORMAL HISTORY

    else:

        query = """
        SELECT * FROM expenses
        WHERE user_id=%s
        """

        cursor.execute(
            query,
            (session["user_id"],)
        )

    expenses = cursor.fetchall()

    return render_template(
        "history.html",
        expenses=expenses
    )
# DELETE EXPENSE

@app.route("/delete/<int:id>")
def delete_expense(id):

    query = "DELETE FROM expenses WHERE id=%s"

    cursor.execute(query, (id,))

    connection.commit()

    return redirect("/history")

# ADD INCOME

@app.route("/add-income", methods=["GET", "POST"])
def add_income():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        source = request.form["source"]
        amount = request.form["amount"]
        income_date = request.form["income_date"]

        user_id = session["user_id"]

        query = """
        INSERT INTO user_income(
            source,
            amount,
            income_date,
            user_id
        )
        VALUES(%s, %s, %s, %s)
        """

        values = (
            source,
            amount,
            income_date,
            user_id
        )

        cursor.execute(query, values)

        connection.commit()

        return redirect("/dashboard")

    return render_template("add_income.html")

# EDIT EXPENSE

@app.route("/edit/<int:id>", methods=["GET", "POST"])
def edit_expense(id):

    if request.method == "POST":

        title = request.form["title"]
        category = request.form["category"]
        amount = request.form["amount"]
        expense_date = request.form["expense_date"]

        update_query = """
        UPDATE expenses
        SET title=%s,
            category=%s,
            amount=%s,
            expense_date=%s
        WHERE id=%s
        """

        values = (
            title,
            category,
            amount,
            expense_date,
            id
        )

        cursor.execute(update_query, values)

        connection.commit()

        return redirect("/history")

    select_query = """
    SELECT * FROM expenses
    WHERE id=%s
    """

    cursor.execute(select_query, (id,))

    expense = cursor.fetchone()

    return render_template(
        "edit_expense.html",
        expense=expense
    )

# REGISTER

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        # CHECK EXISTING USERNAME

        check_query = """
        SELECT * FROM users
        WHERE username=%s
        """

        cursor.execute(check_query, (username,))

        existing_user = cursor.fetchone()

        # IF USERNAME EXISTS

        if existing_user:

            return render_template(
                "register.html",
                error="Username already exists!"
            )

        # INSERT NEW USER

        query = """
        INSERT INTO users(username, password)
        VALUES(%s, %s)
        """

        values = (username, password)

        cursor.execute(query, values)

        connection.commit()

        return redirect("/login")

    return render_template("register.html")

# LOGIN

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        query = """
        SELECT * FROM users
        WHERE username=%s
        AND password=%s
        """

        values = (username, password)

        cursor.execute(query, values)

        user = cursor.fetchone()

        if user:

            session["user"] = username
            session["user_id"] = user[0]

            return redirect("/dashboard")

        else:

            return render_template(
    "login.html",
    error="Invalid Username or Password"
)

    return render_template("login.html")

# LOGOUT

@app.route("/logout")
def logout():

    session.pop("user", None)
    session.pop("user_id", None)

    return redirect("/login")

# ADD BUDGET

@app.route("/add-budget", methods=["GET", "POST"])
def add_budget():

    if "user" not in session:
        return redirect("/login")

    if request.method == "POST":

        category = request.form["category"]
        budget_amount = request.form["budget_amount"]

        query = """
        INSERT INTO budgets(
            category,
            budget_amount,
            user_id
        )
        VALUES(%s, %s, %s)
        """

        values = (
            category,
            budget_amount,
            session["user_id"]
        )

        cursor.execute(query, values)

        connection.commit()

        return redirect("/dashboard")

    return render_template("add_budget.html")

# PDF REPORT

@app.route("/download-report")
def download_report():

    if "user" not in session:
        return redirect("/login")

    query = """
    SELECT title, category, amount, expense_date
    FROM expenses
    WHERE user_id=%s
    """

    cursor.execute(
        query,
        (session["user_id"],)
    )

    expenses = cursor.fetchall()

    pdf_file = "expense_report.pdf"

    doc = SimpleDocTemplate(pdf_file)

    styles = getSampleStyleSheet()

    elements = []

    title = Paragraph(
        "Smart Finance Expense Report",
        styles['Title']
    )

    elements.append(title)

    elements.append(Spacer(1, 20))

    for expense in expenses:

        text = f"""
        Title: {expense[0]} <br/>
        Category: {expense[1]} <br/>
        Amount: ₹{expense[2]} <br/>
        Date: {expense[3]} <br/><br/>
        """

        paragraph = Paragraph(
            text,
            styles['BodyText']
        )

        elements.append(paragraph)

    doc.build(elements)

    return send_file(
        pdf_file,
        as_attachment=True
    )

# RUN APP

if __name__ == "__main__":
    app.run(debug=True)