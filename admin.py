import streamlit as st
import pandas as pd
import datetime
from database import (
    get_connection,
    fetch_one,
    fetch_all,
    record_exists
)

# ==========================================================
# LIBRARY RULES / CONSTANTS
# ==========================================================

LOAN_PERIOD_DAYS = 14      # a book is due 14 days after issue
FINE_PER_DAY = 5           # ₹5 fine per day overdue
MAX_BOOKS_PER_STUDENT = 3  # a student can hold at most 3 books at once


def get_due_date(issue_date):
    """Return the due date for a book issued on issue_date."""
    return issue_date + datetime.timedelta(days=LOAN_PERIOD_DAYS)


def calculate_fine(issue_date, return_date=None):
    """
    Calculate the fine (in ₹) for a book.
    If return_date is None, fine is calculated as of today (still held).
    """
    due_date = get_due_date(issue_date)
    end_date = return_date or datetime.date.today()

    late_days = (end_date - due_date).days

    return max(late_days, 0) * FINE_PER_DAY


def get_active_issue_count(roll_no):
    """How many books a student currently has issued (not yet returned)."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT COUNT(*) FROM issued_books WHERE roll_no=%s AND return_date IS NULL",
        (roll_no,)
    )

    count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return count


def is_book_issued_to_student(roll_no, book_id):
    """Check if this exact book is already issued (and not returned) to this student."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COUNT(*) FROM issued_books
        WHERE roll_no=%s AND book_id=%s AND return_date IS NULL
        """,
        (roll_no, book_id)
    )

    count = cursor.fetchone()[0]

    cursor.close()
    conn.close()

    return count > 0



# ==========================================================
# ADD BOOK
# ==========================================================

def add_book(book_id, book_name, author, category, quantity):

    if not all([book_id, book_name, author, category]):
        st.warning("All fields are required.")
        return False

    if quantity <= 0:
        st.warning("Quantity must be greater than zero.")
        return False

    if record_exists(
        "SELECT book_id FROM books WHERE book_id=%s",
        (book_id,)
    ):
        st.error("Book ID already exists.")
        return False

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
        INSERT INTO books
        (book_id,book_name,author,category,quantity)
        VALUES(%s,%s,%s,%s,%s)
        """,
        (book_id,book_name,author,category,quantity))

        conn.commit()

        st.success("Book Added Successfully ✔")
        return True

    except Exception as e:

        conn.rollback()
        st.error(e)
        return False

    finally:

        cursor.close()
        conn.close()


# ==========================================================
# REGISTER STUDENT
# ==========================================================

def register_student(name, roll_no, course):

    if not all([name, roll_no, course]):
        st.warning("Fill all fields.")
        return False

    if record_exists(
        "SELECT roll_no FROM students WHERE roll_no=%s",
        (roll_no,)
    ):
        st.error("Roll Number already exists.")
        return False

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute("""
        INSERT INTO students
        (name,roll_no,course)
        VALUES(%s,%s,%s)
        """,
        (name,roll_no,course))

        cursor.execute("""
        INSERT INTO users
        (username,password,role,roll_no)
        VALUES(%s,%s,'Student',%s)
        """,
        (roll_no,"1234",roll_no))

        conn.commit()

        st.success("Student Registered Successfully ✔")
        return True

    except Exception as e:

        conn.rollback()
        st.error(e)
        return False

    finally:

        cursor.close()
        conn.close()


# ==========================================================
# REMOVE STUDENT
# ==========================================================

def remove_student(roll_no):

    if not roll_no:

        st.warning("Enter Roll Number")
        return

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "SELECT * FROM students WHERE roll_no=%s",
            (roll_no,)
        )

        student = cursor.fetchone()

        if not student:

            st.error("Student not found.")
            return

        cursor.execute("""
        SELECT COUNT(*)
        FROM issued_books
        WHERE roll_no=%s
        AND return_date IS NULL
        """,
        (roll_no,))

        active = cursor.fetchone()[0]

        if active > 0:

            st.error(
                f"Student has {active} issued book(s)."
            )

            return

        cursor.execute(
            "DELETE FROM users WHERE roll_no=%s",
            (roll_no,)
        )

        cursor.execute(
            "DELETE FROM students WHERE roll_no=%s",
            (roll_no,)
        )

        conn.commit()

        st.success("Student Removed ✔")

    except Exception as e:

        conn.rollback()
        st.error(e)

    finally:

        cursor.close()
        conn.close()


# ==========================================================
# ISSUE BOOK
# ==========================================================

