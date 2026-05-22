import mysql.connector

connection = mysql.connector.connect(
    host="localhost",
    user="root",
    password="9788",
    database="smart_finance_tracker"
)

cursor = connection.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses(
    id INT PRIMARY KEY AUTO_INCREMENT,
    title VARCHAR(255),
    category VARCHAR(100),
    amount DECIMAL(10,2),
    expense_date DATE
)
""")

connection.commit()

connection.close()

print("Database table created successfully!")