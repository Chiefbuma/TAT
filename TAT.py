import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
import warnings
from datetime import datetime

# Suppress warnings related to tight_layout and deprecation warnings
warnings.filterwarnings('ignore', category=UserWarning, message='.*tight_layout.*')
warnings.filterwarnings('ignore', category=DeprecationWarning, message='.*use_column_width.*')

# Set page config as the first Streamlit command
st.set_page_config(page_title="TAT Analysis Dashboard", layout="wide")

# Apply CSS styling with rounded borders and transparent containers
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
        /* Apply rounded borders to st.container */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid white !important;
            border-radius: 15px !important;
            padding: 10px;
            background-color: #1a1a1a;
        }
        /* Transparent containers for specific sections */
        .transparent-container div[data-testid="stVerticalBlockBorderWrapper"] {
            background-color: rgba(255, 255, 255, 0.1) !important; /* Semi-transparent white */
            border: 1px solid white !important;
            border-radius: 15px !important;
        }
    </style>
""", unsafe_allow_html=True)

# Function to classify shifts based on time of day (24-hour operation)
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

# Main data processing function to load and process CSV data
@st.cache_data  # Cache the data loading for performance
def fetch_and_process_data(csv_path):
    import os
    # Debugging: Check if file exists
    if not os.path.exists(csv_path):
        st.error(f"File does not exist at path: {csv_path}")
        return None, None, None, None

    # Debugging: Check file size
    file_size = os.path.getsize(csv_path)
    if file_size == 0:
        st.error(f"File at {csv_path} is empty.")
        return None, None, None, None

    try:
        TAT_df = pd.read_csv(csv_path, dtype={'UHID': str}, low_memory=False)
        # Debugging: Check if DataFrame is empty
        if TAT_df.empty:
            st.error("CSV file loaded but contains no data.")
            return None, None, None, None
    except FileNotFoundError:
        st.error(f"CSV file not found at {csv_path}. Please ensure the file exists.")
        return None, None, None, None
    except Exception as e:
        st.error(f"Error reading the CSV file: {e}")
        return None, None, None, None

    # Define datetime columns to parse
    datetime_columns = [
        'ConsultationBillingTime',
        'Pharmacy_Billing_Time'
    ]

    # Convert datetime columns
    for col in datetime_columns:
        if col in TAT_df.columns:
            TAT_df[col] = pd.to_datetime(TAT_df[col], dayfirst=True, errors='coerce')

    # Select required columns for TAT calculation
    columns_to_import = [
        'UHID', 'PatientName', 'Department', 'FacilityName',
        'ConsultationBillingTime', 'Pharmacy_Billing_Time'
    ]

    # Check for missing columns
    missing_cols = [col for col in columns_to_import if col not in TAT_df.columns]
    if missing_cols:
        st.error(f"Missing required columns in CSV: {missing_cols}")
        return None, None, None, None
    
    # Keep only the required columns
    TAT_df = TAT_df[columns_to_import].copy()

    # Filter out invalid data
    filtered_TAT_df = TAT_df.dropna(subset=['UHID'])
    filtered_TAT_df = filtered_TAT_df[filtered_TAT_df['FacilityName'] != "Bliss Medical Centre HomeCare"]

    # Split data by department
    Consultation_df = filtered_TAT_df[filtered_TAT_df['Department'] == 'GENERAL OPD'].drop(
        columns=['Pharmacy_Billing_Time'] if 'Pharmacy_Billing_Time' in filtered_TAT_df.columns else []).copy()
    Pharmacy_df = filtered_TAT_df[filtered_TAT_df['Department'] == 'Pharmacy'].drop(
        columns=['ConsultationBillingTime'] if 'ConsultationBillingTime' in filtered_TAT_df.columns else []).copy()

    # Add date columns for grouping
    Consultation_df['date'] = Consultation_df['ConsultationBillingTime'].dt.date
    Pharmacy_df['date'] = Pharmacy_df['Pharmacy_Billing_Time'].dt.date

    # Group and aggregate data by taking the earliest timestamps
    TAT_pharmacy_df = Pharmacy_df.groupby(['date', 'UHID', 'PatientName', 'FacilityName']).agg({
        'Pharmacy_Billing_Time': 'min',
        'Department': 'first'
    }).reset_index()

    TAT_consultation_df = Consultation_df.groupby(['date', 'UHID', 'PatientName', 'FacilityName']).agg({
        'ConsultationBillingTime': 'min',
        'Department': 'first'
    }).reset_index()

    # Create unique identifiers for matching records
    for df in [TAT_pharmacy_df, TAT_consultation_df]:
        df['Unique'] = df['UHID'].astype(str) + "_" + \
                       df['PatientName'].astype(str) + "_" + \
                       df['FacilityName'].astype(str) + "_" + \
                       df['date'].astype(str)

    # Merge consultation and pharmacy data
    merged_df = TAT_consultation_df.merge(
        TAT_pharmacy_df[['Unique', 'Pharmacy_Billing_Time']],
        on='Unique',
        how='left'
    )

    # Calculate TAT for matched records
    filtered_merged_df = merged_df[merged_df['Pharmacy_Billing_Time'].notna()].copy()
    filtered_merged_df['TAT'] = (filtered_merged_df['Pharmacy_Billing_Time'] - 
                                 filtered_merged_df['ConsultationBillingTime']).dt.total_seconds() / 60
    # Remove records with negative TAT by filtering
    filtered_merged_df = filtered_merged_df[filtered_merged_df['TAT'] >= 0].copy()
    filtered_merged_df['Time_out'] = filtered_merged_df['Pharmacy_Billing_Time']
    filtered_merged_df['Department'] = 'TAT'

    # No time filter needed since we want 24-hour data
    filtered_period_df = filtered_merged_df.copy()

    if filtered_period_df.empty:
        st.error("No data available after processing.")
        return None, None, None, None

    # Calculate minutes since midnight for plotting (24-hour range)
    filtered_period_df['Minutes_Since_Midnight'] = (
        filtered_period_df['Time_out'].dt.hour * 60 +
        filtered_period_df['Time_out'].dt.minute
    )

    # Extract hour for hourly table
    filtered_period_df['Hour'] = filtered_period_df['Time_out'].dt.hour

    # Add shift and date components
    filtered_period_df['Shift'] = filtered_period_df['Time_out'].apply(classify_shift)
    filtered_period_df['Year'] = filtered_period_df['Time_out'].dt.year
    filtered_period_df['Month'] = filtered_period_df['Time_out'].dt.month
    filtered_period_df['Day'] = filtered_period_df['Time_out'].dt.day
    filtered_period_df['Date'] = pd.to_datetime(filtered_period_df[['Year', 'Month', 'Day']])
    
    # Add Time column by extracting the time portion from Time_out
    filtered_period_df['Time'] = filtered_period_df['Time_out'].dt.time

    # Additional DataFrames requested
    # Create a new column 'time' to extract only the time part
    filtered_merged_df['time'] = filtered_merged_df['Pharmacy_Billing_Time'].dt.time

    # Create a new column 'Shift' by applying the classify_shift function
    filtered_merged_df['Shift'] = filtered_merged_df['Pharmacy_Billing_Time'].apply(classify_shift)

    # Group by 'date', 'FacilityName', and 'Shift'
    grouped_df = filtered_merged_df.groupby(['date', 'FacilityName', 'Shift']).agg(
        # Count of unique UHID
        Unique_UHID_Count=('UHID', 'nunique'),
        Average_TAT=('TAT', 'mean')  # Average TAT
    ).reset_index()

    # Group by 'date', 'PatientName', 'FacilityName', 'ConsultationBillingTime', 'Pharmacy_Billing_Time'
    patient_df = filtered_merged_df.groupby(['date', 'PatientName', 'FacilityName', 'ConsultationBillingTime', 'Pharmacy_Billing_Time']).agg(
        Average_TAT=('TAT', 'mean')  # Average TAT
    ).reset_index()

    # Add 20 minutes to Average TAT
    patient_df['Average_TAT'] += 20

    # Group by 'date' and 'FacilityName'
    grouped_All = filtered_merged_df.groupby(['date', 'FacilityName']).agg(
        Average_TAT=('TAT', 'mean')  # Average TAT
    ).reset_index()

    # Add 20 minutes to Average TAT
    grouped_All['Average_TAT'] += 20

    # Pivot the DataFrame with FacilityName and date as index, and Shift as columns
    pivoted_df = grouped_df.pivot_table(
        index=['FacilityName', 'date'],  # Rows as medical centers and date
        columns='Shift',                 # Columns as shifts
        values='Average_TAT',            # Values as Average TAT
        aggfunc='mean'                   # Average in case of multiple entries
    )

    # Calculate the daily average (across shift columns) and add it as a new column
    pivoted_df['Day Avg'] = pivoted_df.mean(axis=1)

    # Convert TAT from minutes to "X hr Y min" format for each column, including 'Day Avg'
    pivoted_df = pivoted_df.applymap(
        lambda x: f"{int(x // 60)} hr {int(x % 60)} min" if pd.notnull(x) else "")

    # Reset index to make 'FacilityName' and 'date' columns
    pivoted_df = pivoted_df.reset_index()

    # Optional: Remove MultiIndex column names
    pivoted_df.columns.name = None

    # Reorder columns based on preferred shift order, including 'Day Avg'
    preferred_order = ["FacilityName", "date", "Morning", "Mid Morning", "Afternoon", "Evening", "Night Shift", "Day Avg"]
    # Retain only existing columns
    existing_columns = [col for col in preferred_order if col in pivoted_df.columns]
    pivoted_df = pivoted_df[existing_columns]

    return filtered_period_df, patient_df, grouped_All, pivoted_df

# Function to create a plot with TAT trend (no table subplot)
def plot_tat_trend(df, start_date, end_date, facility):
    # Filter data based on the date range
    filtered_df = df[
        (df['Date'] >= start_date) &
        (df['Date'] <= end_date)
    ]

    if filtered_df.empty:
        st.warning(f"No data available for the selected date range: {start_date.date()} to {end_date.date()}.")
        earliest_date = df['Date'].min()
        latest_date = df['Date'].max()
        st.info(f"Falling back to full date range: {earliest_date.date()} to {latest_date.date()}")
        filtered_df = df[
            (df['Date'] >= earliest_date) &
            (df['Date'] <= latest_date)
        ]
        start_date, end_date = earliest_date, latest_date

    if filtered_df.empty:
        st.error("No data available even with fallback filters.")
        return None, None, None, None, None, None

    # If a specific facility is selected (not "All Facilities"), filter by facility
    if facility != "All Facilities":
        filtered_df = filtered_df[filtered_df['FacilityName'] == facility]
        if filtered_df.empty:
            st.error(f"No data available for facility: {facility} in the selected date range.")
            return None, None, None, None, None, None

    # Prepare hourly stats to determine the x-axis range based on footfalls
    hourly_stats = filtered_df.groupby('Hour').agg({
        'TAT': 'mean',
        'Unique': 'nunique'
    }).reindex(range(24), fill_value=0)

    # Round average TAT to 0 decimal places
    hourly_stats['TAT'] = hourly_stats['TAT'].round(0)

    # Determine the x-axis range based on hours with footfalls
    hours_with_footfalls = hourly_stats[hourly_stats['Unique'] > 0].index
    if len(hours_with_footfalls) == 0:
        st.error("No footfalls recorded in the selected date range.")
        return None, None, None, None, None, None

    start_hour = hours_with_footfalls.min()
    end_hour = hours_with_footfalls.max()
    start_minute = start_hour * 60  # Convert to minutes since midnight
    end_minute = (end_hour + 1) * 60  # End of the last hour with footfalls

    # Create figure for the plot (reduced height)
    fig = plt.figure(figsize=(14, 4), facecolor='black')  # Reduced height from 6 to 4
    ax1 = fig.add_subplot(111)  # Single subplot
    ax1.set_facecolor('black')

    # Plot TAT Trend (per minute)
    minutes = filtered_df['Minutes_Since_Midnight']
    tat = filtered_df['TAT']

    # Create a minute range based on footfalls
    all_minutes = np.arange(start_minute, end_minute)
    tat_full = np.full_like(all_minutes, np.nan, dtype=float)

    # Group by minute and average TAT across all days (and facilities if "All Facilities")
    minute_groups = filtered_df.groupby('Minutes_Since_Midnight')['TAT'].mean()
    for min_val, tat_val in minute_groups.items():
        if start_minute <= min_val < end_minute:
            tat_full[int(min_val - start_minute)] = tat_val

    # Interpolate to fill gaps (linear interpolation)
    tat_series = pd.Series(tat_full)
    tat_interpolated = tat_series.interpolate(method='linear')

    # Plot TAT
    label = 'Overall TAT (All Facilities)' if facility == "All Facilities" else f'{facility} TAT'
    ax1.plot(all_minutes, tat_interpolated, linewidth=2, label=label, color='cyan')
    ax1.set_xlabel('Time of Day', fontsize=12, color='white')
    ax1.set_ylabel('Average TAT (Minutes)', fontsize=12, color='cyan')
    ax1.tick_params(axis='y', labelcolor='cyan')
    ax1.tick_params(axis='x', labelcolor='white')

    # Set x-axis with 1-hour intervals within the footfall range
    title = f'Overall TAT Trend - All Facilities - {start_date.date()} to {end_date.date()}' if facility == "All Facilities" else f'TAT Trend - {facility} - {start_date.date()} to {end_date.date()}'
    ax1.set_title(title, fontsize=14, color='white')
    ax1.set_xticks(np.arange(start_minute, end_minute, 60))
    ax1.set_xticklabels([f'{h:02d}:00' for h in range(start_hour, end_hour + 1)], rotation=45)
    ax1.grid(True, alpha=0.3, color='gray')

    # Add legend
    ax1.legend(loc='upper left', labelcolor='white')

    # Adjust layout for the plot
    plt.tight_layout()

    # Save the plot to a bytes buffer for display and download
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor='black')
    buf.seek(0)
    plot_bytes = buf.getvalue()
    plt.close()

    # Prepare hourly stats for Streamlit table (pivoted format)
    hours = [f"{h:02d}:00" for h in range(24)]
    tat_row = hourly_stats['TAT'].values
    footfall_row = hourly_stats['Unique'].values
    hourly_stats_df = pd.DataFrame({
        'Metric': ['Avg TAT (min)', 'Footfalls'],
        **{hour: [tat_row[i], footfall_row[i]] for i, hour in enumerate(hours)}
    })

    # Prepare CSV export data
    stats_df = filtered_df.groupby(['FacilityName', 'Hour']).agg({
        'TAT': 'mean',
        'Unique': 'nunique'
    }).reset_index()

    # Round average TAT to 0 decimal places for CSV export
    stats_df['TAT'] = stats_df['TAT'].round(0)

    # Ensure all hours (0-23) are present for each facility
    facilities = filtered_df['FacilityName'].unique()
    all_hours = range(24)
    all_combinations = pd.MultiIndex.from_product([facilities, all_hours], names=['FacilityName', 'Hour'])
    all_combinations_df = pd.DataFrame(index=all_combinations).reset_index()
    
    # Merge with stats_df to fill in missing hours with 0
    stats_df = all_combinations_df.merge(stats_df, on=['FacilityName', 'Hour'], how='left')
    stats_df['TAT'] = stats_df['TAT'].fillna(0)
    stats_df['Unique'] = stats_df['Unique'].fillna(0)

    # Format the Hours column as "Xam" or "Xpm"
    stats_df['Hours'] = stats_df['Hour'].apply(lambda x: f"{x % 12 if x % 12 != 0 else 12}{'am' if x < 12 else 'pm'}")

    # Prepare CSV data
    csv_data = stats_df[['FacilityName', 'Hours', 'TAT', 'Unique']].copy()
    csv_data.rename(columns={'Unique': 'Footfalls'}, inplace=True)

    return fig, csv_data, plot_bytes, start_date, end_date, hourly_stats_df

# Streamlit app
st.title("TAT Analysis Dashboard")
st.markdown("Select the date range and facility to analyze the Turnaround Time (TAT) trends.")

# Load the data
csv_path = "data/ConsolidatedTATReportNew.csv"  # Adjust this path for your setup
filtered_period_df, patient_df, grouped_All, pivoted_df = fetch_and_process_data(csv_path)

if filtered_period_df is not None:
    # Get the date range for the filters
    earliest_date = filtered_period_df['Date'].min()
    latest_date = filtered_period_df['Date'].max()

    if earliest_date is None or latest_date is None:
        st.error("No valid dates available in the data.")
    else:
        # Create columns for the input widgets
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
            facility_options = ['All Facilities'] + sorted(filtered_period_df['FacilityName'].unique().tolist())
            facility = st.selectbox("Facility", options=facility_options, index=0)

        # Convert start_date and end_date to datetime for comparison
        start_date = pd.to_datetime(start_date)
        end_date = pd.to_datetime(end_date)

        # Button to run the analysis
        if st.button("Run Analysis"):
            with st.spinner("Generating chart..."):
                # Apply date range filter to additional DataFrames
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

                # Apply facility filter to additional DataFrames
                if facility != "All Facilities":
                    patient_df_filtered = patient_df_filtered[patient_df_filtered['FacilityName'] == facility]
                    grouped_All_filtered = grouped_All_filtered[grouped_All_filtered['FacilityName'] == facility]
                    pivoted_df_filtered = pivoted_df_filtered[pivoted_df_filtered['FacilityName'] == facility]

                # 1. Display TAT Trend (Graph)
                result = plot_tat_trend(filtered_period_df, start_date, end_date, facility)
                if result[0] is not None:
                    fig, csv_data, plot_bytes, start_date, end_date, hourly_stats_df = result
                    
                    with st.container():
                        st.subheader("TAT Trend Chart")
                        st.image(plot_bytes, use_container_width=True, output_format='PNG', caption='', clamp=True)

                    # 2. Display Hourly TAT and Footfall Table
                    with st.container():
                        st.subheader("Hourly Statistics")
                        st.dataframe(
                            hourly_stats_df.set_index('Metric'),
                            use_container_width=True,
                            column_config={
                                hour: st.column_config.NumberColumn(
                                    hour,
                                    format="%d"  # Display all numbers as integers (0 decimal places)
                                ) for hour in hourly_stats_df.columns if hour != 'Metric'
                            }
                        )

                    # 3. Display Patient-Level and Facility-Level Data Side by Side
                    cols = st.columns([2, 1])
                    with cols[0]:
                        # Select box for TAT filter
                        tat_filter = st.selectbox("Select TAT Filter", ["All", "TAT above 1 hour (60)"])

                        # Apply filter based on the selected option
                        if tat_filter == "TAT above 1 hour (60)":
                            filtered_df = patient_df_filtered[patient_df_filtered['Average_TAT'] > 59]
                        else:
                            filtered_df = patient_df_filtered

                        # Display the filtered DataFrame in a transparent container
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

                        # Display the grouped DataFrame in a transparent container
                        with st.container():
                            st.markdown('<div class="transparent-container">', unsafe_allow_html=True)
                            st.subheader("Facility-Level TAT Data")
                            st.write(grouped_All_display)
                            st.markdown('</div>', unsafe_allow_html=True)

                    # 4. Display the Shift-Wise Average TAT (not specified in order, placed last)
                    with st.container():
                        st.markdown('<div class="transparent-container">', unsafe_allow_html=True)
                        st.subheader("Shift-Wise Average TAT")
                        st.write(pivoted_df_filtered)
                        st.markdown('</div>', unsafe_allow_html=True)

                    # Provide download links
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
                            label="Download Plot (PNG)",
                            data=plot_bytes,
                            file_name=plot_filename,
                            mime="image/png"
                        )
else:
    st.error("Failed to load data. Please check the CSV file path.")