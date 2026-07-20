import streamlit as st
import mysql.connector


def get_connection():
    """
    Opens a fresh MySQL connection using Streamlit's secrets.
    Works identically on your laptop (.streamlit/secrets.toml) and on
    Streamlit Community Cloud (Secrets set in the app dashboard) —
    no .env / python-dotenv needed.
    """
    return mysql.connector.connect(
        host=st.secrets["db_host"],
        port=int(st.secrets["db_port"]),
        user=st.secrets["db_user"],
        password=st.secrets["db_password"],
        database=st.secrets["db_name"],
        ssl_mode='REQUIRED'  ,# Aiven database ke liye zaroori ho sakta hai
)
    


def fetch_one(query, params=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        return cursor.fetchone()
    finally:
        cursor.close()
        conn.close()


def fetch_all(query, params=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def record_exists(query, params=None):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query, params or ())
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()