import sqlite3

def fix_db():
    conn = sqlite3.connect('bot.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute("ALTER TABLE blocks ADD COLUMN ui_x INTEGER DEFAULT 0")
        print("Added ui_x column")
    except sqlite3.OperationalError as e:
        print(f"ui_x might already exist: {e}")
        
    try:
        cursor.execute("ALTER TABLE blocks ADD COLUMN ui_y INTEGER DEFAULT 0")
        print("Added ui_y column")
    except sqlite3.OperationalError as e:
        print(f"ui_y might already exist: {e}")
        
    conn.commit()
    conn.close()

if __name__ == "__main__":
    fix_db()
