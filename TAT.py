import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import mysql.connector
from mysql.connector import Error

# Set page config for wide layout and dark theme
st.set_page_config(page_title="Total Patients Dashboard", layout="wide")

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

# Function to fetch patient count from MySQL
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_patient_count():
    try:
        conn = mysql.connector.connect(
            host="35.209.69.119",  # Replace with your MySQL host
            user="u0iky3cyvfnfy",        # Replace with your MySQL user
            password="Thisisme@2026",# Replace with your MySQL password
            database="db4idjmbjsqwkf" # Replace with your database name
        )
        query = "SELECT COUNT(DISTINCT patient_id) as total_patients FROM patient WHERE deleted_at IS NULL"
        df = pd.read_sql(query, conn)
        conn.close()
        total_patients = int(df['total_patients'].iloc[0])
        return total_patients
    except Error as e:
        st.error(f"Database error: {e}")
        return 0

# Main app
st.title("Total Patients Dashboard")

# Fetch data
total_patients = fetch_patient_count()

# Prepare data for chart and table
series = [total_patients] if total_patients > 0 else [0]
labels = ["Total Patients"] if total_patients > 0 else ["No Data"]
table_data = [{"label": "Total Patients", "count": total_patients}] if total_patients > 0 else [{"label": "No Data", "count": 0}]

# Create donut chart with Plotly
fig = go.Figure(data=[
    go.Pie(
        labels=labels,
        values=series,
        hole=0.4,  # Create donut shape
        marker=dict(colors=['#3b82f6'], line=dict(color='#27272a', width=2)),
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
    legend=dict(
        font=dict(color='#9ca3af', weight='bold'),
        orientation='h',
        yanchor='bottom',
        y=-0.2,
        xanchor='center',
        x=0.5
    ),
    margin=dict(t=20, b=80, l=20, r=20)
)

# Display chart
with st.container():
    st.subheader("Total Patients Donut Chart")
    st.plotly_chart(fig, use_container_width=True)

# Display table
with st.container():
    st.subheader("Patient Statistics")
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
