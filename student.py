import datetime
import html
import streamlit as st
import pandas as pd
from database import fetch_all, fetch_one

from admin import (
    search_books,
    get_categories,
    LOAN_PERIOD_DAYS,
    FINE_PER_DAY,
    MAX_BOOKS_PER_STUDENT,
    calculate_fine,
    get_due_date
)


# ==========================================================
# MY BOOKS — with due date + live fine calculation
# ==========================================================

def get_my_books(roll_no):

    rows = fetch_all("""
        SELECT
            b.book_id,
            b.book_name,
            b.author,
            ib.issue_date,
            ib.return_date
        FROM issued_books ib
        JOIN books b
        ON ib.book_id = b.book_id
        WHERE ib.roll_no=%s
        ORDER BY ib.issue_date DESC
    """,
    (roll_no,))

    result = []

    for book_id, book_name, author, issue_date, return_date in (rows or []):

        due_date = get_due_date(issue_date)

        if return_date is None:

            fine = calculate_fine(issue_date)
            days_left = (due_date - datetime.date.today()).days

            if days_left < 0:
                status = f"⚠️ Overdue by {abs(days_left)} day(s)"
            elif days_left <= 2:
                status = f"⏰ Due in {days_left} day(s)"
            else:
                status = "📖 Issued"

        else:

            fine = calculate_fine(issue_date, return_date)
            status = "✅ Returned" if fine == 0 else "✅ Returned (was late)"

        result.append({
            "Book Name": book_name,
            "Author": author,
            "Issue Date": issue_date,
            "Due Date": due_date,
            "Return Date": return_date if return_date else "—",
            "Status": status,
            "Fine (₹)": fine
        })

    return result


def display_my_books(roll_no):

    books = get_my_books(roll_no)

    if not books:
        st.info("You haven't issued any books yet. 📖")
        return

    active = [b for b in books if b["Return Date"] == "—"]
    past = [b for b in books if b["Return Date"] != "—"]

    if active:
        st.markdown("**📖 Currently Issued**")

        for b in active:
            days_total = LOAN_PERIOD_DAYS
            days_used = (datetime.date.today() - b["Issue Date"]).days
            fraction = min(max(days_used / days_total, 0), 1)

            with st.container(border=True):
                cc1, cc2 = st.columns([3, 2])

                with cc1:
                    st.markdown(f"**{b['Book Name']}**  \n*by {b['Author']}*")
                    st.caption(f"Issued: {b['Issue Date']}  •  Due: {b['Due Date']}")

                with cc2:
                    st.markdown(f"**{b['Status']}**")
                    if b["Fine (₹)"] > 0:
                        st.caption(f"💰 Fine so far: ₹{b['Fine (₹)']}")

                st.progress(fraction)

        st.divider()

    if past:
        st.markdown("**📜 Past Returns**")
        st.dataframe(pd.DataFrame(past), use_container_width=True)

    total_fine = sum(b["Fine (₹)"] for b in books)

    if total_fine > 0:
        st.warning(f"💰 Total outstanding fine: ₹{total_fine}")
    else:
        st.success("✅ No fine due.")


# ==========================================================
# SEARCH BOOKS — reuses the SAME parameterized search used
# by the Admin's Reports tab, so there's only ONE search
# implementation in the whole app (no duplicate logic).
# ==========================================================

CATEGORY_ICONS = {
    "fiction": "📖", "fantasy": "🧙", "mystery": "🔍", "biography": "👤",
    "programming": "💻", "computer science": "🖥️", "science": "🔬",
    "history": "🏺", "self-help": "🌱", "business": "💼", "psychology": "🧠",
    "philosophy": "🏛️", "mathematics": "➗", "poetry": "✒️"
}


def _category_icon(category):
    return CATEGORY_ICONS.get((category or "").strip().lower(), "📚")


def _truncate(text, length):
    text = str(text)
    return text if len(text) <= length else text[:length - 1].rstrip() + "…"


