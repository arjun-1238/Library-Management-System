import time
import datetime
from zoneinfo import ZoneInfo
import re
import pandas as pd
import streamlit as st

from auth import (
    initialize_session,
    admin_login,
    student_login,
    logout
)

from admin import (
    add_book,
    get_book_by_id,
    update_book,
    register_student,
    remove_student,
    issue_book,
    return_book,
    dashboard_stats,
    show_table,
    get_overdue_books,
    get_categories,
    get_courses,
    get_student_by_roll,
    get_all_students,
    get_available_books,
    get_all_books,
    get_active_books_for_student,
    search_books,
    search_students,
    get_popular_books,
    get_category_distribution,
    get_monthly_issue_trend,
    get_top_students,
    change_password,
    LOAN_PERIOD_DAYS,
    FINE_PER_DAY,
    MAX_BOOKS_PER_STUDENT
)

from student import (
    student_dashboard_page,
    get_my_books
)

# ===================================================
# PAGE CONFIG
# ===================================================

st.set_page_config(
    page_title="Library Management System",
    page_icon="📚",
    layout="wide"
)

initialize_session()

# ===================================================
# FIELD VALIDATION — catches wrong FORMAT, not just
# empty fields (e.g. a roll number with symbols/spaces,
# a name typed with numbers, etc.)
# ===================================================

def is_valid_name(text):
    """Letters, spaces, apostrophes and hyphens only. Must start with a letter."""
    return bool(re.match(r"^[A-Za-z][A-Za-z .'-]{1,99}$", text.strip()))

def is_valid_roll_no(text):
    """Alphanumeric only, 3–20 characters, no spaces or symbols."""
    return bool(re.match(r"^[A-Za-z0-9]{3,20}$", text.strip()))

def is_valid_course(text):
    """Letters, numbers, spaces, dots, & and - only, e.g. 'B.Tech CSE'."""
    return bool(re.match(r"^[A-Za-z0-9][A-Za-z0-9 .&-]{1,49}$", text.strip()))

def is_valid_book_id(text):
    """Alphanumeric plus hyphen/underscore, 2–20 characters, no spaces."""
    return bool(re.match(r"^[A-Za-z0-9_-]{2,20}$", text.strip()))

def is_valid_category(text):
    """Letters, spaces, & and - only, e.g. 'Fiction', 'Sci-Fi'."""
    return bool(re.match(r"^[A-Za-z][A-Za-z &-]{1,39}$", text.strip()))

# ===================================================
# DESIGN TOKENS — one simple accent color, nothing fancy
# ===================================================

INK    = "#1F2937"   # text (fallback for light mode)
MUTED  = "#6B7280"   # secondary text
BLUE   = "#2563EB"   # single accent color, used everywhere

# ===================================================
# LOCAL LIBRARY PHOTO (optional) — put a photo at
# assets/library.jpg and it will show up as a soft,
# light watermark behind the login page. If the file
# isn't there, everything still works fine without it.
# ===================================================

import base64
from pathlib import Path

def _get_base64_image(path):
    try:
        return base64.b64encode(Path(path).read_bytes()).decode()
    except Exception:
        return None

_library_photo_b64 = _get_base64_image("assets/library.jpg")

# ===================================================
# CSS — respects Streamlit's own light/dark theme via
# its built-in CSS variables, with sensible fallbacks.
# ===================================================

