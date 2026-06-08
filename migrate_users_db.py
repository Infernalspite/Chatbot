import pymysql

def migrate():
    try:
        # Establish connection to the local MySQL database
        connection = pymysql.connect(
            host='localhost',
            user='root',
            password='Gokulj7959$',
            database='fakedb',
            port=3030,
        )
        print("Connected to MySQL database successfully!")
        
        with connection.cursor() as cursor:
            # Check if password column already exists
            cursor.execute("DESCRIBE users")
            columns = cursor.fetchall()
            column_names = [col[0] for col in columns]
            
            if 'password' not in column_names:
                print("Adding 'password' column to 'users' table...")
                cursor.execute("ALTER TABLE users ADD COLUMN password VARCHAR(255) DEFAULT NULL")
                print("Column 'password' added successfully!")
            else:
                print("'password' column already exists in 'users' table.")
            
            # Seed default password ("1234") for users with NULL passwords
            cursor.execute("SELECT id, name FROM users WHERE password IS NULL")
            users_to_update = cursor.fetchall()
            
            if users_to_update:
                default_password = "1234"
                print(f"Updating {len(users_to_update)} users with default raw password '{default_password}'...")
                for user_id, name in users_to_update:
                    print(f"Setting default password for user '{name}' (ID: {user_id})")
                    cursor.execute(
                        "UPDATE users SET password = %s WHERE id = %s",
                        (default_password, user_id)
                    )
                connection.commit()
                print("Default passwords seeded successfully!")
            else:
                print("No users need default password seeding.")
                
    except Exception as e:
        print("Migration failed:", e)
    finally:
        if 'connection' in locals() and connection:
            connection.close()

if __name__ == "__main__":
    migrate()
