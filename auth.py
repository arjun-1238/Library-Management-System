import streamlit as st
from database import get_connection

# ==========================================================
# SESSION MANAGEMENT
# ==========================================================

def initialize_session():
    """Initialize session variables."""

    defaults = {
        "logged_in": False,
        "role": "",
        "username": "",
        "name": "",
        "message": ""
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ==========================================================
# INPUT VALIDATION
# ==========================================================

def validate_login(username, password):
    """
    Validate login fields.
    """

    if not username.strip():
        st.warning("Username / Roll Number is required.")
        return False

    if not password.strip():
        st.warning("Password is required.")
        return False

    return True


# ==========================================================
# ADMIN LOGIN
# ==========================================================

def admin_login(username, password):
    """
    Authenticate Admin.
    """

    if not validate_login(username, password):
        return False

    conn = get_connection()

    if conn is None:
        return False

    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT username, role
            FROM users
            WHERE username=%s
            AND password=%s
            AND role='Admin'
        """, (username, password))

        admin = cursor.fetchone()

        if admin:

            st.session_state.logged_in = True
            st.session_state.role = "Admin"
            st.session_state.username = admin["username"]

            return True

        st.error("Invalid Admin Credentials")
        return False

    except Exception as e:
        st.error(e)
        return False

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# STUDENT LOGIN
# ==========================================================

def student_login(roll_no, password):
    """
    Authenticate Student.
    """

    if not validate_login(roll_no, password):
        return False

    conn = get_connection()

    if conn is None:
        return False

    cursor = conn.cursor(dictionary=True)

    try:

        cursor.execute("""
            SELECT
                s.roll_no,
                s.name,
                u.role
            FROM users u
            JOIN students s
            ON u.roll_no = s.roll_no
            WHERE
                u.roll_no=%s
                AND u.password=%s
                AND u.role='Student'
        """, (roll_no, password))

        student = cursor.fetchone()

        if student:

            st.session_state.logged_in = True
            st.session_state.role = "Student"
            st.session_state.username = student["roll_no"]
            st.session_state.name = student["name"]

            return True

        st.error("Invalid Student Credentials")
        return False

    except Exception as e:
        st.error(e)
        return False

    finally:
        cursor.close()
        conn.close()


# ==========================================================
# LOGOUT
# ==========================================================

def logout():

    st.session_state.logged_in = False
    st.session_state.role = ""
    st.session_state.username = ""
    st.session_state.name = ""
    st.session_state.message = ""

    st.rerun()


# ==========================================================
# CHECK LOGIN
# ==========================================================

def is_logged_in():
    return st.session_state.get("logged_in", False)


# ==========================================================
# GET ROLE
# ==========================================================

def get_role():
    return st.session_state.get("role", "")


# ==========================================================
# GET USERNAME
# ==========================================================

def get_username():
    return st.session_state.get("username", "")


# ==========================================================
# CHANGE PASSWORD
# ==========================================================

def change_password(username, old_password, new_password):
    """
    Change user password.
    """

    if len(new_password) < 4:
        st.warning("Password must be at least 4 characters.")
        return False

    conn = get_connection()

    if conn is None:
        return False

    cursor = conn.cursor()

    try:

        cursor.execute("""
            SELECT *
            FROM users
            WHERE username=%s
            AND password=%s
        """, (username, old_password))

        user = cursor.fetchone()

        if not user:
            st.error("Old password is incorrect.")
            return False

        cursor.execute("""
            UPDATE users
            SET password=%s
            WHERE username=%s
        """, (new_password, username))

        conn.commit()

        st.success("Password changed successfully.")

        return True

    except Exception as e:
        conn.rollback()
        st.error(e)
        return False

    finally:
        cursor.close()
        conn.close()