def issue_book(roll_no, book_id, issue_date):

    if not all([roll_no, book_id]):

        st.warning("Enter Roll Number and Book ID.")
        return

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            "SELECT * FROM students WHERE roll_no=%s",
            (roll_no,)
        )

        if cursor.fetchone() is None:

            st.error("Student not found.")
            return

        cursor.execute(
            "SELECT quantity FROM books WHERE book_id=%s",
            (book_id,)
        )

        book = cursor.fetchone()

        if book is None:

            st.error("Book not found.")
            return

        if book[0] <= 0:

            st.error("Book Out of Stock.")
            return

        # ---- Business rule: student can't hold too many books ----
        active_count = get_active_issue_count(roll_no)

        if active_count >= MAX_BOOKS_PER_STUDENT:

            st.error(
                f"Student already has {active_count} book(s) issued. "
                f"Maximum allowed is {MAX_BOOKS_PER_STUDENT}. Please return a book first."
            )
            return

        # ---- Business rule: same book can't be issued twice to same student ----
        if is_book_issued_to_student(roll_no, book_id):

            st.error("This book is already issued to this student and not yet returned.")
            return

        cursor.execute("""
        INSERT INTO issued_books
        (roll_no,book_id,issue_date)
        VALUES(%s,%s,%s)
        """,
        (roll_no,book_id,issue_date))

        cursor.execute("""
        UPDATE books
        SET quantity=quantity-1
        WHERE book_id=%s
        """,
        (book_id,))

        conn.commit()

        due_date = get_due_date(issue_date)

        st.success(
            f"Book Issued Successfully ✔  |  Due back by **{due_date.strftime('%d %b %Y')}**"
        )

    except Exception as e:

        conn.rollback()
        st.error(e)

    finally:

        cursor.close()
        conn.close()


# ==========================================================
# RETURN BOOK
# ==========================================================

def return_book(roll_no, book_id, return_date):

    if not all([roll_no, book_id]):

        st.warning("Enter Roll Number and Book ID")
        return

    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            SELECT issue_date FROM issued_books
            WHERE roll_no=%s AND book_id=%s AND return_date IS NULL
            ORDER BY issue_date ASC
            LIMIT 1
            """,
            (roll_no, book_id)
        )

        row = cursor.fetchone()

        if row is None:

            st.error("No active issue found for this student and book.")
            return

        issue_date = row[0]

        cursor.execute(
            """
            UPDATE issued_books
            SET return_date=%s
            WHERE roll_no=%s AND book_id=%s AND return_date IS NULL
            ORDER BY issue_date ASC
            LIMIT 1
            """,
            (return_date, roll_no, book_id)
        )

        cursor.execute("""
        UPDATE books
        SET quantity=quantity+1
        WHERE book_id=%s
        """,
        (book_id,))

        conn.commit()

        fine = calculate_fine(issue_date, return_date)

        if fine > 0:

            days_late = (return_date - get_due_date(issue_date)).days

            st.warning(
                f"Book Returned ✔  |  {days_late} day(s) late  |  Fine: ₹{fine}"
            )

        else:

            st.success("Book Returned Successfully ✔  |  No Fine — returned on time 🎉")

    except Exception as e:

        conn.rollback()
        st.error(e)

    finally:

        cursor.close()
        conn.close()


# ==========================================================
# ADMIN DASHBOARD STATS
# ==========================================================

def dashboard_stats():

    # 'quantity' in the books table tracks copies CURRENTLY AVAILABLE
    # (it's decremented on issue and incremented on return) — it is
    # NOT the total number of copies the library owns.
    #
    # Note: MySQL's SUM()/COUNT() come back through the connector as
    # Decimal/long types, not plain int — we cast everything to int()
    # here so every metric downstream is a clean whole number.
    available_books = int(fetch_one("""
    SELECT SUM(quantity)
    FROM books
    """)[0] or 0)

    total_students = int(fetch_one(
        "SELECT COUNT(*) FROM students"
    )[0] or 0)

    issued_books = int(fetch_one("""
    SELECT COUNT(*)
    FROM issued_books
    WHERE return_date IS NULL
    """)[0] or 0)

    # Total copies owned = copies available right now + copies currently
    # out on loan (every issue/return keeps this invariant true).
    total_books = int(available_books + issued_books)

    overdue_books = int(fetch_one("""
    SELECT COUNT(*)
    FROM issued_books
    WHERE return_date IS NULL
    AND DATE_ADD(issue_date, INTERVAL %s DAY) < CURDATE()
    """ % LOAN_PERIOD_DAYS)[0] or 0)

    return {
        "books": total_books,
        "students": total_students,
        "issued": issued_books,
        "available": available_books,
        "overdue": overdue_books
    }


# ==========================================================
# OVERDUE BOOKS REPORT
# ==========================================================

def get_overdue_books():
    """List every book that is issued, not returned, and past its due date."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT ib.roll_no, s.name, ib.book_id, b.book_name, ib.issue_date
        FROM issued_books ib
        JOIN students s ON s.roll_no = ib.roll_no
        JOIN books b ON b.book_id = ib.book_id
        WHERE ib.return_date IS NULL
        AND DATE_ADD(ib.issue_date, INTERVAL %s DAY) < CURDATE()
        ORDER BY ib.issue_date ASC
        """,
        (LOAN_PERIOD_DAYS,)
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    result = []

    for roll_no, name, book_id, book_name, issue_date in rows:

        due_date = get_due_date(issue_date)
        days_late = (datetime.date.today() - due_date).days
        fine = days_late * FINE_PER_DAY

        result.append({
            "Roll Number": roll_no,
            "Student Name": name,
            "Book ID": book_id,
            "Book Name": book_name,
            "Issue Date": issue_date,
            "Due Date": due_date,
            "Days Late": days_late,
            "Fine (₹)": fine
        })

    return result


# ==========================================================
# STUDENT'S OWN ISSUED BOOKS (with due date + live fine)
# ==========================================================

def get_student_active_issues(roll_no):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT ib.book_id, b.book_name, ib.issue_date
        FROM issued_books ib
        JOIN books b ON b.book_id = ib.book_id
        WHERE ib.roll_no=%s AND ib.return_date IS NULL
        ORDER BY ib.issue_date ASC
        """,
        (roll_no,)
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    result = []

    for book_id, book_name, issue_date in rows:

        due_date = get_due_date(issue_date)
        days_left = (due_date - datetime.date.today()).days
        fine = calculate_fine(issue_date)

        result.append({
            "Book ID": book_id,
            "Book Name": book_name,
            "Issue Date": issue_date,
            "Due Date": due_date,
            "Days Left": days_left,
            "Fine So Far (₹)": fine
        })

    return result


