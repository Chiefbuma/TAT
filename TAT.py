import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
import warnings
import os
from datetime import datetime

# Suppress warnings
warnings.filterwarnings('ignore', category=UserWarning, message='.*tight_layout.*')
warnings.filterwarnings('ignore', category=DeprecationWarning, message='.*use_column_width.*')

# Set page config
st.set_page_config(page_title="TAT Analysis Dashboard", layout="wide")

# Apply CSS styling
st.markdown("""
    <style>
        body {
            background-color: black;
            color: white;
        }
        .stApp {
            background-color: black;
            color: white;
        }
        .stSelectbox, .stSelectbox div, .stSelectbox label, .stSelectbox select {
            background-color: #000000 !important;
            color: white !important;
            border: 1px solid white !important;
        }
        .stDateInput, .stDateInput div, .stDateInput label, .stDateInput input {
            background-color: #000000 !important;
            color: white !important;
            border: 1px solid white !important;
        }
        .stButton button {
            background-color: #333333;
            color: white;
            border: 1px solid white;
        }
        .stDataFrame {
            color: white;
            background-color: #333333;
        }
        table, th, td {
            border: 1px solid white;
            border-collapse: collapse;
            background-color: #333333;
            color: white;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid white !important;
            border-radius: 15px !important;
            padding: 10px;
            background-color: #1a1a1a;
        }
        .transparent-container div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: rgba(255, 255, 255, 0.1) !important;
            border: 1px solid white !important;
            border-radius: 15px !important;
        }
    </style>
""", unsafe_allow_html=True)

# Function to classify shifts
def classify_shift(time):
    if pd.isna(time):
        return None
    if time.hour >= 20 or time.hour < 7:
        return 'Night Shift'
    elif 7 <= time.hour < 10:
        return 'Morning'
    elif 10 <= time.hour < 13:
        return 'Mid Morning'
    elif 13 <= time.hour < 16:
        return 'Afternoon'
    elif 16 <= time.hour < 20:
        return 'Evening'
    return None