st.markdown(f"""
<style>

.stApp {{
background-color: var(--background-color, #F7F8FA);
color: var(--text-color, {INK});
}}

.block-container {{
padding-top:2rem !important;
max-width:100% !important;
position: relative;
z-index: 1;
}}

.title {{
text-align:center;
font-weight:700;
font-size:34px;
color: var(--text-color, {INK});
margin-bottom:4px;
}}

.subtitle {{
text-align:center;
color: var(--text-color, {MUTED});
opacity: 0.75;
font-size:14px;
margin-bottom:20px;
}}

/* Make sure body text / labels always follow the active theme's text color */
.stApp, .stApp p, .stApp label, .stApp span, .stApp li {{
color: var(--text-color, {INK});
}}

/* Buttons — simple solid color, no gradient (stays legible in both themes) */
div.stButton > button, div[data-testid="stFormSubmitButton"] button {{
border-radius:6px !important;
font-weight:600 !important;
border:1px solid {BLUE} !important;
color:white !important;
background:{BLUE} !important;
}}

div.stButton > button:hover, div[data-testid="stFormSubmitButton"] button:hover {{
background:#1D4ED8 !important;
}}

/* Cards / forms — adapts to light or dark theme automatically */
div[data-testid="stVerticalBlockBorderWrapper"],
div[data-testid="stForm"] {{
border-radius:8px !important;
border:1px solid rgba(128,128,128,0.25) !important;
background: var(--secondary-background-color, #FFFFFF) !important;
padding:1rem !important;
}}

/* Tabs — simple underline on active tab */
.stTabs [aria-selected="true"] {{
color:{BLUE} !important;
font-weight:600;
}}

/* Metrics — adapts to light or dark theme automatically */
div[data-testid="stMetric"] {{
background: var(--secondary-background-color, #FFFFFF);
border:1px solid rgba(128,128,128,0.25);
border-radius:8px;
padding:10px 14px;
}}

[data-testid="stMetricValue"], [data-testid="stMetricLabel"] {{
color: var(--text-color, {INK}) !important;
}}

</style>
""", unsafe_allow_html=True)

# Show the library photo very faintly behind EVERY page (login and all
# dashboard tabs), not just the login screen. Low, fixed opacity means it
# stays "light" and unobtrusive in both light and dark theme, and z-index:-1
# + pointer-events:none keeps it purely decorative — nothing sits behind it,
# nothing can accidentally click through it.
if _library_photo_b64:
    st.markdown(f"""
    <div style="
        position: fixed;
        inset: 0;
        z-index: -1;
        background-image: url(data:image/jpeg;base64,{_library_photo_b64});
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        opacity: 0.07;
        pointer-events: none;
    "></div>
    """, unsafe_allow_html=True)

# Disable the browser's own autocomplete/suggestion dropdown on every input
# field (it was showing old values typed in unrelated fields). Streamlit's
# text_input has no autocomplete= option, so this is injected via JS.
# Runs on a short interval AND via MutationObserver since Streamlit re-renders
# inputs on almost every interaction (a single one-time pass isn't enough).
st.components.v1.html("""
<script>
function disableAutocomplete() {
    try {
        const doc = window.parent.document;
        doc.querySelectorAll('input').forEach(function(el) {
            el.setAttribute('autocomplete', el.type === 'password' ? 'new-password' : 'off');
        });
        doc.querySelectorAll('form').forEach(function(el) {
            el.setAttribute('autocomplete', 'off');
        });
    } catch (e) {}
}
disableAutocomplete();
setInterval(disableAutocomplete, 400);
try {
    const _observer = new MutationObserver(disableAutocomplete);
    _observer.observe(window.parent.document.body, { childList: true, subtree: true });
} catch (e) {}
</script>
""", height=0)


# ===================================================
# LOGIN PAGE
# ===================================================