# ==========================================================
# CATEGORY / COURSE LOOKUPS (for search filter dropdowns)
# ==========================================================

def get_categories():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT DISTINCT category FROM books WHERE category IS NOT NULL AND category<>'' ORDER BY category"
    )

    rows = [r[0] for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return rows


def get_courses():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT DISTINCT course FROM students WHERE course IS NOT NULL AND course<>'' ORDER BY course"
    )

    rows = [r[0] for r in cursor.fetchall()]

    cursor.close()
    conn.close()

    return rows


def get_student_by_roll(roll_no):
    """Look up a single student's name & course by roll number. Returns None if not found."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name, course FROM students WHERE roll_no=%s",
        (roll_no,)
    )

    row = cursor.fetchone()

    cursor.close()
    conn.close()

    return row


def get_all_students():
    """All students as (roll_no, name, course) — used to populate selection dropdowns."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT roll_no, name, course FROM students ORDER BY name")

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


def get_available_books():
    """All books currently in stock (quantity > 0) — used to populate the Issue dropdown."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT book_id, book_name, author, quantity FROM books WHERE quantity > 0 ORDER BY book_name"
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


def get_active_books_for_student(roll_no):
    """Books currently issued (not yet returned) to a specific student — used to populate the Return dropdown."""

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT ib.book_id, b.book_name, ib.issue_date
        FROM issued_books ib
        JOIN books b ON b.book_id = ib.book_id
        WHERE ib.roll_no = %s AND ib.return_date IS NULL
        ORDER BY ib.issue_date ASC
        """,
        (roll_no,)
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return rows


# ==========================================================
# SMART SEARCH (parameterized — safe from SQL injection)
# ==========================================================

def search_books(term="", category="All", available_only=False, sort_by="Name (A-Z)"):

    conditions = []
    params = []

    if term:
        conditions.append(
            "(book_name LIKE %s OR author LIKE %s OR category LIKE %s OR book_id LIKE %s)"
        )
        like = f"%{term}%"
        params += [like, like, like, like]

    if category and category != "All":
        conditions.append("category=%s")
        params.append(category)

    if available_only:
        conditions.append("quantity>0")

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sort_map = {
        "Name (A-Z)": "book_name ASC",
        "Name (Z-A)": "book_name DESC",
        "Quantity (High to Low)": "quantity DESC",
        "Quantity (Low to High)": "quantity ASC",
        "Category": "category ASC"
    }

    order_by = sort_map.get(sort_by, "book_name ASC")

    query = f"""
        SELECT book_id, book_name, author, category, quantity
        FROM books
        {where_clause}
        ORDER BY {order_by}
    """

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return pd.DataFrame(
        rows,
        columns=["Book ID", "Book Name", "Author", "Category", "Available Copies"]
    )


