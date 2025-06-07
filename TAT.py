import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import mysql.connector
from mysql.connector import Error

# Set page config for wide layout
st.set_page_config(page_title="Patient Distribution Dashboard", layout="wide")

# Custom CSS for the desired color scheme (white background, black chart containers)
st.markdown("""
    <style>
        /* Main white background */
        body, .stApp {
            background-color: white !important;
        }
        
        /* Black containers for charts/tables */
        .stPlotlyChart, .stDataFrame, .stDataFrame table {
            background-color: black !important;
            border-radius: 10px;
            padding: 15px;
        }
        
        /* Table styling */
        table {
            background-color: black !important;
            color: white !important;
            border: 1px solid #444 !important;
        }
        
        th, td {
            background-color: black !important;
            color: white !important;
            border: 1px solid #444 !important;
        }
        
        /* Chart title color */
        .gtitle {
            color: white !important;
        }
        
        /* Legend text color */
        .legendtext {
            color: white !important;
        }
        
        /* Remove extra padding around elements */
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
    </style>
""", unsafe_allow_html=True)

# Function to check if a column exists in the table
def column_exists(cursor, table_name, column_name):
    try:
        cursor.execute(f"""
            SELECT COUNT(*)
            FROM information_schema.columns
            WHERE table_name = '{table_name}' AND column_name = '{column_name}'
        """)
        return cursor.fetchone()[0] > 0
    except Error as e:
        st.error(f"Error checking column {column_name}: {e}")
        return False

# Function to fetch patient data from MySQL
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_patient_data():
    try:
        conn = mysql.connector.connect(
           host="35.209.69.119",  # Replace with your MySQL host
            user="u0iky3cyvfnfy",        # Replace with your MySQL user
            password="Thisisme@2026",# Replace with your MySQL password
            database="db4idjmbjsqwkf" # Replace with your database name

        )
        cursor = conn.cursor()

        # Check for required columns
        table_name = 'patient'
        required_columns = ['patient_id', 'deleted_at', 'gender', 'patient_status', 'age_category', 'dob']
        available_columns = {col: column_exists(cursor, table_name, col) for col in required_columns}

        # Query total patients
        total_query = "SELECT COUNT(DISTINCT patient_id) as total_patients FROM patient WHERE deleted_at IS NULL"
        try:
            total_df = pd.read_sql(total_query, conn)
            total_patients = int(total_df['total_patients'].iloc[0]) if not total_df.empty else 0
        except Error as e:
            st.error(f"Total Patients query failed: {e}")
            total_patients = 0

        # Query gender distribution
        if available_columns['gender']:
            gender_query = """
                SELECT gender, COUNT(DISTINCT patient_id) as count
                FROM patient
                WHERE deleted_at IS NULL
                GROUP BY gender
            """
            try:
                gender_df = pd.read_sql(gender_query, conn)
            except Error as e:
                st.error(f"Gender query failed: {e}")
                gender_df = pd.DataFrame({'gender': ['No Data'], 'count': [0]})
        else:
            gender_df = pd.DataFrame({'gender': ['No Data'], 'count': [0]})
            st.warning("Gender column not found in patient table.")

        # Query patient_status distribution
        if available_columns['patient_status']:
            status_query = """
                SELECT patient_status, COUNT(DISTINCT patient_id) as count
                FROM patient
                WHERE deleted_at IS NULL
                GROUP BY patient_status
            """
            try:
                status_df = pd.read_sql(status_query, conn)
            except Error as e:
                st.error(f"Patient Status query failed: {e}")
                status_df = pd.DataFrame({'patient_status': ['No Data'], 'count': [0]})
        else:
            status_df = pd.DataFrame({'patient_status': ['No Data'], 'count': [0]})
            st.warning("Patient Status column not found in patient table.")

        # Query age category distribution
        if available_columns['age_category']:
            age_query = """
                SELECT age_category, COUNT(DISTINCT patient_id) as count
                FROM patient
                WHERE deleted_at IS NULL
                GROUP BY age_category
            """
            try:
                age_df = pd.read_sql(age_query, conn)
                if age_df.empty or age_df['age_category'].isnull().all():
                    raise Error("Age category data is empty or all NULL")
            except Error as e:
                st.warning(f"Age Category query failed or empty: {e}. Falling back to DOB.")
                if available_columns['dob']:
                    age_query = """
                        SELECT 
                            CASE 
                                WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) < 12 THEN '<12 yrs'
                                WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) BETWEEN 13 AND 17 THEN '13-17 yrs'
                                WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) BETWEEN 18 AND 35 THEN '18-35 yrs'
                                WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) > 35 THEN '>35 yrs'
                                ELSE 'Unknown'
                            END as age_category,
                            COUNT(DISTINCT patient_id) as count
                        FROM patient
                        WHERE deleted_at IS NULL
                        GROUP BY age_category
                    """
                    try:
                        age_df = pd.read_sql(age_query, conn)
                    except Error as e:
                        st.error(f"DOB-based Age Category query failed: {e}")
                        age_df = pd.DataFrame({'age_category': ['No Data'], 'count': [0]})
                else:
                    age_df = pd.DataFrame({'age_category': ['No Data'], 'count': [0]})
                    st.warning("DOB column not found in patient table.")
        else:
            st.warning("Age Category column not found. Falling back to DOB.")
            if available_columns['dob']:
                age_query = """
                    SELECT 
                        CASE 
                            WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) < 12 THEN '<12 yrs'
                            WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) BETWEEN 13 AND 17 THEN '13-17 yrs'
                            WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) BETWEEN 18 AND 35 THEN '18-35 yrs'
                            WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) > 35 THEN '>35 yrs'
                            ELSE 'Unknown'
                        END as age_category,
                        COUNT(DISTINCT patient_id) as count
                    FROM patient
                    WHERE deleted_at IS NULL
                    GROUP BY age_category
                """
                try:
                    age_df = pd.read_sql(age_query, conn)
                except Error as e:
                    st.error(f"DOB-based Age Category query failed: {e}")
                    age_df = pd.DataFrame({'age_category': ['No Data'], 'count': [0]})
            else:
                age_df = pd.DataFrame({'age_category': ['No Data'], 'count': [0]})
                st.warning("DOB column not found in patient table.")

        conn.close()
        return {
            'total': total_patients,
            'gender': gender_df,
            'status': status_df,
            'age': age_df
        }
    except Error as e:
        st.error(f"Database connection error: {e}")
        return {
            'total': 0,
            'gender': pd.DataFrame({'gender': ['No Data'], 'count': [0]}),
            'status': pd.DataFrame({'patient_status': ['No Data'], 'count': [0]}),
            'age': pd.DataFrame({'age_category': ['No Data'], 'count': [0]})
        }

