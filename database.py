import mysql.connector
import streamlit as st


def get_connection():
  return mysql.connector.connect(
      host=st.secrets["tidb"]["host"],
      port=int(st.secrets["tidb"]["port"]),
      user=st.secrets["tidb"]["user"],
      password=st.secrets["tidb"]["password"],
      database=st.secrets["tidb"]["database"],
      ssl_verify_cert=True, 
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