def search_students(term="", course="All", sort_by="Name (A-Z)"):

    conditions = []
    params = []

    if term:
        conditions.append(
            "(name LIKE %s OR roll_no LIKE %s OR course LIKE %s)"
        )
        like = f"%{term}%"
        params += [like, like, like]

    if course and course != "All":
        conditions.append("course=%s")
        params.append(course)

    where_clause = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sort_map = {
        "Name (A-Z)": "name ASC",
        "Name (Z-A)": "name DESC",
        "Roll Number": "roll_no ASC",
        "Course": "course ASC"
    }

    order_by = sort_map.get(sort_by, "name ASC")

    query = f"""
        SELECT roll_no, name, course
        FROM students
        {where_clause}
        ORDER BY {order_by}
    """

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()

    return pd.DataFrame(
        rows,
        columns=["Roll Number", "Name", "Course"]
    )


# ==========================================================
# ANALYTICS (for the Admin dashboard charts)
# ==========================================================

def get_popular_books(limit=5):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT b.book_name, COUNT(*) AS times_issued
        FROM issued_books ib
        JOIN books b ON b.book_id = ib.book_id
        GROUP BY b.book_name
        ORDER BY times_issued DESC
        LIMIT %s
        """,
        (limit,)
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return pd.DataFrame(rows, columns=["Book Name", "Times Issued"]).set_index("Book Name")


def get_category_distribution():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT COALESCE(category, 'Uncategorized'), SUM(quantity)
        FROM books
        GROUP BY category
        ORDER BY SUM(quantity) DESC
        """
    )

    rows = cursor.fetchall()
    rows = [(cat, int(qty or 0)) for cat, qty in rows]

    cursor.close()
    conn.close()

    return pd.DataFrame(rows, columns=["Category", "Total Quantity"]).set_index("Category")


def get_monthly_issue_trend():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT DATE_FORMAT(issue_date, '%Y-%m') AS month, COUNT(*) AS issues
        FROM issued_books
        GROUP BY month
        ORDER BY month ASC
        """
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return pd.DataFrame(rows, columns=["Month", "Books Issued"]).set_index("Month")


def get_top_students(limit=5):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT s.name, COUNT(*) AS books_issued
        FROM issued_books ib
        JOIN students s ON s.roll_no = ib.roll_no
        GROUP BY s.name
        ORDER BY books_issued DESC
        LIMIT %s
        """,
        (limit,)
    )

    rows = cursor.fetchall()

    cursor.close()
    conn.close()

    return pd.DataFrame(rows, columns=["Student Name", "Books Issued"]).set_index("Student Name")


# ==========================================================
# SHOW TABLE
# ==========================================================

def show_table(query, columns, title):

    data = fetch_all(query)

    df = pd.DataFrame(data, columns=columns)

    st.subheader(title)

    st.dataframe(
        df,
        use_container_width=True
    )


# ==========================================================
# CHANGE PASSWORD (shared by Admin & Student — both are
# just rows in the same `users` table)
# ==========================================================

def change_password(username, old_password, new_password, confirm_password):

    if not old_password or not new_password or not confirm_password:
        st.warning("Please fill in all fields.")
        return False

    if new_password != confirm_password:
        st.error("New password and confirm password do not match.")
        return False

    if len(new_password) < 4:
        st.warning("New password must be at least 4 characters long.")
        return False

    if new_password == old_password:
        st.warning("New password must be different from the current password.")
        return False

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT password FROM users WHERE username=%s",
            (username,)
        )

        row = cursor.fetchone()

        if row is None:
            st.error("User not found.")
            return False

        if row[0] != old_password:
            st.error("Current password is incorrect.")
            return False

        cursor.execute(
            "UPDATE users SET password=%s WHERE username=%s",
            (new_password, username)
        )

        conn.commit()

        st.success("Password changed successfully ✔")
        return True

    except Exception as e:

        conn.rollback()
        st.error(e)
        return False

    finally:

        cursor.close()
        conn.close()