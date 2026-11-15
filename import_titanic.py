import pandas as pd
import psycopg2

# Read the CSV file
df = pd.read_csv("Titanic-Dataset.csv")

# Connect to PostgreSQL
conn = psycopg2.connect(
    host="localhost",
    database="titanic_db",
    user="postgres",
    password="",
    port="5432"
)

cursor = conn.cursor()

# Insert data using the correct column order
columns = [
    "PassengerId", "Survived", "Pclass", "Name",
    "Sex", "Age", "SibSp", "Parch", "Ticket",
    "Fare", "Cabin", "Embarked"
]
insert_query = """
INSERT INTO titanic_project.titanic_staging
(passengerid, survived, pclass, name, sex, age,
 sibsp, parch, ticket, fare, cabin, embarked)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

# Replace pandas NaN values with Python None (SQL NULL)
df = df.where(pd.notnull(df), None)

for row in df[columns].itertuples(index=False, name=None):
    cursor.execute(insert_query, row)

conn.commit()

print("Titanic data imported successfully!")

cursor.close()
conn.close()