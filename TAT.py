import streamlit as st
from streamlit_apexjs import st_apexcharts
import pandas as pd
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
        
        /* Container styling */
        .dashboard-container {
            background-color: black;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 20px;
            height: 650px;
            display: flex;
            flex-direction: column;
            justify-content: space-between;
        }
        
        /* Chart styling */
        .apexcharts-canvas {
            height: 400px !important;
        }
        
        /* Table styling */
        .stDataFrame, .stDataFrame table {
            background-color: black !important;
            color: white !important;
            font-size: 14px !important;
            width: 100%;
        }
        
        th, td {
            background-color: black !important;
            color: white !important;
            border: 1px solid #444 !important;
            font-size: 14px !important;
            padding: 8px !important;
        }
        
        /* Title styling */
        .container-title {
            color: white;
            font-size: 20px;
            font-weight: bold;
            margin-bottom: 15px;
            text-align: center;
        }
        
        /* Legend styling */
        .apexcharts-legend-text {
            fill: white !important;
            font-size: 14px !important;
        }
        
        /* Error message styling */
        .error-message {
            color: red;
            font-weight: bold;
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
            database="db4idjmbjsqwkf",
            connect_timeout=50
        )
        cursor = conn.cursor()

        # Check for required columns
        table_name = 'patient'
        required_columns = ['patient_id', 'gender', 'patient_status', 'deleted_at', 'age_category', 'dob']
        available_columns = {col: column_exists(cursor, table_name, col) for col in required_columns}

        # Query total patients
        total_query = "SELECT COUNT(DISTINCT patient_id) as total FROM patient WHERE deleted_at IS NULL"
        try:
            total_df = pd.read_sql(total_query, conn)
            total_patients = int(total_df['total'].iloc[0]) if not total_df.empty else 0
        except Error as e:
            st.error(f"Total Patients query failed: {e}")
            total_patients = 0

        # Query gender distribution
        if available_columns['gender']:
            gender_query = """
                SELECT gender, COUNT(DISTINCT patient_id) as total
                FROM patient WHERE deleted_at IS NULL
                GROUP BY gender
            """
            try:
                gender_df = pd.read_sql(gender_query, conn)
            except Error as e:
                st.error(f"Gender query failed: {e}")
                gender_df = pd.DataFrame({'gender': ['No Data'], 'total': [0]})
        else:
            gender_df = pd.DataFrame({'gender': ['No Data'], 'total': [0]})
            st.warning("Gender column not found in patient table.")

        # Query patient_status distribution
        if available_columns['patient_status']:
            status_query = """
                SELECT patient_status, COUNT(DISTINCT patient_id) as total
                FROM patient WHERE deleted_at IS NULL
                GROUP BY patient_status
            """
            try:
                status_df = pd.read_sql(status_query, conn)
            except Error as e:
                st.error(f"Patient Status query failed: {e}")
                status_df = pd.DataFrame({'patient_status': ['No Data'], 'total': [0]})
        else:
            status_df = pd.DataFrame({'patient_status': ['No Data'], 'total': [0]})
            st.warning("Patient Status column not found in patient table.")

        # Query age category distribution
        if available_columns['age_category']:
            age_query = """
                SELECT age_category, COUNT(DISTINCT patient_id) as total
                FROM patient WHERE deleted_at IS NULL
                GROUP BY age_category
            """
            try:
                age_df = pd.read_sql(age_query, conn)
                if age_df.empty or age_df['age_category'].isna().all():
                    raise Error("Age category data is empty or all NULL")
            except Error as e:
                st.warning(f"Age Category query failed or empty: {e}. Falling back to default.")
                if available_columns['dob']:
                    age_query = """
                        SELECT 
                            CASE 
                                WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) < 20 THEN '<20 yrs'
                                WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) BETWEEN 20 AND 40 THEN '20-40 yrs'
                                WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) BETWEEN 41 AND 60 THEN '41-60 yrs'
                                ELSE '>60 yrs'
                            END as age_category,
                            COUNT(DISTINCT patient_id) as total
                        FROM patient WHERE deleted_at IS NULL 
                        GROUP BY age_category
                    """
                    try:
                        age_df = pd.read_sql(age_query, conn)
                    except Error as e:
                        st.error(f"DOB-based Age Category query failed: {e}")
                        age_df = pd.DataFrame({'age_category': ['No Data'], 'total': [0]})
                else:
                    age_df = pd.DataFrame({'age_category': ['No Data'], 'total': [0]})
                    st.warning("DOB column not found in patient table.")
        else:
            st.warning("Age Category column not found. Falling back to DOB.")
            if available_columns['dob']:
                age_query = """
                    SELECT 
                        CASE 
                            WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) < 20 THEN '<20 yrs'
                            WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) BETWEEN 20 AND 40 THEN '20-40 yrs'
                            WHEN TIMESTAMPDIFF(YEAR, dob, CURDATE()) BETWEEN 41 AND 60 THEN '41-60 yrs'
                            ELSE '>60 yrs'
                        END as age_category,
                        COUNT(DISTINCT patient_id) as total
                    FROM patient WHERE deleted_at IS NULL 
                    GROUP BY age_category
                """
                try:
                    age_df = pd.read_sql(age_query, conn)
                except Error as e:
                    st.error(f"DOB-based Age Category query failed: {e}")
                    age_df = pd.DataFrame({'age_category': ['No Data'], 'total': [0]})
            else:
                age_df = pd.DataFrame({'age_category': ['No Data'], 'total': [0]})
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
            'gender': pd.DataFrame({'gender': ['No Data'], 'total': [0]}),
            'status': pd.DataFrame({'patient_status': ['No Data'], 'total': [0]}),
            'age': pd.DataFrame({'age_category': ['No Data'], 'total': [0]})
        }