def display_search_result():

    categories = ["All"] + get_categories()

    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])

    with c1:
        term = st.text_input(
            "🔍 Search by name, author or category",
            key="student_search_term"
        )

    with c2:
        category = st.selectbox("Category", categories, key="student_search_category")

    with c3:
        sort_by = st.selectbox(
            "Sort by",
            ["Name (A-Z)", "Name (Z-A)", "Quantity (High to Low)", "Category"],
            key="student_search_sort"
        )

    with c4:
        available_only = st.checkbox("Available only", value=True, key="student_search_available")

    df = search_books(
        term=term.strip(),
        category=category,
        available_only=available_only,
        sort_by=sort_by
    )

    view_mode = st.radio(
        "View as", ["🗂️ Cards", "📋 Table"],
        horizontal=True, key="student_book_view_mode", label_visibility="collapsed"
    )

    st.caption(f"{len(df)} book(s) found")

    if df.empty:
        st.info("No books match your search. Try a different keyword or filter. 🔎")
        return

    if view_mode == "📋 Table":
        st.dataframe(df, use_container_width=True)
        return

    # ---- Card grid view — fixed-height cards so the grid always looks even ----
    # NOTE: every piece of HTML here is built as ONE continuous line with no
    # leading whitespace — multi-line indented HTML gets misread by Streamlit's
    # markdown parser as a code block (4+ leading spaces = code block) instead
    # of being rendered as HTML.
    card_blocks = []

    for _, book in df.iterrows():
        icon = _category_icon(book["Category"])
        qty = book["Available Copies"]

        if qty > 1:
            badge_bg, badge_color, badge_text = "#DCFCE7", "#166534", f"✅ {qty} available"
        elif qty == 1:
            badge_bg, badge_color, badge_text = "#FEF9C3", "#854D0E", "⚠️ Only 1 left"
        else:
            badge_bg, badge_color, badge_text = "#FEE2E2", "#991B1B", "❌ Unavailable"

        name = html.escape(_truncate(book["Book Name"], 42))
        author = html.escape(_truncate(book["Author"] or "Unknown", 30))
        category = html.escape(book["Category"] or "Uncategorized")

        card = (
            '<div style="border:1px solid #E5E7EB;border-radius:8px;padding:14px;'
            'height:172px;display:flex;flex-direction:column;justify-content:space-between;'
            'background:white;">'
              '<div>'
                f'<div style="font-weight:700;font-size:14.5px;line-height:1.35;margin-bottom:4px;'
                f'display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;">'
                f'{icon} {name}</div>'
                f'<div style="color:#6B7280;font-size:12px;margin-bottom:8px;'
                f'white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">by {author}</div>'
                f'<span style="display:inline-block;background:#F3F4F6;color:#374151;'
                f'border-radius:6px;padding:2px 8px;font-size:11px;">{category}</span>'
              '</div>'
              f'<div style="background:{badge_bg};color:{badge_color};border-radius:6px;'
              f'padding:5px 9px;font-size:12px;font-weight:600;text-align:center;">{badge_text}</div>'
            '</div>'
        )
        card_blocks.append(card)

    grid_html = (
        '<div style="display:grid;grid-template-columns:repeat(auto-fill, minmax(210px, 1fr));gap:12px;">'
        + "".join(card_blocks) +
        '</div>'
    )

    st.markdown(grid_html, unsafe_allow_html=True)


# ==========================================================
# STUDENT DASHBOARD STATS
# ==========================================================

def student_dashboard(roll_no):

    total_books = fetch_one("""
        SELECT SUM(quantity)
        FROM books
    """)

    available_books = total_books[0] if total_books and total_books[0] else 0

    issued_books = fetch_one("""
        SELECT COUNT(*)
        FROM issued_books
        WHERE
            roll_no=%s
            AND return_date IS NULL
    """,
    (roll_no,))

    issued = issued_books[0] if issued_books else 0

    active_books = get_my_books(roll_no)
    active_books = [b for b in active_books if b["Return Date"] == "—"]

    overdue_count = sum(1 for b in active_books if "Overdue" in b["Status"])
    current_fine = sum(b["Fine (₹)"] for b in active_books)

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("📚 Books Available", int(available_books))

    with col2:
        st.metric("📖 My Issued Books", int(issued))

    with col3:
        st.metric("⏰ Overdue", overdue_count)

    with col4:
        st.metric("💰 Fine Due", f"₹{current_fine}")

    if overdue_count > 0:
        st.error(
            f"⚠️ You have {overdue_count} overdue book(s). Please return them soon — "
            f"fine is ₹{FINE_PER_DAY}/day."
        )
    else:
        due_soon = sum(
            1 for b in active_books
            if "Due in" in b["Status"]
        )
        if due_soon > 0:
            st.warning(f"⏰ {due_soon} book(s) due within 2 days.")


# ==========================================================
# STUDENT HOME PAGE
# ==========================================================

def student_dashboard_page(roll_no):

    st.title("🎓 Student Dashboard")

    st.caption(
        f"📌 Loan period: {LOAN_PERIOD_DAYS} days  •  Fine: ₹{FINE_PER_DAY}/day late  •  "
        f"You can hold up to {MAX_BOOKS_PER_STUDENT} books at a time"
    )

    student_dashboard(roll_no)

    st.divider()

    tab1, tab2 = st.tabs(
        [
            "🔍 Search Books",
            "📖 My Books"
        ]
    )

    with tab1:

        display_search_result()

    with tab2:

        display_my_books(roll_no)