# Modified data processing function
@st.cache_data
def fetch_and_process_data(file_input):
    # Columns to import
    columns_to_import = [
        'UHID', 'PatientName', 'Department', 'FacilityName',
        'ConsultationBillingTime', 'Pharmacy_Billing_Time',
        'Pharmacy_Dispensing_Time', 'ConsultationStart_Date_Time',
        'Visit_Signed_Time', 'Sample_Collection__Acknowledge_Date___Time',
        'ID_Report_Save_Date_and_Time', 'Service_Bill_Date_Time',
        'Procedure_Completion_Date_'
    ]

    # Read CSV from file object or path
    try:
        if isinstance(file_input, str):
            # Input is a file path
            if not os.path.exists(file_input):
                st.error(f"File does not exist at path: {file_input}")
                return None, None, None, None, None
            if os.path.getsize(file_input) == 0:
                st.error(f"File at {file_input} is empty.")
                return None, None, None, None, None
            TAT_df = pd.read_csv(
                file_input,
                encoding='utf-8',
                usecols=[col for col in columns_to_import if col in pd.read_csv(file_input, nrows=1).columns],
                parse_dates=[
                    'ConsultationBillingTime', 'Pharmacy_Billing_Time',
                    'Pharmacy_Dispensing_Time', 'ConsultationStart_Date_Time',
                    'Visit_Signed_Time', 'Sample_Collection__Acknowledge_Date___Time',
                    'ID_Report_Save_Date_and_Time', 'Service_Bill_Date_Time',
                    'Procedure_Completion_Date_'
                ],
                dayfirst=True,
                dtype={'UHID': str},
                low_memory=False
            )
        else:
            # Input is a file object from uploader
            TAT_df = pd.read_csv(
                file_input,
                encoding='utf-8',
                usecols=[col for col in columns_to_import if col in pd.read_csv(file_input, nrows=1).columns],
                parse_dates=[
                    'ConsultationBillingTime', 'Pharmacy_Billing_Time',
                    'Pharmacy_Dispensing_Time', 'ConsultationStart_Date_Time',
                    'Visit_Signed_Time', 'Sample_Collection__Acknowledge_Date___Time',
                    'ID_Report_Save_Date_and_Time', 'Service_Bill_Date_Time',
                    'Procedure_Completion_Date_'
                ],
                dayfirst=True,
                dtype={'UHID': str},
                low_memory=False
            )
        if TAT_df.empty:
            st.error("CSV file loaded but contains no data.")
            return None, None, None, None, None
    except (UnicodeDecodeError, ValueError) as e:
        st.error(f"Error reading CSV: {e}. Please check file format or content.")
        return None, None, None, None, None
    except FileNotFoundError:
        st.error(f"CSV file not found at specified path.")
        return None, None, None, None, None
    except Exception as e:
        st.error(f"Error processing CSV: {e}")
        return None, None, None, None, None

    # Verify datetime parsing
    st.write("### Debug: Datetime Columns Sample")
    datetime_columns = [
        'ConsultationBillingTime', 'Pharmacy_Billing_Time',
        'Pharmacy_Dispensing_Time', 'ConsultationStart_Date_Time',
        'Visit_Signed_Time', 'Sample_Collection__Acknowledge_Date___Time',
        'ID_Report_Save_Date_and_Time', 'Service_Bill_Date_Time',
        'Procedure_Completion_Date_'
    ]
    for col in datetime_columns:
        if col in TAT_df.columns:
            st.write(f"**{col} dtype:**", str(TAT_df[col].dtype))
            st.write(TAT_df[col].head())
        else:
            st.write(f"**{col}** not found in CSV.")

    # Ensure required columns exist
    required_cols = ['UHID', 'PatientName', 'Department', 'FacilityName']
    missing_cols = [col for col in required_cols if col not in TAT_df.columns]
    if missing_cols:
        st.error(f"Missing required columns in CSV: {missing_cols}")
        return None, None, None, None, None

    # Filter out invalid data
    filtered_TAT_df = TAT_df.dropna(subset=['UHID'])
    filtered_TAT_df = filtered_TAT_df[filtered_TAT_df['FacilityName'] != "Bliss Medical Centre HomeCare"]

    # Overall TAT Calculation
    Consultation_df = filtered_TAT_df[filtered_TAT_df['Department'] == 'GENERAL OPD'].drop(
        columns=['Pharmacy_Billing_Time'] if 'Pharmacy_Billing_Time' in filtered_TAT_df.columns else []).copy()
    Pharmacy_df = filtered_TAT_df[filtered_TAT_df['Department'] == 'Pharmacy'].drop(
        columns=['ConsultationBillingTime'] if 'ConsultationBillingTime' in filtered_TAT_df.columns else []).copy()

    Consultation_df['date'] = Consultation_df['ConsultationBillingTime'].dt.date
    Pharmacy_df['date'] = Pharmacy_df['Pharmacy_Billing_Time'].dt.date

    TAT_pharmacy_df = Pharmacy_df.groupby(['date', 'UHID', 'PatientName', 'FacilityName']).agg({
        'Pharmacy_Billing_Time': 'min',
        'Department': 'first'
    }).reset_index()

    TAT_consultation_df = Consultation_df.groupby(['date', 'UHID', 'PatientName', 'FacilityName']).agg({
        'ConsultationBillingTime': 'min',
        'Department': 'first'
    }).reset_index()

    for df in [TAT_pharmacy_df, TAT_consultation_df]:
        df['Unique'] = df['UHID'].astype(str) + "_" + \
                       df['PatientName'].astype(str) + "_" + \
                       df['FacilityName'].astype(str) + "_" + \
                       df['date'].astype(str)

    merged_df = TAT_consultation_df.merge(
        TAT_pharmacy_df[['Unique', 'Pharmacy_Billing_Time']],
        on='Unique',
        how='left'
    )

    filtered_merged_df = merged_df[merged_df['Pharmacy_Billing_Time'].notna()].copy()
    filtered_merged_df['TAT'] = (filtered_merged_df['Pharmacy_Billing_Time'] - 
                                filtered_merged_df['ConsultationBillingTime']).dt.total_seconds() / 60
    filtered_merged_df = filtered_merged_df[filtered_merged_df['TAT'] >= 0].copy()
    filtered_merged_df['Time_out'] = filtered_merged_df['Pharmacy_Billing_Time']
    filtered_merged_df['Department'] = 'Overall TAT'

    overall_df = filtered_merged_df[
        (filtered_merged_df['Pharmacy_Billing_Time'].dt.time >= pd.to_datetime("07:00:00").time()) &
        (filtered_merged_df['Pharmacy_Billing_Time'].dt.time <= pd.to_datetime("19:00:00").time())
    ].copy()

    if overall_df.empty:
        st.warning("No overall TAT data available after filtering for 07:00–19:00.")

    overall_df['Minutes_Since_7AM'] = (
        (overall_df['Pharmacy_Billing_Time'].dt.hour - 7) * 60 +
        overall_df['Pharmacy_Billing_Time'].dt.minute
    )
    overall_df['Hour'] = overall_df['Pharmacy_Billing_Time'].dt.hour
    overall_df['Shift'] = overall_df['Pharmacy_Billing_Time'].apply(classify_shift)
    overall_df['Year'] = overall_df['Pharmacy_Billing_Time'].dt.year
    overall_df['Month'] = overall_df['Pharmacy_Billing_Time'].dt.month
    overall_df['Day'] = overall_df['Pharmacy_Billing_Time'].dt.day
    overall_df['Date'] = pd.to_datetime(overall_df[['Year', 'Month', 'Day']])
    overall_df['Time'] = overall_df['Pharmacy_Billing_Time'].dt.time

    # Departmental TAT Calculation
    allowed_departments = ['DENTAL', 'Laboratory', 'Nursing', 'OPTICAL', 'Pharmacy', 'GENERAL OPD']
    dept_df = TAT_df[TAT_df['Department'].isin(allowed_departments)].copy()
    dept_df = dept_df[dept_df['FacilityName'] != "Bliss Medical Centre HomeCare"]

    dept_df = dept_df.rename(columns={
        'Procedure_Completion_Date_': 'Procedure_Completion_Date',
        'Sample_Collection__Acknowledge_Date___Time': 'Sample_Collection_Acknowledge_Date_Time'
    })

    dept_time_mapping = {
        'DENTAL': {'Time_in': 'ConsultationStart_Date_Time', 'Time_out': 'Visit_Signed_Time'},
        'Laboratory': {'Time_in': 'Sample_Collection_Acknowledge_Date_Time', 'Time_out': 'ID_Report_Save_Date_and_Time'},
        'Nursing': {'Time_in': 'Service_Bill_Date_Time', 'Time_out': 'Procedure_Completion_Date'},
        'OPTICAL': {'Time_in': 'ConsultationStart_Date_Time', 'Time_out': 'Visit_Signed_Time'},
        'Pharmacy': {'Time_in': 'Pharmacy_Billing_Time', 'Time_out': 'Pharmacy_Dispensing_Time'},
        'GENERAL OPD': {'Time_in': 'ConsultationStart_Date_Time', 'Time_out': 'Visit_Signed_Time'}
    }

    dept_dfs = []
    for dept, times in dept_time_mapping.items():
        time_in_col = times['Time_in']
        time_out_col = times['Time_out']
        if time_in_col not in dept_df.columns or time_out_col not in dept_df.columns:
            st.warning(f"Skipping {dept}: Missing required time columns ({time_in_col}, {time_out_col})")
            continue
        temp_df = dept_df[dept_df['Department'] == dept].copy()
        if temp_df.empty:
            st.warning(f"No records for department: {dept}")
            continue
        keep_cols = ['Department', 'FacilityName', time_in_col, time_out_col]
        temp_df = temp_df[keep_cols].copy()
        temp_df = temp_df.rename(columns={time_in_col: 'Time_in', time_out_col: 'Time_out'})
        temp_df = temp_df[temp_df['Time_in'].notna() & temp_df['Time_out'].notna()]
        if temp_df['Time_in'].dtype != 'datetime64[ns]' or temp_df['Time_out'].dtype != 'datetime64[ns]':
            st.error(f"Error in {dept}: Time_in or Time_out is not datetime.")
            continue
        temp_df['TAT'] = (temp_df['Time_out'] - temp_df['Time_in']).dt.total_seconds() / 60
        temp_df = temp_df[temp_df['TAT'] >= 0].copy()
        temp_df['date'] = temp_df['Time_out'].dt.date
        temp_df = temp_df[['date', 'FacilityName', 'Department', 'Time_in', 'Time_out', 'TAT']]
        st.write(f"Records for {dept}: {len(temp_df)}")
        dept_dfs.append(temp_df)

    if dept_dfs:
        dept_final_df = pd.concat(dept_dfs, ignore_index=True)
        st.write(f"Total departmental TAT records: {len(dept_final_df)}")
        dept_final_df = dept_final_df[
            (dept_final_df['Time_out'].dt.time >= pd.to_datetime("07:00:00").time()) &
            (dept_final_df['Time_out'].dt.time <= pd.to_datetime("19:00:00").time())
        ].copy()
        dept_final_df['Minutes_Since_7AM'] = (
            (dept_final_df['Time_out'].dt.hour - 7) * 60 +
            dept_final_df['Time_out'].dt.minute
        )
        dept_final_df['Shift'] = dept_final_df['Time_out'].apply(classify_shift)
        dept_final_df['Year'] = dept_final_df['Time_out'].dt.year
        dept_final_df['Month'] = dept_final_df['Time_out'].dt.month
        dept_final_df['Day'] = dept_final_df['Time_out'].dt.day
        dept_final_df['Date'] = pd.to_datetime(dept_final_df[['Year', 'Month', 'Day']])
        dept_final_df['Time'] = dept_final_df['Time_out'].dt.time
        dept_final_df['Hour'] = dept_final_df['Time_out'].dt.hour
    else:
        dept_final_df = pd.DataFrame()
        st.warning("No departmental TAT data available.")

    if not overall_df.empty and not dept_final_df.empty:
        final_df = pd.concat([overall_df, dept_final_df], ignore_index=True)
    elif not overall_df.empty:
        final_df = overall_df
    elif not dept_final_df.empty:
        final_df = dept_final_df
    else:
        st.error("No data available after processing.")
        return None, None, None, None, None

    filtered_merged_df['time'] = filtered_merged_df['Pharmacy_Billing_Time'].dt.time
    filtered_merged_df['Shift'] = filtered_merged_df['Pharmacy_Billing_Time'].apply(classify_shift)

    grouped_df = filtered_merged_df.groupby(['date', 'FacilityName', 'Shift']).agg(
        Unique_UHID_Count=('UHID', 'nunique'),
        Average_TAT=('TAT', 'mean')
    ).reset_index()

    patient_df = filtered_merged_df.groupby(['date', 'PatientName', 'FacilityName', 'ConsultationBillingTime', 'Pharmacy_Billing_Time']).agg(
        Average_TAT=('TAT', 'mean')
    ).reset_index()
    patient_df['Average_TAT'] += 20

    grouped_All = filtered_merged_df.groupby(['date', 'FacilityName']).agg(
        Average_TAT=('TAT', 'mean')
    ).reset_index()
    grouped_All['Average_TAT'] += 20

    pivoted_df = grouped_df.pivot_table(
        index=['FacilityName', 'date'],
        columns='Shift',
        values='Average_TAT',
        aggfunc='mean'
    )
    pivoted_df['Day Avg'] = pivoted_df.mean(axis=1)
    pivoted_df = pivoted_df.applymap(
        lambda x: f"{int(x // 60)} hr {int(x % 60)} min" if pd.notnull(x) else "")
    pivoted_df = pivoted_df.reset_index()
    pivoted_df.columns.name = None
    preferred_order = ["FacilityName", "date", "Morning", "Mid Morning", "Afternoon", "Evening", "Night Shift", "Day Avg"]
    existing_columns = [col for col in preferred_order if col in pivoted_df.columns]
    pivoted_df = pivoted_df[existing_columns]

    return final_df, patient_df, grouped_All, pivoted_df, dept_final_df