# Function to create donut chart with black background
def create_donut_chart(labels, values, title):
    fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker=dict(colors=['#3b82f6', '#10b981', '#f59e0b', '#ef4444'], line=dict(color='#000', width=2)),
            textinfo='label+value',
            textfont=dict(color='white', size=14),
            hoverinfo='label+value',
            showlegend=True
        )
    ])
    fig.update_layout(
        height=300,
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white', size=12),
        title=dict(text=title, font=dict(color='white', size=16), x=0.5, xanchor='center'),
        legend=dict(
            font=dict(color='white', weight='bold'),
            orientation='h',
            yanchor='bottom',
            y=-0.2,
            xanchor='center',
            x=0.5
        ),
        margin=dict(t=40, b=80, l=20, r=20)
    )
    return fig

# Main app
st.title("Patient Distribution Dashboard")

# Fetch data
data = fetch_patient_data()
total_patients = data['total']
gender_df = data['gender']
status_df = data['status']
age_df = data['age']

# Create 2-column layout
col1, col2 = st.columns(2)

# Column 1 - Top Chart (Total Patients)
with col1:
    st.subheader("Total Patients")
    series = [total_patients] if total_patients > 0 else [0]
    labels = ["Total Patients"] if total_patients > 0 else ["No Data"]
    fig = create_donut_chart(labels, series, "Total Patients")
    st.plotly_chart(fig, use_container_width=True)
    
    # Table below the chart
    table_data = [{"label": "Total Patients", "count": total_patients}] if total_patients > 0 else [{"label": "No Data", "count": 0}]
    df_table = pd.DataFrame(table_data)
    st.dataframe(
        df_table,
        use_container_width=True,
        column_config={
            "label": st.column_config.TextColumn("Label"),
            "count": st.column_config.NumberColumn("Count", format="%d")
        },
        hide_index=True
    )

# Column 1 - Bottom Chart (Patients by Gender)
with col1:
    st.subheader("Patients by Gender")
    if not gender_df.empty and not gender_df['gender'].eq('No Data').all():
        labels = gender_df['gender'].fillna('Unknown').tolist()
        values = gender_df['count'].tolist()
        table_data = [{"label": gender if gender else "Unknown", "count": count} for gender, count in zip(gender_df['gender'], gender_df['count'])]
    else:
        labels = ["No Data"]
        values = [0]
        table_data = [{"label": "No Data", "count": 0}]
    
    fig = create_donut_chart(labels, values, "Patients by Gender")
    st.plotly_chart(fig, use_container_width=True)
    
    # Table below the chart
    df_table = pd.DataFrame(table_data)
    st.dataframe(
        df_table,
        use_container_width=True,
        column_config={
            "label": st.column_config.TextColumn("Label"),
            "count": st.column_config.NumberColumn("Count", format="%d")
        },
        hide_index=True
    )

# Column 2 - Top Chart (Patients by Status)
with col2:
    st.subheader("Patients by Status")
    if not status_df.empty and not status_df['patient_status'].eq('No Data').all():
        labels = status_df['patient_status'].fillna('Unknown').tolist()
        values = status_df['count'].tolist()
        table_data = [{"label": status if status else "Unknown", "count": count} for status, count in zip(status_df['patient_status'], status_df['count'])]
    else:
        labels = ["No Data"]
        values = [0]
        table_data = [{"label": "No Data", "count": 0}]
    
    fig = create_donut_chart(labels, values, "Patients by Status")
    st.plotly_chart(fig, use_container_width=True)
    
    # Table below the chart
    df_table = pd.DataFrame(table_data)
    st.dataframe(
        df_table,
        use_container_width=True,
        column_config={
            "label": st.column_config.TextColumn("Status"),
            "count": st.column_config.NumberColumn("Count", format="%d")
        },
        hide_index=True
    )

# Column 2 - Bottom Chart (Patients by Age Category)
with col2:
    st.subheader("Patients by Age Category")
    if not age_df.empty and not age_df['age_category'].eq('No Data').all():
        labels = age_df['age_category'].fillna('Unknown').tolist()
        values = age_df['count'].tolist()
        table_data = [{"label": age_category if age_category else "Unknown", "count": count} for age_category, count in zip(age_df['age_category'], age_df['count'])]
    else:
        labels = ["No Data"]
        values = [0]
        table_data = [{"label": "No Data", "count": 0}]
    
    fig = create_donut_chart(labels, values, "Patients by Age Category")
    st.plotly_chart(fig, use_container_width=True)
    
    # Table below the chart
    df_table = pd.DataFrame(table_data)
    st.dataframe(
        df_table,
        use_container_width=True,
        column_config={
            "label": st.column_config.TextColumn("Age Category"),
            "count": st.column_config.NumberColumn("Count", format="%d")
        },
        hide_index=True
    )
