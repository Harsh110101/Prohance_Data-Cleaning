import streamlit as st
import pandas as pd
import datetime

st.set_page_config(page_title="DNC CSV Filter", layout="wide")
st.title("📤 DNC Filter & Merger for CSVs")

# --- Step 1: Upload DNC Domains ---
st.header("Step 1: Upload DNC Domains List")
domain_file = st.file_uploader("Upload a CSV file containing DNC Domains", type=["csv"], key="domain")

# --- Step 2: Upload DNC Emails ---
st.header("Step 2: Upload DNC Emails List")
email_file = st.file_uploader("Upload a CSV file containing DNC Emails", type=["csv"], key="email")

# --- Step 3: Upload Emails Added in Last 6 Months ---
st.header("Step 3: Upload Recent Emails to Exclude")
recent_emails_file = st.file_uploader("Upload a CSV containing emails added in the last 6 months", type=["csv"], key="recent_emails")

# --- Step 4: Upload CSVs to be Filtered ---
st.header("Step 4: Upload CSVs to Filter (ZoomInfo, Apollo, etc.)")
data_files = st.file_uploader("Upload one or more CSV files", type=["csv"], accept_multiple_files=True)

# --- Step 5: Merge Option ---
st.header("Step 5: Choose Merge Option")
merge_data = st.radio("Do you want to merge all filtered data into one file?", ["Yes", "No"]) == "Yes"

# --- Step 6: Run Filtering and Download ---
if st.button("Step 6: Run Filtering"):
    if not domain_file or not email_file or not data_files:
        st.error("⚠️ Please upload all required files.")
    else:
        # Load blocklists
        dnc_domains = pd.read_csv(domain_file, encoding='ISO-8859-1').iloc[:, 0].dropna().str.lower().tolist()
        dnc_emails = pd.read_csv(email_file, encoding='ISO-8859-1').iloc[:, 0].dropna().str.lower().tolist()

        # Load recent emails
        if recent_emails_file:
            recent_emails = pd.read_csv(recent_emails_file, encoding='ISO-8859-1').iloc[:, 0].dropna().str.lower().tolist()
        else:
            recent_emails = []

        unwanted_titles = ["marketing", "sales", "regional", "market", "legal"]
        filtered_data = []
        skipped_files = []

        def parse_zoominfo(df):
            return pd.DataFrame({
                "First Name": df.get("First Name"),
                "Last Name": df.get("Last Name"),
                "Full Name": df.get("First Name") + " " + df.get("Last Name"),
                "Title": df.get("Job Title"),
                "Email": df.get("Email Address"),
                "Domain": df.get("Email Address").str.split("@").str[1].str.lower(),
                "Company Name": df.get("Company Name"),
                "Website": df.get("Website"),
                "Person LinkedIn URL": df.get("LinkedIn Contact Profile URL"),
                "Source": "ZoomInfo"
            })

        def parse_apollo(df):
            df["Domain"] = df["Email"].str.split("@").str[1].str.lower()
            return pd.DataFrame({
                "First Name": df.get("First Name"),
                "Last Name": df.get("Last Name"),
                "Full Name": df.get("First Name") + " " + df.get("Last Name"),
                "Title": df.get("Title"),
                "Email": df.get("Email").str.lower(),
                "Domain": df.get("Domain"),
                "Company Name": df.get("Company"),
                "Website": df.get("Website"),
                "Person LinkedIn URL": df.get("Person Linkedin Url"),
                "Source": "Apollo"
            })

        for file in data_files:
            df = pd.read_csv(file)
            original_file_name = file.name

            # Detect format
            if {"ZoomInfo Contact ID", "LinkedIn Contact Profile URL"}.intersection(df.columns):
                parsed = parse_zoominfo(df)
            elif {"Person Linkedin Url", "Work Direct Phone", "Departments"}.intersection(df.columns):
                parsed = parse_apollo(df)
            else:
                st.warning(f"❌ Skipped unknown format: {original_file_name}")
                continue

            before = len(parsed)
            parsed = parsed[
                (~parsed["Domain"].isin(dnc_domains)) &
                (~parsed["Email"].isin(dnc_emails)) &
                (~parsed["Email"].isin(recent_emails)) &  # 🆕 Exclude recent
                (~parsed["Title"].str.contains("|".join(unwanted_titles), na=False, case=False))
            ]
            after = len(parsed)
            st.success(f"✅ {original_file_name}: Filtered {before - after} rows, kept {after}")

            parsed["Source File"] = original_file_name
            filtered_data.append(parsed)

        # Final Output: Merged or Individual
        if merge_data:
            final_df = pd.concat(filtered_data, ignore_index=True)
            csv = final_df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "⬇️ Download Merged CSV",
                data=csv,
                file_name="filtered_merged.csv",
                mime="text/csv"
            )
        else:
            for df in filtered_data:
                if df.empty:
                    file_label = df["Source File"].iloc[0] if "Source File" in df.columns and not df["Source File"].empty else "Unknown"
                    skipped_files.append(file_label)
                    continue

                filename = df["Source File"].iloc[0].replace(".csv", "_filtered.csv")
                csv = df.to_csv(index=False).encode("utf-8")
                st.download_button(
                    f"⬇️ Download {filename}",
                    data=csv,
                    file_name=filename,
                    mime="text/csv",
                    key=filename
                )

        # Show skipped files
        if skipped_files:
            st.warning(f"⚠️ Skipped empty filtered file(s): {', '.join(skipped_files)}")