# Function to create donut chart with labels outside
def create_donut_chart(labels, values, title, total, chart_id):
    percentages = [(value / total * 100) if total > 0 else 0 for value in values]
    data_labels = [f"{label}\\n{value} ({percent:.1f}%)" for label, value, percent in zip(labels, values, percentages)]
    
    options = {
        "chart": {
            "id": chart_id,
            "type": "donut",
            "toolbar": {"show": False},
            "background": "black",
            "height": 400
        },
        "labels": labels,
        "series": values,
        "dataLabels": {
            "enabled": True,
            "style": {
                "fontSize": "14px",
                "colors": ["#fff"]
            },
            "formatter": f"function(val, opts) {{ return {data_labels}[opts.seriesIndex]; }}"
        },
        "legend": {
            "show": False
        },
        "colors": ['#3b82f6', '#10b981', '#f59e0b', '#ef4444'],
        "plotOptions": {
            "pie": {
                "donut": {
                    "size": "65%",
                    "labels": {
                        "show": True,
                        "total": {
                            "show": True,
                            "label": "Total",
                            "fontSize": "14px",
                            "color": "#fff"
                        }
                    }
                }
            }
        },
        "title": {
            "text": title,
            "align": "center",
            "style": {
                "fontSize": "18px",
                "color": "#fff"
            }
        }
    }
    return options, values

