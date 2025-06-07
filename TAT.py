import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import mysql.connector
from mysql.connector import Error

# Set page config for wide layout and dark theme
st.set_page_config(page_title="Patient Distribution Dashboard", layout="wide")

# Apply dark theme CSS to match Filament styling
st.markdown("""
    <style>
        body, .stApp {
            background-color: #18181b;
            color: #fff;
        }
        .stDataFrame, table, th, td {
            background-color: #27272a;
            color: #fff;
            border: 1px solid #27272a;
            border-collapse: collapse;
        }
        th, td {
            padding: 0.5rem;
            text-align: left;
        }
        th {
            background-color: #27272a;
        }
        .stDataFrame th:last-child, .stDataFrame td:last-child {
            text-align: right;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid #27272a;
            border-radius: 1rem;
            padding: 1.5rem;
            background-color: #18181b;
        }
    </style>
""", unsafe_allow_html=True)

# Function to check if a column exists in the table
def column_exists(cursor, table_name, column_name):
    cursor.execute(f"""
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_name = '{table_name}' AND column_name = '{column_name}'
    """)
    return cursor.fetchone()[0] > 0

# Function to fetch patient data from MySQL
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_patient_data():
    try:
        conn = mysql.connector.connect(
            host="your_mysql_host",  # Replace with your MySQL host
            user="your_user",        # Replace with your MySQL user
            password="your_password",# Replace with your MySQL password
            database="your_database" # Replace with your database name
        )
        cursor = conn.cursor()

        # Check for required columns
        table_name = 'patient'
        required_columns = ['patient_id', 'deleted_at', 'gender', 'patient_status', 'dob']
        available_columns = {col: column_exists(cursor, table_name, col) for col in required_columns}

        # Query total patients
        total_query = "SELECT COUNT(DISTINCT patient_id) as total_patients FROM patient WHERE deleted_at IS NULL"
        total_df = pd.read_sql(total_query, conn)
        total_patients = int(total_df['total_patients'].iloc[0]) if not total_df.empty else 0

        # Query gender distribution
        if available_columns['gender']:
            gender_query = """
                SELECT gender, COUNT(DISTINCT patient_id) as count
                FROM patient
                WHERE deleted_at IS NULL
                GROUP BY gender
            """
            gender_df = pd.read_sql(gender_query, conn)
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

        # Query age group distribution
        if available_columns['dob']:
            age_query = """
                SELECT 
                    CASE 
                        WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) < 12 THEN '<12 yrs'
                        WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) BETWEEN 13 AND 17 THEN '13-17 yrs'
                        WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) BETWEEN 18 AND 35 THEN '18-35 yrs'
                        WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) > 35 THEN '>35 yrs'
                        ELSE 'Unknown'
                    END as age_group,
                    COUNT(DISTINCT patient_id) as count
                FROM patient
                WHERE deleted_at IS NULL
                GROUP BY age_group
            """
            age_df = pd.read_sql(age_query, conn)
        else:
            age_df = pd.DataFrame({'age_group': ['No Data'], 'count': [0]})
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
            'age': pd.DataFrame({'age_group': ['No Data'], 'count': [0]})
        }

# Function to create donut chart
def create_donut_chart(labels, values, title):
    fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker=dict(colors=['#3b82f6', '#10b981', '#f59e0b', '#ef4444'], line=dict(color='#27272a', width=2)),
            textinfo='label+value',
            textfont=dict(color='#9ca3af', size=14),
            hoverinfo='label+value',
            showlegend=True
        )
    ])
    fig.update_layout(
        height=300,
        paper_bgcolor='#18181b',
        plot_bgcolor='#18181b',
        font=dict(color='#9ca3af', size=12),
        title=dict(text=title, font=dict(color='#fff', size=16), x=0.5, xanchor='center'),
        legend=dict(
            font=dict(color='#9ca3af', weight='bold'),
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

# Total Patients Chart and Table
with st.container():
    st.subheader("Total Patients")
    series = [total_patients] if total_patients > 0 else [0]
    labels = ["Total Patients"] if total_patients > 0 else ["No Data"]
    fig = create_donut_chart(labels, series, "Total Patients")
    st.plotly_chart(fig, use_container_width=True)
    
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

# Gender Distribution Chart and Table
with st.container():
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

# Patient Status Distribution Chart and Table
with st.container():
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

# Age Group Distribution Chart and Table
with st.container():
    st.subheader("Patients by Age Group")
    if not age_df.empty and not age_df['age_group'].eq('No Data').all():
        labels = age_df['age_group'].fillna('Unknown').tolist()
        values = age_df['count'].tolist()
        table_data = [{"label": age_group if age_group else "Unknown", "count": count} for age_group, count in zip(age_df['age_group'], age_df['count'])]
    else:
        labels = ["No Data"]
        values = [0]
        table_data = [{"label": "No Data", "count": 0}]
    
    fig = create_donut_chart(labels, values, "Patients by Age Group")
    st.plotly_chart(fig, use_container_width=True)
    
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
