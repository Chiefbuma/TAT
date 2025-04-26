import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
import warnings

# Suppress warnings related to tight_layout
warnings.filterwarnings('ignore', category=UserWarning, message='.*tight_layout.*')

# Set page config as the first Streamlit command
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
        .stButton button {
            background-color: #333333;
            color: white;
            border: 1px solid white;
        }
        .stTable {
            color: white;
        }
        table, th, td {
            border: 1px solid white;
            border-collapse: collapse;
            background-color: #333333;
            color: white;
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
    try:
        TAT_df = pd.read_csv(csv_path, dtype={'UHID': str}, low_memory=False)
    except FileNotFoundError:
        st.error(f"CSV file not found at {csv_path}. Please ensure the file exists.")
        return None
    except Exception as e:
        st.error(f"Error reading the CSV file: {e}")
        return None

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
        return None
    
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
        return None

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

    return filtered_period_df

# Function to create a plot with TAT trend and a table below it
def plot_tat_trend(df, start_year, start_month, start_day, end_year, end_month, end_day, facility):
    # Construct start and end dates
    start_date = pd.to_datetime(f"{start_year}-{start_month}-{start_day}")
    end_date = pd.to_datetime(f"{end_year}-{end_month}-{end_day}")

    # Ensure start_date <= end_date
    if start_date > end_date:
        start_date, end_date = end_date, start_date

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
        return None, None, None, None, None

    # If a specific facility is selected (not "All Facilities"), filter by facility
    if facility != "All Facilities":
        filtered_df = filtered_df[filtered_df['FacilityName'] == facility]
        if filtered_df.empty:
            st.error(f"No data available for facility: {facility} in the selected date range.")
            return None, None, None, None, None

    # Create figure with two subplots: one for the graph, one for the table
    fig = plt.figure(figsize=(14, 8), facecolor='black')
    gs = fig.add_gridspec(2, 1, height_ratios=[3, 1], hspace=0.4)

    # --- Plot the TAT Trend (Top Subplot) ---
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.set_facecolor('black')

    # Plot TAT Trend (per minute, left y-axis)
    minutes = filtered_df['Minutes_Since_Midnight']
    tat = filtered_df['TAT']

    # Create a full minute range (00:00 to 23:59 = 1440 minutes)
    all_minutes = np.arange(0, 1440)
    tat_full = np.full_like(all_minutes, np.nan, dtype=float)

    # Group by minute and average TAT across all days (and facilities if "All Facilities")
    minute_groups = filtered_df.groupby('Minutes_Since_Midnight')['TAT'].mean()
    for min_val, tat_val in minute_groups.items():
        tat_full[int(min_val)] = tat_val

    # Interpolate to fill gaps (linear interpolation)
    tat_series = pd.Series(tat_full)
    tat_interpolated = tat_series.interpolate(method='linear')

    # Plot TAT on the left y-axis
    label = 'Overall TAT (All Facilities)' if facility == "All Facilities" else f'{facility} TAT'
    ax1.plot(all_minutes, tat_interpolated, linewidth=2, label=label, color='cyan')
    ax1.set_xlabel('Time of Day', fontsize=12, color='white')
    ax1.set_ylabel('Average TAT (Minutes)', fontsize=12, color='cyan')
    ax1.tick_params(axis='y', labelcolor='cyan')
    ax1.tick_params(axis='x', labelcolor='white')

    # Set x-axis with 1-hour intervals (00:00 to 23:00)
    title = f'Overall TAT Trend (24 Hours) - All Facilities - {start_date.date()} to {end_date.date()}' if facility == "All Facilities" else f'TAT Trend (24 Hours) - {facility} - {start_date.date()} to {end_date.date()}'
    ax1.set_title(title, fontsize=14, color='white')
    ax1.set_xticks(np.arange(0, 1440, 60))
    ax1.set_xticklabels([f'{h:02d}:00' for h in range(0, 24)], rotation=45)
    ax1.grid(True, alpha=0.3, color='gray')

    # Add legend
    ax1.legend(loc='upper left', labelcolor='white')

    # --- Create the Hourly Table (Bottom Subplot) ---
    ax_table = fig.add_subplot(gs[1, 0])
    ax_table.set_facecolor('black')

    # Group by hour to calculate average TAT and count of unique records (footfalls)
    hourly_stats = filtered_df.groupby('Hour').agg({
        'TAT': 'mean',
        'Unique': 'nunique'
    }).reindex(range(24), fill_value=0)

    # Round average TAT to 2 decimal places
    hourly_stats['TAT'] = hourly_stats['TAT'].round(2)

    # Prepare table data
    table_data = [
        hourly_stats['TAT'].values,
        hourly_stats['Unique'].values
    ]
    row_labels = ['Avg TAT (min)', 'Footfalls']
    col_labels = [f'{h}' for h in range(24)]

    # Create the table with white text for visibility
    table = ax_table.table(cellText=table_data,
                           rowLabels=row_labels,
                           colLabels=col_labels,
                           cellLoc='center',
                           loc='center',
                           cellColours=[[('#333333' if val != 0 else 'black') for val in row] for row in table_data],
                           colColours=['#333333' for _ in range(24)],
                           rowColours=['#333333', '#333333'])
    
    # Style the table
    table.auto_set_font_size(False)
    table.set_fontsize(8)
    for key, cell in table.get_celld().items():
        cell.set_text_props(color='white')
    table.scale(1, 1.5)
    ax_table.axis('off')

    # Prepare CSV export data
    stats_df = filtered_df.groupby(['FacilityName', 'Hour']).agg({
        'TAT': 'mean',
        'Unique': 'nunique'
    }).reset_index()

    # Round average TAT to 2 decimal places
    stats_df['TAT'] = stats_df['TAT'].round(2)

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

    # Adjust layout manually to prevent overlap
    plt.subplots_adjust(top=0.85, bottom=0.15, hspace=0.4)

    # Save the plot to a bytes buffer for download
    buf = io.BytesIO()
    plt.savefig(buf, format='png', facecolor='black')
    buf.seek(0)
    plot_bytes = buf.getvalue()
    buf.close()

    return fig, csv_data, plot_bytes, start_date, end_date

# Streamlit app
st.title("TAT Analysis Dashboard")
st.markdown("Select the date range and facility to analyze the Turnaround Time (TAT) trends.")

# Load the data
csv_path = "data/ConsolidatedTATReportNew.csv"  # Adjust this path for your setup
df = fetch_and_process_data(csv_path)

if df is not None:
    # Get unique values for filters
    years = sorted(df['Year'].dropna().unique().astype(int))
    if not years:
        st.error("No valid years available in the data.")
    else:
        # Create columns for the input widgets
        col1, col2, col3, col4, col5, col6, col7 = st.columns(7)

        with col1:
            start_year = st.selectbox("Start Year", options=years, index=0)
        with col2:
            start_months = sorted(df[df['Year'] == start_year]['Month'].dropna().unique().astype(int))
            start_month = st.selectbox("Start Month", options=start_months, index=0)
        with col3:
            start_days = sorted(df[(df['Year'] == start_year) & (df['Month'] == start_month)]['Day'].dropna().unique().astype(int))
            start_day = st.selectbox("Start Day", options=start_days, index=0)

        with col4:
            end_year = st.selectbox("End Year", options=years, index=len(years)-1)
        with col5:
            end_months = sorted(df[df['Year'] == end_year]['Month'].dropna().unique().astype(int))
            end_month = st.selectbox("End Month", options=end_months, index=len(end_months)-1)
        with col6:
            end_days = sorted(df[(df['Year'] == end_year) & (df['Month'] == end_month)]['Day'].dropna().unique().astype(int))
            end_day = st.selectbox("End Day", options=end_days, index=len(end_days)-1)

        with col7:
            facility_options = ['All Facilities'] + sorted(df['FacilityName'].unique().tolist())
            facility = st.selectbox("Facility", options=facility_options, index=0)

        # Button to run the analysis
        if st.button("Run Analysis"):
            result = plot_tat_trend(df, start_year, start_month, start_day, end_year, end_month, end_day, facility)
            if result[0] is not None:
                fig, csv_data, plot_bytes, start_date, end_date = result
                # Display the plot
                st.pyplot(fig)
                plt.close()

                # Provide download links
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