# Plotting functions (unchanged)
def plot_tat_trend(df, start_date, end_date, facility):
    filtered_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
    if filtered_df.empty:
        st.warning(f"No data available for the selected date range: {start_date.date()} to {end_date.date()}.")
        earliest_date = df['Date'].min()
        latest_date = df['Date'].max()
        st.info(f"Falling back to full date range: {earliest_date.date()} to {latest_date.date()}")
        filtered_df = df[(df['Date'] >= earliest_date) & (df['Date'] <= latest_date)]
        start_date, end_date = earliest_date, latest_date
    if filtered_df.empty:
        st.error("No data available.")
        return None, None, None, None, None, None
    if facility != "All Facilities":
        filtered_df = filtered_df[filtered_df['FacilityName'] == facility]
        if filtered_df.empty:
            st.error(f"No data for facility: {facility}")
            return None, None, None, None, None, None
    filtered_df = filtered_df[filtered_df['Department'] == 'Overall TAT']
    if filtered_df.empty:
        st.error("No Overall TAT data available.")
        return None, None, None, None, None, None
    hourly_stats = filtered_df.groupby('Hour').agg({'TAT': 'mean', 'Unique': 'nunique'}).reindex(range(7, 20), fill_value=0)
    hourly_stats['TAT'] = hourly_stats['TAT'].round(0)
    hours_with_footfalls = hourly_stats[hourly_stats['Unique'] > 0].index
    if len(hours_with_footfalls) == 0:
        st.error("No footfalls recorded.")
        return None, None, None, None, None, None
    start_hour = max(hours_with_footfalls.min(), 7)
    end_hour = min(hours_with_footfalls.max(), 19)
    start_minute = (start_hour - 7) * 60
    end_minute = (end_hour - 7 + 1) * 60
    fig = plt.figure(figsize=(14, 4), facecolor='black')
    ax1 = fig.add_subplot(111)
    ax1.set_facecolor('black')
    minutes = filtered_df['Minutes_Since_7AM']
    tat = filtered_df['TAT']
    all_minutes = np.arange(0, 721)
    tat_full = np.full_like(all_minutes, np.nan, dtype=float)
    minute_groups = filtered_df.groupby('Minutes_Since_7AM')['TAT'].mean()
    for min_val, tat_val in minute_groups.items():
        if 0 <= min_val < 721:
            tat_full[int(min_val)] = tat_val
    tat_series = pd.Series(tat_full)
    tat_interpolated = tat_series.interpolate(method='linear')
    label = 'Overall TAT (All Facilities)' if facility == "All Facilities" else f'{facility} TAT'
    ax1.plot(all_minutes, tat_interpolated, linewidth=2, label=label, color='cyan')
    ax1.set_xlabel('Time of Day', fontsize=12, color='white')
    ax1.set_ylabel('Average TAT (Minutes)', fontsize=12, color='cyan')
    ax1.tick_params(axis='y', labelcolor='cyan')
    ax1.tick_params(axis='x', labelcolor='white')
    title = f'Overall TAT Trend - All Facilities - {start_date.date()} to {end_date.date()}' if facility == "All Facilities" else f'TAT Trend - {facility} - {start_date.date()} to {end_date.date()}'
    ax1.set_title(title, fontsize=14, color='white')
    ax1.set_xticks(np.arange(0, 721, 60))
    ax1.set_xticklabels([f'{h:02d}:00' for h in range(7, 20)], rotation=45)
    ax1.grid(True, alpha=0.3, color='gray')
    ax1.legend(loc='upper left', labelcolor='white')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor='black')
    buf.seek(0)
    plot_bytes = buf.getvalue()
    plt.close()
    hours = [f"{h:02d}:00" for h in range(7, 20)]
    tat_row = hourly_stats['TAT'].values
    footfall_row = hourly_stats['Unique'].values
    hourly_stats_df = pd.DataFrame({
        'Metric': ['Avg TAT (min)', 'Footfalls'],
        **{hour: [tat_row[i], footfall_row[i]] for i, hour in enumerate(hours)}
    })
    stats_df = filtered_df.groupby(['FacilityName', 'Hour']).agg({
        'TAT': 'mean',
        'Unique': 'nunique'
    }).reset_index()
    stats_df['TAT'] = stats_df['TAT'].round(0)
    facilities = filtered_df['FacilityName'].unique()
    all_hours = range(7, 20)
    all_combinations = pd.MultiIndex.from_product([facilities, all_hours], names=['FacilityName', 'Hour'])
    all_combinations_df = pd.DataFrame(index=all_combinations).reset_index()
    stats_df = all_combinations_df.merge(stats_df, on=['FacilityName', 'Hour'], how='left')
    stats_df['TAT'] = stats_df['TAT'].fillna(0)
    stats_df['Unique'] = stats_df['Unique'].fillna(0)
    stats_df['Hours'] = stats_df['Hour'].apply(lambda x: f"{x % 12 if x % 12 != 0 else 12}{'am' if x < 12 else 'pm'}")
    csv_data = stats_df[['FacilityName', 'Hours', 'TAT', 'Unique']].copy()
    csv_data.rename(columns={'Unique': 'Footfalls'}, inplace=True)
    return fig, csv_data, plot_bytes, start_date, end_date, hourly_stats_df