# Function to create bar chart with labels outside
def create_bar_chart(labels, values, title, total, chart_id):
    percentages = [(value / total * 100) if total > 0 else 0 for value in values]
    data_labels = [f"{value} ({percent:.1f}%)" for value, percent in zip(values, percentages)]
    
    options = {
        "chart": {
            "id": chart_id,
            "type": "bar",
            "toolbar": {"show": False},
            "background": "black",
            "height": 400
        },
        "xaxis": {
            "categories": labels,
            "labels": {
                "style": {
                    "fontSize": "14px",
                    "colors": ["#fff"]
                }
            },
            "title": {
                "text": "Status",
                "style": {
                    "fontSize": "14px",
                    "color": "#fff"
                }
            }
        },
        "yaxis": {
            "labels": {
                "style": {
                    "fontSize": "14px",
                    "colors": ["#fff"]
                }
            },
            "title": {
                "text": "Count",
                "style": {
                    "fontSize": "14px",
                    "color": "#fff"
                }
            }
        },
        "dataLabels": {
            "enabled": True,
            "style": {
                "fontSize": "14px",
                "colors": ["#fff"]
            },
            "position": "top",
            "formatter": f"function(val, opts) {{ return {data_labels}[opts.dataPointIndex]; }}"
        },
        "legend": {
            "show": False
        },
        "colors": ['#3b82f6'],
        "title": {
            "text": title,
            "align": "center",
            "style": {
                "fontSize": "18px",
                "color": "#fff"
            }
        }
    }
    series = [{"name": "Count", "data": values}]
    return options, series

# Helper function to create table with percentages
def create_table_data(df, label_column, total):
    if not df.empty and not df[label_column].eq('No Data').all():
        labels = df[label_column].fillna('Unknown').tolist()
        counts = df['total'].tolist()
        percentages = [(count / total * 100) if total > 0 else 0 for count in counts]
        table_data = [
            {"Label": label if label else "Unknown", "Count": count, "Percentage": f"{percent:.1f}%"}
            for label, count, percent in zip(labels, counts, percentages)
        ]
    else:
        table_data = [{"Label": "No Data", "Count": 0, "Percentage": "0.0%"}]
    return pd.DataFrame(table_data)

# Main app
st.title("Patient Distribution Dashboard")

# Fetch data
try:
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
            st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
            st.markdown('<div class="container-title">Total Patients</div>', unsafe_allow_html=True)
            series = [total_patients] if total_patients > 0 else [0]
            labels = ["Total Patients"] if total_patients > 0 else ["No Data"]
            options, series = create_donut_chart(labels, series, "", total_patients, "total_chart")
            st_apexcharts(options, series, 'donut', '100%')
            table_data = [{"Label": "Total Patients", "Count": total_patients, "Percentage": "100.0%"}] if total_patients > 0 else [{"Label": "No Data", "Count": 0, "Percentage": "0.0%"}]
            df_table = pd.DataFrame(table_data)
            st.dataframe(df_table, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Column 1 - Patients by Gender
    with col1:
        with st.container():
            st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
            st.markdown('<div class="container-title">Patients by Gender</div>', unsafe_allow_html=True)
            df_table = create_table_data(gender_df, 'gender', total_patients)
            options, series = create_donut_chart(df_table['Label'].tolist(), df_table['Count'].tolist(), "", total_patients, "gender_chart")
            st_apexcharts(options, series, 'donut', '100%')
            st.dataframe(df_table, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Column 2 - Patients by Status
    with col2:
        with st.container():
            st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
            st.markdown('<div class="container-title">Patients by Status</div>', unsafe_allow_html=True)
            df_table = create_table_data(status_df, 'patient_status', total_patients)
            options, series = create_bar_chart(df_table['Label'].tolist(), df_table['Count'].tolist(), "", total_patients, "status_chart")
            st_apexcharts(options, series, 'bar', '100%')
            st.dataframe(df_table, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # Column 2 - Patients by Age Category
    with col2:
        with st.container():
            st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
            st.markdown('<div class="container-title">Patients by Age Category</div>', unsafe_allow_html=True)
            df_table = create_table_data(age_df, 'age_category', total_patients)
            options, series = create_donut_chart(df_table['Label'].tolist(), df_table['Count'].tolist(), "", total_patients, "age_chart")
            st_apexcharts(options, series, 'donut', '100%')
            st.dataframe(df_table, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

except Exception as e:
    st.error(f"An error occurred while loading the dashboard: {str(e)}")
    st.markdown('<div class="error-message">Please check the database connection and try again.</div>', unsafe_allow_html=True)
