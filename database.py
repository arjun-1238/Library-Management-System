import streamlit as st
import pymysql

def get_connection():
    """
    Opens a fresh MySQL connection using PyMySQL and Streamlit's secrets.
    """
    return pymysql.connect(
        host=st.secrets["db_host"],
        port=int(st.secrets["db_port"]),
        user=st.secrets["db_user"],
        password=st.secrets["db_password"],
        database=st.secrets["db_name"],
        ssl={'ssl': {}}  # Aiven Cloud ke liye secure SSL connection mandatory hai
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