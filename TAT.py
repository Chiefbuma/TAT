import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import mysql.connector
from mysql.connector import Error

# Set page config for wide layout
st.set_page_config(page_title="Patient Distribution Dashboard", layout="wide")

# Custom CSS for styling
st.markdown("""
    <style>
        /* Main white background */
        body, .stApp {
            background-color: white !important;
        }
        
        /* Container styling for charts and tables */
        .chart-container {
            background-color: black !important;
            border-radius: 10px;
            padding: 15px;
            height: 500px; /* Fixed height for all containers */
            margin-bottom: 20px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        
        /* Table styling */
        table {
            background-color: black !important;
            color: white !important;
            border: 1px solid #444 !important;
            width: 100%;
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
        
        /* Chart part */
        .chart-part {
            flex: 2; /* Allocate more space to chart */
        }
        
        /* Table part */
        .table-part {
            flex: 1; /* Allocate less space to table */
            overflow: auto;
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
@st.cache_data(ttl=300)
def fetch_patient_data():
    try:
        conn = mysql.connector.connect(
            host="35.209.69.119",
            user="u0iky3cyvfnfy",
            password="Thisisme@2026",
            database="db4idjmbjsqwkf"
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

# Function to create donut chart with larger size
def create_donut_chart(labels, values, title, total):
    percentages = [(value / total * 100) if total > 0 else 0 for value in values]
    text_labels = [f"{label}<br>{value}<br>{percent:.1f}%" for label, value, percent in zip(labels, values, percentages)]
    
    fig = go.Figure(data=[
        go.Pie(
            labels=labels,
            values=values,
            hole=0.4,
            marker=dict(colors=['#3b82f6', '#10b981', '#f59e0b', '#ef4444'], line=dict(color='#000', width=2)),
            text=text_labels,
            textinfo='text',
            textfont=dict(color='white', size=14),
            hoverinfo='label+value+percent',
            showlegend=True
        )
    ])
    fig.update_layout(
        height=350,  # Increased chart size
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white', size=12),
        title=dict(text=title, font=dict(color='white', size=16), x=0.5, xanchor='center'),
        legend=dict(
            font=dict(color='white'),
            orientation='h',
            yanchor='bottom',
            y=-0.2,
            xanchor='center',
            x=0.5
        ),
        margin=dict(t=40, b=80, l=20, r=20)
    )
    return fig

# Function to create bar chart with larger size
def create_bar_chart(labels, values, title, total):
    percentages = [(value / total * 100) if total > 0 else 0 for value in values]
    text_labels = [f"{value}<br>{percent:.1f}%" for value, percent in zip(values, percentages)]
    
    fig = go.Figure(data=[
        go.Bar(
            x=labels,
            y=values,
            text=text_labels,
            textposition='auto',
            marker=dict(
                color=['#3b82f6', '#10b981', '#f59e0b', '#ef4444'],
                line=dict(color='#000', width=2)
            ),
            hoverinfo='x+y+text'
        )
    ])
    fig.update_layout(
        height=350,  # Increased chart size
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white', size=12),
        title=dict(text=title, font=dict(color='white', size=16), x=0.5, xanchor='center'),
        xaxis=dict(
            title='Status',
            tickfont=dict(color='white'),
            titlefont=dict(color='white')
        ),
        yaxis=dict(
            title='Count',
            tickfont=dict(color='white'),
            titlefont=dict(color='white')
        ),
        margin=dict(t=40, b=80, l=40, r=40)
    )
    return fig

# Helper function to create table with percentages
def create_table_data(df, label_column, total):
    if not df.empty and not df[label_column].eq('No Data').all():
        labels = df[label_column].fillna('Unknown').tolist()
        counts = df['count'].tolist()
        percentages = [(count / total * 100) if total > 0 else 0 for count in counts]
        table_data = [
            {"label": label if label else "Unknown", "count": count, "percentage": f"{percent:.1f}%"}
            for label, count, percent in zip(labels, counts, percentages)
        ]
    else:
        table_data = [{"label": "No Data", "count": 0, "percentage": "0.0%"}]
    return pd.DataFrame(table_data)

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

# Column 1 - Total Patients
with col1:
    with st.container():
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("Total Patients")
        series = [total_patients] if total_patients > 0 else [0]
        labels = ["Total Patients"] if total_patients > 0 else ["No Data"]
        fig = create_donut_chart(labels, series, "Total Patients", total_patients)
        st.plotly_chart(fig, use_container_width=True)
        
        table_data = [{"label": "Total Patients", "count": total_patients, "percentage": "100.0%"}] if total_patients > 0 else [{"label": "No Data", "count": 0, "percentage": "0.0%"}]
        df_table = pd.DataFrame(table_data)
        st.dataframe(
            df_table,
            use_container_width=True,
            column_config={
                "label": st.column_config.TextColumn("Label"),
                "count": st.column_config.NumberColumn("Count", format="%d"),
                "percentage": st.column_config.TextColumn("Percentage")
            },
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# Column 1 - Patients by Gender
with col1:
    with st.container():
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("Patients by Gender")
        df_table = create_table_data(gender_df, 'gender', total_patients)
        fig = create_donut_chart(df_table['label'].tolist(), df_table['count'].tolist(), "Patients by Gender", total_patients)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            df_table,
            use_container_width=True,
            column_config={
                "label": st.column_config.TextColumn("Gender"),
                "count": st.column_config.NumberColumn("Count", format="%d"),
                "percentage": st.column_config.TextColumn("Percentage")
            },
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# Column 2 - Patients by Status
with col2:
    with st.container():
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("Patients by Status")
        df_table = create_table_data(status_df, 'patient_status', total_patients)
        fig = create_bar_chart(df_table['label'].tolist(), df_table['count'].tolist(), "Patients by Status", total_patients)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            df_table,
            use_container_width=True,
            column_config={
                "label": st.column_config.TextColumn("Status"),
                "count": st.column_config.NumberColumn("Count", format="%d"),
                "percentage": st.column_config.TextColumn("Percentage")
            },
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# Column 2 - Patients by Age Category
with col2:
    with st.container():
        st.markdown('<div class="chart-container">', unsafe_allow_html=True)
        st.subheader("Patients by Age Category")
        df_table = create_table_data(age_df, 'age_category', total_patients)
        fig = create_donut_chart(df_table['label'].tolist(), df_table['count'].tolist(), "Patients by Age Category", total_patients)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            df_table,
            use_container_width=True,
            column_config={
                "label": st.column_config.TextColumn("Age Category"),
                "count": st.column_config.NumberColumn("Count", format="%d"),
                "percentage": st.column_config.TextColumn("Percentage")
            },
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
