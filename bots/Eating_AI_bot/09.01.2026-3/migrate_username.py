import sqlite3

def migrate():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE bot_users ADD COLUMN username VARCHAR")
        conn.commit()
        print("Successfully added username column to bot_users")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("Column username already exists")
        else:
            print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
