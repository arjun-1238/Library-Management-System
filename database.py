import streamlit as st
import mysql.connector


def get_connection():
    return mysql.connector.connect(
        host=st.secrets["db_host"],
        port=int(st.secrets.get("db_port", 3306)),
        user=st.secrets["db_user"],
        password=st.secrets["db_password"],
        database=st.secrets["db_name"],
        ssl_disabled=False,   # Aiven requires an SSL connection
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
