import streamlit as st
import psycopg2
import pandas as pd

# Page Configuration
st.set_page_config(
    page_title="Titanic Project",
    page_icon="🚢",
    layout="wide"
)

st.title("🚢 Titanic Data Analysis")


# PostgreSQL Connection and Data Import
from psycopg2.extras import execute_values

def get_connection():
    db = st.secrets["postgres"]
    return psycopg2.connect(
        host=db["host"],
        database=db["database"],
        user=db["user"],
        password=db["password"],
        port=db["port"],
        sslmode=db["sslmode"]
    )

try:
    conn = get_connection()
    st.success("PostgreSQL connected successfully!")

    # Check whether the Neon table currently contains passenger records.
    df = pd.read_sql_query(
        "SELECT * FROM titanic_project.passengers ORDER BY passengerid;",
        conn
    )

    if df.empty:
        st.warning("Your passengers table exists, but it contains no records.")
        st.subheader("Import Titanic CSV into Neon")
        uploaded_file = st.file_uploader(
            "Choose your Titanic-Dataset.csv file",
            type=["csv"]
        )

        if uploaded_file is not None:
            try:
                upload_df = pd.read_csv(uploaded_file)
                upload_df.columns = [str(col).strip().lower() for col in upload_df.columns]

                csv_columns = [
                    "passengerid", "survived", "pclass", "name", "sex",
                    "age", "sibsp", "parch", "ticket", "fare", "cabin", "embarked"
                ]

                missing = [col for col in csv_columns if col not in upload_df.columns]
                if missing:
                    st.error("CSV is missing these columns: " + ", ".join(missing))
                    conn.close()
                    st.stop()

                upload_df = upload_df[csv_columns].copy()
                upload_df = upload_df.astype(object).where(pd.notna(upload_df), None)

                rows = [tuple(row) for row in upload_df.itertuples(index=False, name=None)]

                with conn.cursor() as cur:
                    execute_values(
                        cur,
                        """
                        INSERT INTO titanic_project.passengers
                        (passengerid, survived, pclass, name, sex, age, sibsp,
                         parch, ticket, fare, cabin, embarked)
                        VALUES %s
                        ON CONFLICT (passengerid) DO NOTHING
                        """,
                        rows,
                        page_size=500
                    )

                conn.commit()
                conn.close()
                st.success(f"Imported {len(rows)} CSV rows (existing passenger IDs were skipped).")
                st.rerun()

            except Exception as import_error:
                conn.rollback()
                conn.close()
                st.error(f"CSV import failed: {import_error}")
                st.stop()

        conn.close()
        st.info("Upload your Titanic CSV above to populate the Neon passengers table.")
        st.stop()

    conn.close()

    # Normalize column names for consistent use throughout the dashboard.
    df.columns = [str(column).lower() for column in df.columns]

    required_columns = {"passengerid", "survived", "pclass", "name", "sex"}
    missing_columns = required_columns.difference(df.columns)
    if missing_columns:
        st.error("The passengers table is missing required columns: " + ", ".join(sorted(missing_columns)))
        st.stop()

    st.success(f"Loaded {len(df)} passenger records from Neon.")

    # Dataset Overview
    st.header("📊 Dataset Overview")

    col1, col2, col3 = st.columns(3)

    col1.metric("Total Passengers", len(df))
    col2.metric("Survived", int(df["survived"].sum()))
    col3.metric(
        "Did Not Survive",
        int((df["survived"] == 0).sum())
    )

    # Passenger Data
    st.subheader("Passenger Data")

    st.dataframe(
        df.head(10),
        use_container_width=True
    )

    # Survival Analysis
    st.header("📈 Survival Analysis")

    survival_data = df["survived"].value_counts()

    survival_data.index = [
        "Did Not Survive" if i == 0 else "Survived"
        for i in survival_data.index
    ]

    st.bar_chart(survival_data)

    # Survival by Gender
    st.subheader("Survival by Gender")

    gender_data = df.groupby("sex")["survived"].sum()
    st.bar_chart(gender_data)

    # Passengers by Class
    st.subheader("Passengers by Class")

    class_data = df["pclass"].value_counts().sort_index()
    st.bar_chart(class_data)

    # Data Explorer
    st.header("🔎 Data Explorer")

    selected_class = st.multiselect(
        "Select Passenger Class",
        options=[1, 2, 3],
        default=[1, 2, 3]
    )

    selected_gender = st.multiselect(
        "Select Gender",
        options=["male", "female"],
        default=["male", "female"]
    )

    search_name = st.text_input("Search Passenger Name")

    filtered_df = df[
        (df["pclass"].isin(selected_class)) &
        (df["sex"].isin(selected_gender))
    ]

    if search_name:
        filtered_df = filtered_df[
            filtered_df["name"].str.contains(
                search_name,
                case=False,
                na=False
            )
        ]

    st.write("Total matching passengers:", len(filtered_df))

    st.dataframe(
        filtered_df,
        use_container_width=True
    )

    # SQL Practice
    st.header("💻 SQL Practice")

    queries = {
        "Passengers by Gender": """
            SELECT sex, COUNT(*) AS total_passengers
            FROM titanic_project.passengers
            GROUP BY sex;
        """,

        "Passengers by Class": """
            SELECT pclass, COUNT(*) AS total_passengers
            FROM titanic_project.passengers
            GROUP BY pclass
            ORDER BY pclass;
        """,

        "Average Age by Class": """
            SELECT pclass,
                   ROUND(AVG(age)::numeric, 2) AS average_age
            FROM titanic_project.passengers
            GROUP BY pclass
            ORDER BY pclass;
        """,

        "Survival by Gender": """
            SELECT sex,
                   SUM(survived) AS survivors,
                   ROUND(
                       100.0 * SUM(survived) / COUNT(*), 2
                   ) AS survival_percentage
            FROM titanic_project.passengers
            GROUP BY sex;
        """
    }

    selected_query = st.selectbox(
        "Choose an SQL Query",
        list(queries.keys())
    )

    st.code(queries[selected_query], language="sql")

    if st.button("Run SQL Query"):
        try:
            with get_connection() as sql_conn:

                result = pd.read_sql_query(
                    queries[selected_query],
                    sql_conn
                )

            st.success("Query executed successfully!")
            st.dataframe(result, use_container_width=True)

        except Exception as e:
            st.error(f"SQL Error: {e}")

    # Interactive Test
    st.header("📝 Titanic Interactive Test")

    questions = [
        {
            "question": "1. How many passengers are in the dataset?",
            "options": ["500", "891", "1000", "1200"],
            "answer": "891",
            "explanation": "The dataset contains 891 passengers."
        },
        {
            "question": "2. Which column represents survival?",
            "options": ["Pclass", "Age", "Survived", "Fare"],
            "answer": "Survived",
            "explanation": "Survived indicates whether a passenger survived."
        },
        {
            "question": "3. What does Survived = 1 mean?",
            "options": ["Died", "Survived", "Missing", "Unknown"],
            "answer": "Survived",
            "explanation": "1 means survived and 0 means did not survive."
        },
        {
            "question": "4. Which SQL function counts records?",
            "options": ["SUM()", "AVG()", "COUNT()", "MAX()"],
            "answer": "COUNT()",
            "explanation": "COUNT() returns the number of records."
        },
        {
            "question": "5. Which class had the most passengers?",
            "options": ["First", "Second", "Third", "Equal"],
            "answer": "Third",
            "explanation": "Third class had 491 passengers."
        },
        {
            "question": "6. Which gender had a higher survival rate?",
            "options": ["Male", "Female", "Equal", "Unknown"],
            "answer": "Female",
            "explanation": "Female passengers had a higher survival rate."
        },
        {
            "question": "7. Which SQL clause groups records?",
            "options": ["WHERE", "GROUP BY", "ORDER BY", "LIMIT"],
            "answer": "GROUP BY",
            "explanation": "GROUP BY groups rows with matching values."
        },
        {
            "question": "8. Which column stores passenger age?",
            "options": ["Fare", "Age", "SibSp", "Parch"],
            "answer": "Age",
            "explanation": "The Age column stores passenger age."
        },
        {
            "question": "9. Which SQL function calculates average?",
            "options": ["COUNT()", "SUM()", "AVG()", "MIN()"],
            "answer": "AVG()",
            "explanation": "AVG() calculates the average value."
        },
        {
            "question": "10. What does NULL represent in SQL?",
            "options": ["Zero", "Empty string", "Missing value", "False"],
            "answer": "Missing value",
            "explanation": "NULL represents an unknown or missing value."
        },
        {
            "question": "11. Which Python library is used for data analysis?",
            "options": ["Pandas", "Turtle", "Random", "Math"],
            "answer": "Pandas",
            "explanation": "Pandas is used for data manipulation and analysis."
        },
        {
            "question": "12. Which library creates the web application?",
            "options": ["NumPy", "Streamlit", "Psycopg2", "Matplotlib"],
            "answer": "Streamlit",
            "explanation": "Streamlit helps create interactive web applications."
        },
        {
            "question": "13. Which library connects Python to PostgreSQL?",
            "options": ["Pandas", "Psycopg2", "Streamlit", "OS"],
            "answer": "Psycopg2",
            "explanation": "Psycopg2 connects Python applications to PostgreSQL."
        },
        {
            "question": "14. Which SQL clause filters records?",
            "options": ["WHERE", "GROUP BY", "SELECT", "INSERT"],
            "answer": "WHERE",
            "explanation": "WHERE filters records based on a condition."
        },
        {
            "question": "15. How many passengers survived?",
            "options": ["549", "342", "891", "177"],
            "answer": "342",
            "explanation": "342 passengers survived."
        }
    ]

    with st.form("titanic_quiz"):

        user_answers = []

        for i, q in enumerate(questions):

            st.write(f"**{q['question']}**")

            answer = st.radio(
                "Choose your answer:",
                q["options"],
                key=f"quiz_{i}"
            )

            user_answers.append(answer)

        submitted = st.form_submit_button("Submit Test")

    if submitted:

        score = 0

        for i, q in enumerate(questions):
            if user_answers[i] == q["answer"]:
                score += 1

        percentage = (score / len(questions)) * 100

        st.subheader("🎯 Your Test Results")

        st.metric("Your Score", f"{score}/15")
        st.metric("Percentage", f"{percentage:.2f}%")

        if percentage >= 80:
            st.success("Excellent work!")
        elif percentage >= 50:
            st.info("Good effort! Keep practising.")
        else:
            st.warning("Keep learning and try again.")

        st.subheader("Answer Explanations")

        for i, q in enumerate(questions):

            if user_answers[i] == q["answer"]:
                st.success(f"Q{i+1}: Correct")
            else:
                st.error(
                    f"Q{i+1}: Incorrect. Correct answer: {q['answer']}"
                )

            st.write(q["explanation"])


except Exception as e:
    st.error(f"Database / application error: {e}")