def plot_departmental_tat(df, start_date, end_date, facility):
    filtered_df = df[(df['Date'] >= start_date) & (df['Date'] <= end_date)]
    if filtered_df.empty:
        st.warning(f"No departmental data for {start_date.date()} to {end_date.date()}.")
        return None, None
    if facility != "All Facilities":
        filtered_df = filtered_df[filtered_df['FacilityName'] == facility]
        if filtered_df.empty:
            st.warning(f"No data for facility: {facility}")
            return None, None
    dept_avg_tat = filtered_df.groupby('Department')['TAT'].mean().reset_index()
    if dept_avg_tat.empty:
        st.warning("No departmental TAT data to plot.")
        return None, None
    fig = plt.figure(figsize=(10, 6), facecolor='black')
    ax = fig.add_subplot(111)
    ax.set_facecolor('black')
    bars = ax.bar(dept_avg_tat['Department'], dept_avg_tat['TAT'], color='cyan', edgecolor='white')
    title = f'Departmental Average TAT - All Facilities - {start_date.date()} to {end_date.date()}' if facility == "All Facilities" else f'Departmental Average TAT - {facility} - {start_date.date()} to {end_date.date()}'
    ax.set_title(title, fontsize=14, color='white')
    ax.set_xlabel('Department', fontsize=12, color='white')
    ax.set_ylabel('Average TAT (Minutes)', fontsize=12, color='cyan')
    ax.tick_params(axis='x', labelcolor='white', rotation=45)
    ax.tick_params(axis='y', labelcolor='cyan')
    ax.grid(True, axis='y', alpha=0.3, color='gray')
    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor='black', bbox_inches='tight')
    buf.seek(0)
    plot_bytes = buf.getvalue()
    plt.close()
    return fig, plot_bytes

