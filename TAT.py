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
        
        /* Container styling */
        .dashboard-container {
            background-color: black;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
            height: 600px;
        }
        
        /* Chart styling */
        .stPlotlyChart {
            height: 350px !important;
        }
        
        /* Table styling */
        .stDataFrame, .stDataFrame table {
            background-color: black !important;
            color: white !important;
        }
        
        th, td {
            background-color: black !important;
            color: white !important;
            border: 1px solid #444 !important;
        }
        
        /* Title styling */
        .container-title {
            color: white;
            font-size: 18px;
            font-weight: bold;
            margin-bottom: 15px;
        }
    </style>
""", unsafe_allow_html=True)

# [Keep all the existing functions: column_exists, fetch_patient_data, 
# create_donut_chart, create_bar_chart, create_table - unchanged from your original code]

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

# Column 1 - Top Container (Total Patients)
with col1:
    with st.container():
        st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
        st.markdown('<div class="container-title">Total Patients</div>', unsafe_allow_html=True)
        
        # Chart
        series = [total_patients] if total_patients > 0 else [0]
        labels = ["Total Patients"] if total_patients > 0 else ["No Data"]
        fig = create_donut_chart(labels, series, "")
        st.plotly_chart(fig, use_container_width=True)
        
        # Table
        table_data = [{"Label": "Total Patients", "Count": total_patients, "Percentage": "100%"}] if total_patients > 0 else [{"Label": "No Data", "Count": 0, "Percentage": "0%"}]
        df_table = pd.DataFrame(table_data)
        st.dataframe(
            df_table,
            use_container_width=True,
            column_config={
                "Label": st.column_config.TextColumn("Label"),
                "Count": st.column_config.NumberColumn("Count", format="%d"),
                "Percentage": st.column_config.TextColumn("Percentage")
            },
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# Column 1 - Bottom Container (Patients by Gender)
with col1:
    with st.container():
        st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
        st.markdown('<div class="container-title">Patients by Gender</div>', unsafe_allow_html=True)
        
        # Chart
        if not gender_df.empty and not gender_df['gender'].eq('No Data').all():
            labels = gender_df['gender'].fillna('Unknown').tolist()
            values = gender_df['count'].tolist()
        else:
            labels = ["No Data"]
            values = [0]
        
        fig = create_donut_chart(labels, values, "")
        st.plotly_chart(fig, use_container_width=True)
        
        # Table
        if not gender_df.empty and not gender_df['gender'].eq('No Data').all():
            table_df = gender_df.copy()
            table_df.columns = ['Label', 'Count']
            table_df = create_table(table_df, total_patients)
        else:
            table_df = pd.DataFrame({'Label': ['No Data'], 'Count': [0], 'percentage': ['0%']})
        
        st.dataframe(
            table_df,
            use_container_width=True,
            column_config={
                "Label": st.column_config.TextColumn("Gender"),
                "Count": st.column_config.NumberColumn("Count", format="%d"),
                "percentage": st.column_config.TextColumn("Percentage")
            },
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# Column 2 - Top Container (Patients by Status)
with col2:
    with st.container():
        st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
        st.markdown('<div class="container-title">Patients by Status</div>', unsafe_allow_html=True)
        
        # Chart
        if not status_df.empty and not status_df['patient_status'].eq('No Data').all():
            labels = status_df['patient_status'].fillna('Unknown').tolist()
            values = status_df['count'].tolist()
        else:
            labels = ["No Data"]
            values = [0]
        
        fig = create_bar_chart(labels, values, "")
        st.plotly_chart(fig, use_container_width=True)
        
        # Table
        if not status_df.empty and not status_df['patient_status'].eq('No Data').all():
            table_df = status_df.copy()
            table_df.columns = ['Label', 'Count']
            table_df = create_table(table_df, total_patients)
        else:
            table_df = pd.DataFrame({'Label': ['No Data'], 'Count': [0], 'percentage': ['0%']})
        
        st.dataframe(
            table_df,
            use_container_width=True,
            column_config={
                "Label": st.column_config.TextColumn("Status"),
                "Count": st.column_config.NumberColumn("Count", format="%d"),
                "percentage": st.column_config.TextColumn("Percentage")
            },
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# Column 2 - Bottom Container (Patients by Age Category)
with col2:
    with st.container():
        st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
        st.markdown('<div class="container-title">Patients by Age Category</div>', unsafe_allow_html=True)
        
        # Chart
        if not age_df.empty and not age_df['age_category'].eq('No Data').all():
            labels = age_df['age_category'].fillna('Unknown').tolist()
            values = age_df['count'].tolist()
        else:
            labels = ["No Data"]
            values = [0]
        
        fig = create_donut_chart(labels, values, "")
        st.plotly_chart(fig, use_container_width=True)
        
        # Table
        if not age_df.empty and not age_df['age_category'].eq('No Data').all():
            table_df = age_df.copy()
            table_df.columns = ['Label', 'Count']
            table_df = create_table(table_df, total_patients)
        else:
            table_df = pd.DataFrame({'Label': ['No Data'], 'Count': [0], 'percentage': ['0%']})
        
        st.dataframe(
            table_df,
            use_container_width=True,
            column_config={
                "Label": st.column_config.TextColumn("Age Category"),
                "Count": st.column_config.NumberColumn("Count", format="%d"),
                "percentage": st.column_config.TextColumn("Percentage")
            },
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
