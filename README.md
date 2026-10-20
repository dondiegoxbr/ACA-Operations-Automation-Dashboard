# ACA-Operations-Automation-Dashboard

End-to-end data processing and reporting automation using Python and Google Sheets.

**Role:** Operations Analyst | **Tools:** Python, Pandas, Google Sheets API | **Timeline:** 4 weeks

## Dashboard Preview

<img width="1745" height="648" alt="image" src="https://github.com/user-attachments/assets/2da284ec-33ee-4ced-8e2d-5aafe5f661a1" />

## 1. The Problem:

Personal project: inspired by recurring reporting challenges in my current role. Metrics were defined based on a discussion with my supervisor about the factors needed for monthly decision-making.This proof of concept covers a six-month reporting period (January–June) and  uses a synthetic dataset with intentionally injected errors to demonstrate the end-to-end process without exposing confidential client data.

Monthly operation reports for internal operations and management meetings required manual data cleaning, had inconsistent visualization choices, and no standardized format to answer recurring business questions. The process was slow and error-prone every month.

## 2. Approach & Execution:

**Key Questions:**
Interviewed my supervisor to identify which metrics to track for monthly reporting, then structured them using the SMART framework.

**Data Cleanup:**
Built a synthetic CSV composed of 13 columns and 1000 rows with injected errors to simulate messy real-world data. Handled misspelling and wrong formatting errors in policy ID, client name, carrier, members covered and premium fields. Corrected formatting on dates in multiple columns such as purchase date, deadline and cancellation date by casting strings to datetime. Converted empty strings to true nulls, removed duplicates. Calculated commissions for the agency and agents.

**Automation:**
Automated row sorting, column reorganization, and data uploads via the Google Sheets API. When the Python script is executed, it updates the spreadsheet data, triggering the recalculation of formulas and refresh of charts in the dashboard.

**Reporting:**
The fully cleaned dataset is uploaded as a reference sheet, separated from the dashboard, in case the team needs to check underlying detail. Used QUERY function to answer each business question, then matched it to the clearest chart type and grouped them into 3 dashboard sections (around 3 charts each).

## 3. Key Challenge & Solution:

Calculating monthly commissions required a complex nested formula in Google Sheets. Instead, I used Python to build a dataframe that tracks each policy's activity at month end. A policy was considered active at month end if its purchase date was on or before the last day of the month and its cancellation date was either empty or on or after the last day of the month. For each active policy, the corresponding commission value was recorded. Finally, commissions were summed by month to calculate total monthly revenue.

## 4. Results & Business Impact:

**Efficiency:** Reduced the simulated monthly reporting workflow from an estimated 2 hours of manual work to under 5 minutes per script execution, representing a time reduction of over 95%.

**Data Quality:** Automated data cleaning, validation, and standardization. Verified processing results against the known data quality issues intentionally injected into the synthetic dataset.

## 5. How to run:

Download both Python scripts and install the required dependencies listed in requirements.txt.

Create a Google Sheets spreadsheet and set up a Google Cloud service account with access to the spreadsheet.

Download the service account credentials JSON file and save it locally in the project folder as “creds.json”. Do not upload this file to GitHub.

**IMPORTANT: Fill in the “SPREADSHEET_ID” field with the corresponding value. Else the code will not run.**

Run the data generator script first, followed by the data processing script:

**python data_generator_opt.py**

**python csv_processing_opt.py**

The scripts generate synthetic raw data, process and clean the dataset, and update the spreadsheet.

