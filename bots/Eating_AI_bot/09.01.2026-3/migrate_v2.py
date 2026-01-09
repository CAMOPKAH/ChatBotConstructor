import sqlite3
import os
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def migrate():
    db_path = 'bot.db'
    if not os.path.exists(db_path):
        print("Database not found, skipping migration.")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # 1. Create new tables
        print("Creating new tables...")
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR NOT NULL UNIQUE,
            password_hash VARCHAR NOT NULL,
            role VARCHAR DEFAULT 'user',
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workflows (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR NOT NULL,
            description TEXT,
            owner_id INTEGER,
            telegram_token VARCHAR,
            openai_key VARCHAR,
            status VARCHAR DEFAULT 'stopped',
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (owner_id) REFERENCES admin_users (id)
        )
        """)
        
        # 2. Add workflow_id to existing tables
        tables = ['blocks', 'bot_users', 'user_sessions', 'user_params', 'trace']
        for table in tables:
            try:
                cursor.execute(f"ALTER TABLE {table} ADD COLUMN workflow_id INTEGER REFERENCES workflows(id)")
                print(f"Added workflow_id to {table}")
            except sqlite3.OperationalError as e:
                if "duplicate column" in str(e):
                    print(f"workflow_id already exists in {table}")
                else:
                    print(f"Error adding column to {table}: {e}")

        # 3. Create Default Admin
        print("Creating default admin...")
        admin_user = cursor.execute("SELECT * FROM admin_users WHERE username='Admin'").fetchone()
        if not admin_user:
            hashed_pw = pwd_context.hash("123456")
            cursor.execute("INSERT INTO admin_users (username, password_hash, role) VALUES (?, ?, ?)", 
                           ("Admin", hashed_pw, "admin"))
            admin_id = cursor.lastrowid
            print(f"Created Admin user (ID: {admin_id})")
        else:
            admin_id = admin_user[0]
            print("Admin user already exists")

        # 4. Create Default Workflow
        print("Creating default workflow...")
        workflow = cursor.execute("SELECT * FROM workflows WHERE name='Legacy Workflow'").fetchone()
        if not workflow:
            cursor.execute("INSERT INTO workflows (name, description, owner_id, status) VALUES (?, ?, ?, ?)", 
                           ("Legacy Workflow", "Imported from previous version", admin_id, "stopped"))
            workflow_id = cursor.lastrowid
            print(f"Created Legacy Workflow (ID: {workflow_id})")
            
            # 5. Migrate Data
            print("Migrating data to Legacy Workflow...")
            for table in tables:
                cursor.execute(f"UPDATE {table} SET workflow_id = ? WHERE workflow_id IS NULL", (workflow_id,))
                print(f"Updated {cursor.rowcount} rows in {table}")
        else:
            print("Legacy Workflow already exists")

        conn.commit()
        print("Migration completed successfully.")
        
    except Exception as e:
        print(f"Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