if not st.session_state.logged_in:

    _login_hour = datetime.datetime.now(ZoneInfo("Asia/Kolkata")).hour
    if _login_hour < 12:
        _login_greeting = "Good Morning"
    elif _login_hour < 17:
        _login_greeting = "Good Afternoon"
    else:
        _login_greeting = "Good Evening"

    st.markdown(f"<p class='subtitle' style='margin-bottom:2px;'>👋 {_login_greeting}</p>", unsafe_allow_html=True)
    st.markdown("<h1 class='title'>📚 Library Management System</h1>", unsafe_allow_html=True)
    st.markdown("<p class='subtitle'>Manage books, students and issued copies — all in one place</p>", unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])

    with c2:

        with st.container(border=True):

            st.markdown("### Welcome back 👋")
            st.caption("Login to continue to your dashboard")

            role=st.selectbox(
                "Login As",
                ["Admin","Student"]
            )

            if role=="Admin":

                with st.form("admin_login_form", clear_on_submit=False):

                    username=st.text_input("Username")
                    password=st.text_input(
                        "Password",
                        type="password"
                    )

                    submitted = st.form_submit_button("Login 🔐", use_container_width=True)

                    if submitted:

                        if not username or not password:
                            st.warning("⚠️ Please enter both username and password.")
                        else:
                            with st.spinner("Checking credentials..."):
                                time.sleep(0.4)
                                success = admin_login(username,password)

                            if success:
                                st.success(f"Welcome back, {username}! 🎉")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("❌ Invalid username or password. Please try again.")

            else:

                with st.form("student_login_form", clear_on_submit=False):

                    roll=st.text_input("Roll Number")

                    password=st.text_input(
                        "Password",
                        type="password"
                    )

                    submitted = st.form_submit_button("Login 🔐", use_container_width=True)

                    if submitted:

                        if not roll or not password:
                            st.warning("⚠️ Please enter both roll number and password.")
                        else:
                            with st.spinner("Checking credentials..."):
                                time.sleep(0.4)
                                success = student_login(roll, password)

                            if success:
                                st.success("Login successful! 🎉")
                                time.sleep(0.5)
                                st.rerun()
                            else:
                                st.error("❌ Invalid roll number or password. Please try again.")


# ===================================================
# DASHBOARD
# ===================================================

