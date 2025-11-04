from db.database import engine
import sqlite3

def column_exists(conn, table, column):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info('{table}')")
    cols = [row[1] for row in cur.fetchall()]
    return column in cols

def add_is_admin():
    # Connect with sqlite3 to run PRAGMA and ALTER statements
    db_path = engine.url.database
    if not db_path:
        print("Could not determine SQLite database path from engine.url")
        return

    conn = sqlite3.connect(db_path)
    try:
        if column_exists(conn, 'users', 'is_admin'):
            print('Column is_admin already exists on users table.')
            return

        # SQLite supports adding a column with a default value. Use 0 for False.
        alter_sql = "ALTER TABLE users ADD COLUMN is_admin BOOLEAN NOT NULL DEFAULT 0"
        print('Adding is_admin column to users table...')
        conn.execute(alter_sql)
        conn.commit()
        print('is_admin column added successfully.')
    except Exception as e:
        print('Error while adding is_admin column:', e)
    finally:
        conn.close()

if __name__ == '__main__':
    add_is_admin()