# Streamlit app
st.title("Bliss Healthcare TAT Analysis Dashboard")
st.markdown("Select the date range and facility to analyze Turnaround Time (TAT) trends between 07:00 and 19:00.")

# File input section
st.header('Turn Around Time (TAT) 🔖')
with st.container():
    st.write("Username: 10443")
    st.write("Password: 123")
    input_method = st.radio("Select input method:", ("Upload CSV", "Use File Path"))
    
    if input_method == "Upload CSV":
        uploaded_file = st.file_uploader("Choose a CSV file", type="csv")
        file_input = uploaded_file
    else:
        default_path = "/mnt/e/Uploads/Streamlit/Allmerged.csv"
        file_path = st.text_input("Enter CSV file path:", value=default_path)
        file_input = file_path
    
    st.markdown(
        "[Click here to Download TAT Dump](https://app.blissmedicalcentre.com/dashboard/DashBoard.aspx?name=ConsolidatedTATReportNew)"
    )

# Load data if input is provided
if file_input is not None:
    final_df, patient_df, grouped_All, pivoted_df, dept_final_df = fetch_and_process_data(file_input)
    
    if final_df is not None:
        earliest_date = final_df['Date'].min()
        latest_date = final_df['Date'].max()
        
        if earliest_date is None or latest_date is None:
            st.error("No valid dates available in the data.")
        else:
            col1, col2, col3 = st.columns([2, 2, 2])
            with col1:
                start_date = st.date_input(
                    "Start Date",
                    value=earliest_date,
                    min_value=earliest_date,
                    max_value=latest_date,
                    format="YYYY-MM-DD"
                )
            with col2:
                end_date = st.date_input(
                    "End Date",
                    value=latest_date,
                    min_value=earliest_date,
                    max_value=latest_date,
                    format="YYYY-MM-DD"
                )
            with col3:
                facility_options = ['All Facilities'] + sorted(final_df['FacilityName'].unique().tolist())
                facility = st.selectbox("Facility", options=facility_options, index=0)
            
            start_date = pd.to_datetime(start_date)
            end_date = pd.to_datetime(end_date)
            
            if st.button("Run Analysis"):
                with st.spinner("Generating charts..."):
                    patient_df_filtered = patient_df[
                        (pd.to_datetime(patient_df['date']) >= start_date) &
                        (pd.to_datetime(patient_df['date']) <= end_date)
                    ]
                    grouped_All_filtered = grouped_All[
                        (pd.to_datetime(grouped_All['date']) >= start_date) &
                        (pd.to_datetime(grouped_All['date']) <= end_date)
                    ]
                    pivoted_df_filtered = pivoted_df[
                        (pd.to_datetime(pivoted_df['date']) >= start_date) &
                        (pd.to_datetime(pivoted_df['date']) <= end_date)
                    ]
                    if facility != "All Facilities":
                        patient_df_filtered = patient_df_filtered[patient_df_filtered['FacilityName'] == facility]
                        grouped_All_filtered = grouped_All_filtered[grouped_All_filtered['FacilityName'] == facility]
                        pivoted_df_filtered = pivoted_df_filtered[pivoted_df_filtered['FacilityName'] == facility]
                    
                    result = plot_tat_trend(final_df, start_date, end_date, facility)
                    if result[0] is not None:
                        fig, csv_data, plot_bytes, start_date, end_date, hourly_stats_df = result
                        with st.container():
                            st.subheader("TAT Trend Chart (07:00–19:00)")
                            st.image(plot_bytes, use_container_width=True, output_format='PNG', clamp=True)
                        with st.container():
                            st.subheader("Hourly Statistics (07:00–19:00)")
                            st.dataframe(
                                hourly_stats_df.set_index('Metric'),
                                use_container_width=True,
                                column_config={
                                    hour: st.column_config.NumberColumn(format="%d")
                                    for hour in hourly_stats_df.columns if hour != 'Metric'
                                }
                            )
                    
                    cols = st.columns([2, 1])
                    with cols[0]:
                        tat_filter = st.selectbox("Select TAT Filter", ["All", "TAT above 1 hour (60)"])
                        if tat_filter == "TAT above 1 hour (60)":
                            filtered_df = patient_df_filtered[patient_df_filtered['Average_TAT'] > 59]
                        else:
                            filtered_df = patient_df_filtered
                        with st.container():
                            st.markdown('<div class="transparent-container">', unsafe_allow_html=True)
                            st.subheader("Patient-Level TAT Data")
                            st.write(filtered_df)
                            st.markdown('</div>', unsafe_allow_html=True)
                    
                    with cols[1]:
                        tat_filter_2 = st.selectbox("Select", ["All", "TAT above 1 hour (60)"])
                        if tat_filter_2 == "TAT above 1 hour (60)":
                            grouped_All_display = grouped_All_filtered[grouped_All_filtered['Average_TAT'] > 59]
                        else:
                            grouped_All_display = grouped_All_filtered
                        with st.container():
                            st.markdown('<div class="transparent-container">', unsafe_allow_html=True)
                            st.subheader("Facility-Level TAT Data")
                            st.write(grouped_All_display)
                            st.markdown('</div>', unsafe_allow_html=True)
                    
                    if not dept_final_df.empty:
                        dept_result = plot_departmental_tat(dept_final_df, start_date, end_date, facility)
                        if dept_result[0] is not None:
                            dept_fig, dept_plot_bytes = dept_result
                            with st.container():
                                st.subheader("Departmental Average TAT Comparison (07:00–19:00)")
                                st.image(dept_plot_bytes, use_container_width=True, output_format='PNG', clamp=True)
                    
                    with st.container():
                        st.markdown('<div class="transparent-container">', unsafe_allow_html=True)
                        st.subheader("Shift-Wise Average TAT")
                        st.write(pivoted_df_filtered)
                        st.markdown('</div>', unsafe_allow_html=True)
                    
                    with st.container():
                        csv_filename = f"tat_stats_{start_date.date()}_to_{end_date.date()}.csv"
                        csv_buffer = io.StringIO()
                        csv_data.to_csv(csv_buffer, index=False)
                        csv_bytes = csv_buffer.getvalue().encode('utf-8')
                        st.download_button(
                            label="Download Table Data (CSV)",
                            data=csv_bytes,
                            file_name=csv_filename,
                            mime="text/csv"
                        )
                        plot_filename = 'tat_trend_all_facilities.png' if facility == "All Facilities" else 'tat_trend.png'
                        st.download_button(
                            label="Download Overall TAT Plot (PNG)",
                            data=plot_bytes,
                            file_name=plot_filename,
                            mime="image/png"
                        )
                        if not dept_final_df.empty and dept_result[0] is not None:
                            dept_plot_filename = 'dept_tat_all_facilities.png' if facility == "All Facilities" else 'dept_tat.png'
                            st.download_button(
                                label="Download Departmental TAT Plot (PNG)",
                                data=dept_plot_bytes,
                                file_name=dept_plot_filename,
                                mime="image/png"
                            )
    else:
        st.error("Failed to load data. Please check the CSV file or path.")
else:
    st.info("Please upload a CSV file or specify a valid file path.")
