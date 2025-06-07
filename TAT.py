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
            padding: 20px;
            margin-bottom: 20px;
            height: 650px;
            display: flex;
            flex-direction: column;
        }
        
        /* Chart styling */
        .stPlotlyChart {
            height: 400px !important;
        }
        
        /* Table styling */
        .stDataFrame, .stDataFrame table {
            background-color: black !important;
            color: white !important;
            font-size: 14px !important;
        }
        
        th, td {
            background-color: black !important;
            color: white !important;
            border: 1px solid #444 !important;
            font-size: 14px !important;
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
        .legend text {
            font-size: 14px !important;
        }
    </style>
""", unsafe_allow_html=True)

# [Keep all the existing functions: column_exists, fetch_patient_data - unchanged from your original code]

# Function to create donut chart with larger size and external labels
def create_donut_chart(labels, values, title, total):
    percentages = [(value / total * 100) if total > 0 else 0 for value in values]
    text_labels = [f"{label}<br>{value} ({percent:.1f}%)" for label, value, percent in zip(labels, values, percentages)]
    
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
            showlegend=True,
            textposition='outside'
        )
    ])
    fig.update_layout(
        height=400,
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white', size=14),
        title=dict(text=title, font=dict(color='white', size=18), x=0.5, xanchor='center'),
        legend=dict(
            font=dict(color='white', size=14),
            orientation='h',
            yanchor='bottom',
            y=-0.3,
            xanchor='center',
            x=0.5
        ),
        margin=dict(t=60, b=100, l=40, r=40)
    )
    return fig

# Function to create bar chart with larger size
def create_bar_chart(labels, values, title, total):
    percentages = [(value / total * 100) if total > 0 else 0 for value in values]
    text_labels = [f"{value} ({percent:.1f}%)" for value, percent in zip(values, percentages)]
    
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
            textfont=dict(size=14),
            hoverinfo='x+y+text'
        )
    ])
    fig.update_layout(
        height=400,
        paper_bgcolor='black',
        plot_bgcolor='black',
        font=dict(color='white', size=14),
        title=dict(text=title, font=dict(color='white', size=18), x=0.5, xanchor='center'),
        xaxis=dict(
            title=None,
            tickfont=dict(color='white', size=14)
        ),
        yaxis=dict(
            title=None,
            tickfont=dict(color='white', size=14),
            showgrid=False
        ),
        margin=dict(t=60, b=100, l=40, r=40)
    )
    return fig

# Helper function to create table with percentages
def create_table_data(df, label_column, total):
    if not df.empty and not df[label_column].eq('No Data').all():
        labels = df[label_column].fillna('Unknown').tolist()
        counts = df['count'].tolist()
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
        
        # Chart
        series = [total_patients] if total_patients > 0 else [0]
        labels = ["Total Patients"] if total_patients > 0 else ["No Data"]
        fig = create_donut_chart(labels, series, "", total_patients)
        st.plotly_chart(fig, use_container_width=True)
        
        # Table
        table_data = [{"Label": "Total Patients", "Count": total_patients, "Percentage": "100.0%"}] if total_patients > 0 else [{"Label": "No Data", "Count": 0, "Percentage": "0.0%"}]
        df_table = pd.DataFrame(table_data)
        st.dataframe(
            df_table,
            use_container_width=True,
            column_config={
                "Label": st.column_config.TextColumn("Label", width="medium"),
                "Count": st.column_config.NumberColumn("Count", format="%d"),
                "Percentage": st.column_config.TextColumn("Percentage")
            },
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# Column 1 - Patients by Gender
with col1:
    with st.container():
        st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
        st.markdown('<div class="container-title">Patients by Gender</div>', unsafe_allow_html=True)
        
        # Chart and Table
        df_table = create_table_data(gender_df, 'gender', total_patients)
        fig = create_donut_chart(df_table['Label'].tolist(), df_table['Count'].tolist(), "", total_patients)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            df_table,
            use_container_width=True,
            column_config={
                "Label": st.column_config.TextColumn("Gender", width="medium"),
                "Count": st.column_config.NumberColumn("Count", format="%d"),
                "Percentage": st.column_config.TextColumn("Percentage")
            },
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# Column 2 - Patients by Status
with col2:
    with st.container():
        st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
        st.markdown('<div class="container-title">Patients by Status</div>', unsafe_allow_html=True)
        
        # Chart and Table
        df_table = create_table_data(status_df, 'patient_status', total_patients)
        fig = create_bar_chart(df_table['Label'].tolist(), df_table['Count'].tolist(), "", total_patients)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            df_table,
            use_container_width=True,
            column_config={
                "Label": st.column_config.TextColumn("Status", width="medium"),
                "Count": st.column_config.NumberColumn("Count", format="%d"),
                "Percentage": st.column_config.TextColumn("Percentage")
            },
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)

# Column 2 - Patients by Age Category
with col2:
    with st.container():
        st.markdown('<div class="dashboard-container">', unsafe_allow_html=True)
        st.markdown('<div class="container-title">Patients by Age Category</div>', unsafe_allow_html=True)
        
        # Chart and Table
        df_table = create_table_data(age_df, 'age_category', total_patients)
        fig = create_donut_chart(df_table['Label'].tolist(), df_table['Count'].tolist(), "", total_patients)
        st.plotly_chart(fig, use_container_width=True)
        
        st.dataframe(
            df_table,
            use_container_width=True,
            column_config={
                "Label": st.column_config.TextColumn("Age Category", width="medium"),
                "Count": st.column_config.NumberColumn("Count", format="%d"),
                "Percentage": st.column_config.TextColumn("Percentage")
            },
            hide_index=True
        )
        st.markdown('</div>', unsafe_allow_html=True)
