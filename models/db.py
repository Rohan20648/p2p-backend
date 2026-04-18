import pymysql, os
from flask import jsonify

def get_connection():
    return pymysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DB", "p2p_energy"),
        port=int(os.getenv("MYSQL_PORT", 3306)),
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )

def query(sql, args=None, fetch="all"):
    """Single-query helper. Use transact() for multi-step writes."""
    conn = None
    try:
        conn = get_connection()
        cur  = conn.cursor()
        cur.execute(sql, args or ())
        if fetch == "all":
            data = cur.fetchall()
        elif fetch == "one":
            data = cur.fetchone()
        else:
            # FIX #1: commit was missing for fetch="none" path when exception
            # FIX #8: connection now always closed via finally block
            conn.commit()
            data = {"affected_rows": cur.rowcount, "lastrowid": cur.lastrowid}
        return data, None
    except Exception as e:
        import traceback; traceback.print_exc()
        if conn:
            try: conn.rollback()
            except: pass
        return None, str(e)
    finally:
        # FIX #8: always close connection, even on exception
        if conn:
            try: conn.close()
            except: pass

def transact(steps):
    """
    Run multiple write steps in a single DB transaction.
    steps  — list of (sql, args) tuples executed in order.
    Returns (list_of_results, error_string_or_None).
    On any error the transaction is rolled back.
    """
    conn = None
    try:
        conn = get_connection()
        cur  = conn.cursor()
        results = []
        for sql, args in steps:
            cur.execute(sql, args or ())
            results.append({"affected_rows": cur.rowcount, "lastrowid": cur.lastrowid})
        conn.commit()
        return results, None
    except Exception as e:
        import traceback; traceback.print_exc()
        if conn:
            try: conn.rollback()
            except: pass
        return None, str(e)
    finally:
        if conn:
            try: conn.close()
            except: pass

def transact_with_cursor(fn):
    """
    Advanced helper: runs fn(conn, cur) inside a single transaction.
    fn receives the connection and cursor; fn's return value is returned.
    Use this when you need lastrowid mid-sequence (e.g. order placement).
    """
    conn = None
    try:
        conn = get_connection()
        cur  = conn.cursor()
        result = fn(conn, cur)
        conn.commit()
        return result, None
    except Exception as e:
        import traceback; traceback.print_exc()
        if conn:
            try: conn.rollback()
            except: pass
        return None, str(e)
    finally:
        if conn:
            try: conn.close()
            except: pass

def success(data=None, message="ok", status=200):
    return jsonify({"success": True, "message": message, "data": data}), status

def error(message="An error occurred", status=400):
    return jsonify({"success": False, "message": message}), status
