import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import os

DATABASE = 'data.db'

def init_database():
    """Initialize database with necessary tables"""
    try:
        conn = init_db()
        cursor = conn.cursor()
        
        # Create conversation history table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question TEXT NOT NULL,
            sql_query TEXT NOT NULL,
            results TEXT NOT NULL,
            explanation TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            expires_at DATETIME NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Error initializing database: {str(e)}")
        raise

def init_db():
    """Initialize database connection"""
    try:
        # Use absolute path to the database file
        db_path = os.path.join(os.path.dirname(__file__), DATABASE)
        conn = sqlite3.connect(db_path)
        return conn
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        raise

def get_table_schema():
    """Get detailed schema information for all tables"""
    schema = {}
    try:
        with init_db() as conn:
            cursor = conn.cursor()
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                cursor.execute(f"PRAGMA table_info({table_name});")
                columns = cursor.fetchall()
                schema[table_name] = {
                    'columns': [col[1] for col in columns],
                    'types': [col[2] for col in columns]
                }
        return schema
    except Exception as e:
        print(f"Error getting schema: {str(e)}")
        return {}

def create_table_from_file(df, table_name):
    """Create a new table in SQLite database from DataFrame"""
    try:
        conn = init_db()
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        print(f"Created table {table_name} with {len(df)} rows")  # Debug print
        
        # Verify the table was created
        cursor = conn.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cursor.fetchone()[0]
        print(f"Verified table {table_name} has {count} rows")  # Debug print
        
        conn.close()
    except Exception as e:
        print(f"Error creating table {table_name}: {str(e)}")
        raise

def remove_table(table_name):
    """Remove a table from the database"""
    try:
        with init_db() as conn:
            cursor = conn.cursor()
            cursor.execute(f"DROP TABLE IF EXISTS {table_name};")
        return True
    except Exception as e:
        print(f"Error removing table {table_name}: {str(e)}")
        raise

# Unused functions commented out:
"""
def get_recent_conversations():
    #Get conversations from last 24 hours
    conn = init_db()
    cursor = conn.cursor()
    
    # Clean up expired conversations
    cleanup_expired_conversations()
    
    # Get valid conversations
    cursor.execute('''
    SELECT question, sql_query, results, explanation, timestamp
    FROM conversation_history
    WHERE expires_at > CURRENT_TIMESTAMP
    ORDER BY timestamp DESC
    ''')
    
    conversations = cursor.fetchall()
    conn.close()
    
    return [
        {
            'question': conv[0],
            'sql_query': conv[1],
            'results': conv[2],
            'explanation': conv[3],
            'timestamp': conv[4]
        }
        for conv in conversations
    ]

def cleanup_expired_conversations():
    #Delete conversations older than 24 hours
    conn = init_db()
    cursor = conn.cursor()
    
    cursor.execute('''
    DELETE FROM conversation_history
    WHERE expires_at <= CURRENT_TIMESTAMP
    ''')
    
    conn.commit()
    conn.close()
""" 