else:

    st.sidebar.title("📚 Library")

    _hour = datetime.datetime.now().hour
    if _hour < 12:
        _greeting = "Good Morning"
    elif _hour < 17:
        _greeting = "Good Afternoon"
    else:
        _greeting = "Good Evening"

    st.sidebar.caption(f"👋 {_greeting}!")

    st.sidebar.success(
        f"👤 {st.session_state.username}"
    )

    st.sidebar.info(
        f"🏷️ Role: {st.session_state.role}"
    )

    with st.sidebar.expander("🔑 Change Password"):

        with st.form("change_password_form", clear_on_submit=True):

            old_pwd = st.text_input(
                "Current Password", type="password", key="old_pwd",
                help="The password you currently use to log in."
            )
            new_pwd = st.text_input(
                "New Password", type="password", key="new_pwd",
                help="At least 4 characters, different from your current password."
            )
            confirm_pwd = st.text_input("Confirm New Password", type="password", key="confirm_pwd")

            pwd_submitted = st.form_submit_button("Update Password", use_container_width=True)

            if pwd_submitted:
                with st.spinner("Updating password..."):
                    ok = change_password(
                        st.session_state.username,
                        old_pwd,
                        new_pwd,
                        confirm_pwd
                    )
                if ok:
                    st.balloons()

    if st.session_state.role == "Admin":

        with st.sidebar.expander("🔍 Quick Lookup"):

            quick_query = st.text_input(
                "Search books or students",
                key="quick_lookup",
                placeholder="Name, ID or roll no...",
                help="Instantly search across books and students from anywhere — no need to switch tabs."
            )

            if quick_query.strip():

                q_books = search_books(term=quick_query.strip(), category="All", available_only=False, sort_by="Name (A-Z)")
                q_students = search_students(term=quick_query.strip(), course="All", sort_by="Name (A-Z)")

                st.caption(f"📖 **{len(q_books)}** book(s)")
                for _, b in q_books.head(4).iterrows():
                    st.caption(f"• {b['Book Name']} — {b['Available Copies']} available")

                st.caption(f"🎓 **{len(q_students)}** student(s)")
                for _, s in q_students.head(4).iterrows():
                    st.caption(f"• {s['Name']} ({s['Roll Number']})")

    st.sidebar.divider()

    confirm_logout = st.sidebar.checkbox("Confirm logout")

    if st.sidebar.button("Logout", disabled=not confirm_logout, use_container_width=True):
        with st.spinner("Logging out..."):
            time.sleep(0.3)
        logout()

    if not confirm_logout:
        st.sidebar.caption("Tick the box above to enable logout.")

    # ===============================================
    # ADMIN
    # ===============================================

    if st.session_state.role=="Admin":

        title_col, refresh_col = st.columns([5, 1])

        with title_col:
            st.title("📚 Admin Dashboard")

        with refresh_col:
            st.write("")
            st.write("")
            if st.button("🔄 Refresh", use_container_width=True, help="Reload the latest stats"):
                st.rerun()

        with st.spinner("Loading stats..."):
            stats=dashboard_stats()

        if stats["overdue"] > 0:
            st.error(
                f"⚠️ {stats['overdue']} book(s) are currently overdue. Check the Reports tab for details."
            )

        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("📗 Total Books", stats["books"])
        c2.metric("🎓 Students", stats["students"])
        c3.metric("📤 Currently Issued", stats["issued"])
        c4.metric("✅ Available Now", stats["available"])
        c5.metric("⏰ Overdue", stats["overdue"])

        st.divider()

        tab1,tab2,tab3,tab4,tab5,tab6=st.tabs(
            [
                "📖 Books",
                "🎓 Students",
                "📤 Issue",
                "📥 Return",
                "📊 Reports",
                "📈 Analytics"
            ]
        )

        # ===========================================
        # BOOKS
        # ===========================================

        with tab1:

            book_t1, book_t2 = st.tabs(["➕ Add Book", "✏️ Update Book"])

            with book_t1:

                st.subheader("Add a New Book")

                with st.form("add_book_form", clear_on_submit=True):

                    col1, col2, col3 = st.columns(3)

                    with col1:
                        book_id=st.text_input("Book ID", help="A unique code for this book, e.g. B001")
                        category=st.text_input("Category")

                    with col2:
                        name=st.text_input("Book Name")
                        qty=st.number_input(
                            "Quantity",
                            min_value=1,
                            value=1,
                            help="Number of physical copies being added"
                        )

                    with col3:
                        author=st.text_input("Author")

                    submitted = st.form_submit_button("➕ Add Book", use_container_width=True)

                    if submitted:

                        errors = []

                        if not book_id or not name or not author or not category:
                            errors.append("Book ID, Book Name, Author and Category are all required.")
                        else:
                            if not is_valid_book_id(book_id):
                                errors.append("Book ID should be 2–20 letters/numbers/hyphens only, no spaces (e.g. B001).")
                            if len(name.strip()) < 2:
                                errors.append("Book Name looks too short.")
                            if not is_valid_name(author):
                                errors.append("Author should contain only letters, spaces or hyphens (no numbers).")
                            if not is_valid_category(category):
                                errors.append("Category should contain only letters and spaces (e.g. Fiction).")

                        if errors:
                            for e in errors:
                                st.warning(f"⚠️ {e}")
                        else:
                            with st.spinner("Adding book..."):
                                added = add_book(
                                    book_id,
                                    name,
                                    author,
                                    category,
                                    qty
                                )
                                time.sleep(0.3)
                            if added:
                                st.balloons()

            with book_t2:

                st.subheader("Update an Existing Book")

                all_books = get_all_books()

                if not all_books:
                    st.info("📭 No books in the catalogue yet — add one first.")
                else:
                    update_book_options = {
                        f"{bid} — {bname} by {author}  (Stock: {qty})": bid
                        for bid, bname, author, qty in all_books
                    }

                    selected_label = st.selectbox(
                        "🔍 Search and select a book to edit",
                        list(update_book_options.keys()),
                        index=None,
                        placeholder="Type a book ID, name or author...",
                        key="update_book_select"
                    )

                    if not selected_label:
                        st.info("ℹ️ Select a book above to load and edit its details.")
                    else:
                        selected_book_id = update_book_options[selected_label]
                        current = get_book_by_id(selected_book_id)

                        if not current:
                            st.error("Couldn't load this book's details. It may have just been removed.")
                        else:
                            _, cur_name, cur_author, cur_category, cur_qty = current

                            with st.form("update_book_form"):

                                st.caption(f"Book ID: `{selected_book_id}` (Book ID itself can't be changed)")

                                ucol1, ucol2, ucol3 = st.columns(3)

                                with ucol1:
                                    u_name = st.text_input("Book Name", value=cur_name)

                                with ucol2:
                                    u_author = st.text_input("Author", value=cur_author)

                                with ucol3:
                                    u_category = st.text_input("Category", value=cur_category or "")

                                u_qty = st.number_input(
                                    "Quantity Available",
                                    min_value=0,
                                    value=int(cur_qty),
                                    help="Total copies currently available for issue — adjust this when restocking."
                                )

                                update_submitted = st.form_submit_button("💾 Save Changes", use_container_width=True)

                                if update_submitted:

                                    errors = []

                                    if not u_name or not u_author or not u_category:
                                        errors.append("Book Name, Author and Category are all required.")
                                    else:
                                        if len(u_name.strip()) < 2:
                                            errors.append("Book Name looks too short.")
                                        if not is_valid_name(u_author):
                                            errors.append("Author should contain only letters, spaces or hyphens (no numbers).")
                                        if not is_valid_category(u_category):
                                            errors.append("Category should contain only letters and spaces (e.g. Fiction).")

                                    if errors:
                                        for e in errors:
                                            st.warning(f"⚠️ {e}")
                                    else:
                                        with st.spinner("Saving changes..."):
                                            updated = update_book(
                                                selected_book_id,
                                                u_name,
                                                u_author,
                                                u_category,
                                                u_qty
                                            )
                                            time.sleep(0.3)
                                        if updated:
                                            st.balloons()

        # ===========================================
        # STUDENT
        # ===========================================

        with tab2:

            t1,t2=st.tabs(
                [
                    "➕ Register",
                    "🗑️ Remove"
                ]
            )

            with t1:

                with st.form("register_student_form", clear_on_submit=True):

                    rc1, rc2, rc3 = st.columns(3)

                    with rc1:
                        name=st.text_input("Student Name")

                    with rc2:
                        roll=st.text_input("Roll Number", help="Used as the student's login username. Default password is 1234.")

                    with rc3:
                        course=st.text_input("Course")

                    submitted = st.form_submit_button("➕ Register Student", use_container_width=True)

                    if submitted:

                        errors = []

                        if not name or not roll or not course:
                            errors.append("Please fill in all fields.")
                        else:
                            if not is_valid_name(name):
                                errors.append("Student Name should contain only letters and spaces (no numbers/symbols).")
                            if not is_valid_roll_no(roll):
                                errors.append("Roll Number should be 3–20 letters/numbers only, no spaces or symbols (e.g. 2023CS01).")
                            if not is_valid_course(course):
                                errors.append("Course should contain only letters, numbers, spaces or dots (e.g. B.Tech CSE).")

                        if errors:
                            for e in errors:
                                st.warning(f"⚠️ {e}")
                        else:
                            with st.spinner("Registering student..."):
                                registered = register_student(
                                    name,
                                    roll,
                                    course
                                )
                                time.sleep(0.3)
                            if registered:
                                st.balloons()

            with t2:

                roll=st.text_input(
                    "Roll Number",
                    key="remove"
                )

                confirm_remove = st.checkbox("I confirm I want to remove this student", key="confirm_remove")

                if roll and not confirm_remove:
                    st.caption("⚠️ Please confirm before removing.")

                if st.button("🗑️ Remove", disabled=not (roll and confirm_remove), use_container_width=True):

                    with st.spinner("Removing student..."):
                        remove_student(
                            roll
                        )
                        time.sleep(0.3)

        # ===========================================
        # ISSUE
        # ===========================================

        with tab3:

            st.subheader("Issue a Book")

            st.caption(
                f"📌 Loan period: {LOAN_PERIOD_DAYS} days  •  Fine: ₹{FINE_PER_DAY}/day late  •  "
                f"Max {MAX_BOOKS_PER_STUDENT} books per student at a time"
            )

            all_students = get_all_students()
            available_books = get_available_books()

            if not all_students:
                st.info("👥 No students registered yet. Add a student first from the Students tab.")
            elif not available_books:
                st.info("📭 No books are currently available to issue. Add books or wait for returns.")
            else:
                student_options = {
                    f"{roll} — {name} ({course})": roll
                    for roll, name, course in all_students
                }

                book_options = {
                    f"{bid} — {bname} by {author}  (Available: {qty})": bid
                    for bid, bname, author, qty in available_books
                }

                with st.form("issue_book_form", clear_on_submit=True):

                    ic1, ic2, ic3 = st.columns(3)

                    with ic1:
                        student_label = st.selectbox(
                            "🎓 Student",
                            list(student_options.keys()),
                            index=None,
                            placeholder="Search by roll number or name...",
                            help="Type a roll number (e.g. 2023CS01) or student name to filter the list.",
                            key="issue_student_select"
                        )

                    with ic2:
                        book_label = st.selectbox(
                            "📖 Book",
                            list(book_options.keys()),
                            index=None,
                            placeholder="Type to search a book...",
                            key="issue_book_select"
                        )

                    with ic3:
                        date=st.date_input(
                            "Issue Date"
                        )

                    submitted = st.form_submit_button("📤 Issue Book", use_container_width=True)

                    if submitted:

                        if not student_label or not book_label:
                            st.warning("⚠️ Please search and select both a student and a book.")
                        else:
                            roll = student_options[student_label]
                            book = book_options[book_label]

                            with st.spinner("Issuing book..."):
                                issue_book(
                                    roll,
                                    book,
                                    date
                                )
                                time.sleep(0.3)

        # ===========================================
        # RETURN
        # ===========================================

        with tab4:

            st.subheader("Return a Book")

            all_students = get_all_students()

            if not all_students:
                st.info("👥 No students registered yet.")
            else:
                student_options = {
                    f"{roll} — {name} ({course})": roll
                    for roll, name, course in all_students
                }

                rc1, rc2, rc3 = st.columns(3)

                with rc1:
                    return_student_label = st.selectbox(
                        "🎓 Student",
                        list(student_options.keys()),
                        index=None,
                        placeholder="Search by roll number or name...",
                        help="Type a roll number (e.g. 2023CS01) or student name to filter the list.",
                        key="return_student_select"
                    )

                if not return_student_label:

                    with rc2:
                        st.selectbox("📖 Book", ["Select a student first"], disabled=True, key="return_book_empty")
                    with rc3:
                        st.date_input("Return Date", key="return_date_empty", disabled=True)
                    st.info("ℹ️ Search and select a student above to see their currently issued books.")

                else:

                    return_roll = student_options[return_student_label]
                    active_books = get_active_books_for_student(return_roll)

                    if not active_books:
                        with rc2:
                            st.selectbox("📖 Book", ["No books currently issued"], disabled=True, key="return_book_empty2")
                        with rc3:
                            st.date_input("Return Date", key="return_date_empty2", disabled=True)
                        st.info("ℹ️ This student has no books currently issued.")
                    else:
                        book_options = {
                            f"{bid} — {bname}  (issued {idate})": bid
                            for bid, bname, idate in active_books
                        }

                        with rc2:
                            return_book_label = st.selectbox(
                                "📖 Book to Return",
                                list(book_options.keys()),
                                index=None,
                                placeholder="Type to search a book...",
                                key="return_book_select"
                            )

                        with rc3:
                            date = st.date_input("Return Date", key="return_date_input")

                        if not return_book_label:
                            st.button("📥 Return Book", use_container_width=True, disabled=True, key="return_submit_btn_disabled")
                            st.caption("⚠️ Please select a book to return.")
                        else:
                            return_book_id = book_options[return_book_label]

                            if st.button("📥 Return Book", use_container_width=True, key="return_submit_btn"):

                                with st.spinner("Processing return..."):
                                    return_book(
                                        return_roll,
                                        return_book_id,
                                        date
                                    )
                                    time.sleep(0.3)

        # ===========================================
        # REPORTS
        # ===========================================

        with tab5:

            st.subheader("Reports")

            report_tab1, report_tab2, report_tab3, report_tab4 = st.tabs(
                ["📖 Books", "🎓 Students", "⏰ Overdue", "👤 By Student"]
            )

            # ---------------------------------------------
            # BOOKS REPORT — search + filter + sort + export
            # ---------------------------------------------
            with report_tab1:

                categories = ["All"] + get_categories()

                bc1, bc2, bc3, bc4 = st.columns([2,1,1,1])

                with bc1:
                    book_term = st.text_input(
                        "🔍 Search (name, author, category, ID)",
                        key="book_term"
                    )

                with bc2:
                    book_category = st.selectbox("Category", categories, key="book_category")

                with bc3:
                    book_sort = st.selectbox(
                        "Sort by",
                        ["Name (A-Z)", "Name (Z-A)", "Quantity (High to Low)", "Quantity (Low to High)", "Category"],
                        key="book_sort"
                    )

                with bc4:
                    available_only = st.checkbox("Available only", key="available_only")

                books_df = search_books(
                    term=book_term.strip(),
                    category=book_category,
                    available_only=available_only,
                    sort_by=book_sort
                )

                st.dataframe(books_df, use_container_width=True)
                st.caption(f"{len(books_df)} book(s) found")

                if not books_df.empty:
                    st.download_button(
                        "📥 Download as CSV",
                        books_df.to_csv(index=False),
                        file_name="books_report.csv",
                        mime="text/csv",
                        key="download_books_csv"
                    )

            # ---------------------------------------------
            # STUDENTS REPORT — search + filter + sort + export
            # ---------------------------------------------
            with report_tab2:

                courses = ["All"] + get_courses()

                sc1, sc2, sc3 = st.columns([2,1,1])

                with sc1:
                    student_term = st.text_input(
                        "🔍 Search (name, roll number, course)",
                        key="student_term"
                    )

                with sc2:
                    student_course = st.selectbox("Course", courses, key="student_course")

                with sc3:
                    student_sort = st.selectbox(
                        "Sort by",
                        ["Name (A-Z)", "Name (Z-A)", "Roll Number", "Course"],
                        key="student_sort"
                    )

                students_df = search_students(
                    term=student_term.strip(),
                    course=student_course,
                    sort_by=student_sort
                )

                st.dataframe(students_df, use_container_width=True)
                st.caption(f"{len(students_df)} student(s) found")

                if not students_df.empty:
                    st.download_button(
                        "📥 Download as CSV",
                        students_df.to_csv(index=False),
                        file_name="students_report.csv",
                        mime="text/csv",
                        key="download_students_csv"
                    )

                st.divider()

                if st.button("📤 Show Currently Issued Books", use_container_width=True):

                    with st.spinner("Fetching issued books..."):
                        show_table(
                            """
                            SELECT
                            roll_no,
                            book_id,
                            issue_date
                            FROM issued_books
                            WHERE return_date IS NULL
                            """,

                            [
                                "Roll Number",
                                "Book ID",
                                "Issue Date"
                            ],

                            "Issued Books"
                        )

            # ---------------------------------------------
            # OVERDUE REPORT — with fines
            # ---------------------------------------------
            with report_tab3:

                with st.spinner("Checking for overdue books..."):
                    overdue = get_overdue_books()

                if not overdue:
                    st.success("🎉 No overdue books right now!")
                else:
                    st.error(f"⚠️ {len(overdue)} book(s) are overdue.")

                    overdue_df = pd.DataFrame(overdue)
                    st.dataframe(overdue_df, use_container_width=True)

                    total_fine = int(overdue_df["Fine (₹)"].sum())
                    st.metric("💰 Total Outstanding Fine", f"₹{total_fine}")

                    st.download_button(
                        "📥 Download as CSV",
                        overdue_df.to_csv(index=False),
                        file_name="overdue_books_report.csv",
                        mime="text/csv",
                        key="download_overdue_csv"
                    )

            # ---------------------------------------------
            # BY STUDENT — full issue history for one roll no
            # ---------------------------------------------
            with report_tab4:

                st.caption("Enter a student's roll number to see every book they've ever issued — currently held or returned — with due dates and fines.")

                lookup_col1, lookup_col2 = st.columns([3,1])

                with lookup_col1:
                    lookup_roll = st.text_input("🔍 Roll Number", key="lookup_roll", placeholder="e.g. 2023CS01")

                with lookup_col2:
                    st.write("")
                    st.write("")
                    lookup_clicked = st.button("Search", key="lookup_btn", use_container_width=True)

                if lookup_clicked or lookup_roll:

                    if not lookup_roll.strip():
                        st.warning("⚠️ Please enter a roll number.")
                    else:
                        roll = lookup_roll.strip()
                        student_info = get_student_by_roll(roll)

                        if not student_info:
                            st.error(f"No student found with roll number '{roll}'.")
                        else:
                            name, course = student_info

                            with st.spinner("Fetching issue history..."):
                                history = get_my_books(roll)

                            st.info(f"👤 **{name}**  •  🎓 {course}  •  Roll No: {roll}")

                            if not history:
                                st.info("This student hasn't issued any books yet. 📖")
                            else:
                                history_df = pd.DataFrame(history)
                                st.dataframe(history_df, use_container_width=True)

                                active_count = sum(1 for b in history if b["Return Date"] == "—")
                                total_fine = sum(b["Fine (₹)"] for b in history)

                                hc1, hc2, hc3 = st.columns(3)
                                hc1.metric("📚 Total Books Ever Issued", len(history))
                                hc2.metric("📖 Currently Holding", active_count)
                                hc3.metric("💰 Total Fine (all-time)", f"₹{total_fine}")

                                st.download_button(
                                    "📥 Download as CSV",
                                    history_df.to_csv(index=False),
                                    file_name=f"issue_history_{roll}.csv",
                                    mime="text/csv",
                                    key="download_history_csv"
                                )

        # ===========================================
        # ANALYTICS
        # ===========================================

        with tab6:

            st.subheader("📈 Library Analytics")

            a1, a2 = st.columns(2)

            with a1:
                st.markdown("**🔥 Most Popular Books**")
                popular_df = get_popular_books(limit=5)

                if popular_df.empty:
                    st.info("No issue history yet.")
                else:
                    st.bar_chart(popular_df)

            with a2:
                st.markdown("**📚 Books by Category**")
                category_df = get_category_distribution()

                if category_df.empty:
                    st.info("No books added yet.")
                else:
                    st.bar_chart(category_df)

            st.divider()

            a3, a4 = st.columns(2)

            with a3:
                st.markdown("**📅 Monthly Issue Trend**")
                trend_df = get_monthly_issue_trend()

                if trend_df.empty:
                    st.info("No issue history yet.")
                else:
                    st.line_chart(trend_df)

            with a4:
                st.markdown("**🏅 Top Active Students**")
                top_students_df = get_top_students(limit=5)

                if top_students_df.empty:
                    st.info("No issue history yet.")
                else:
                    st.bar_chart(top_students_df)

    # ===============================================
    # STUDENT
    # ===============================================

    elif st.session_state.role=="Student":

        student_dashboard_page(
            st.session_state.username
        )
