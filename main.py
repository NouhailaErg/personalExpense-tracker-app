import streamlit as st
import pandas as pd 
import plotly.express as px
import json
import os

# Set the Streamlit page configuration
st.set_page_config(page_title="Finance App", page_icon="🏛", layout="wide")

category_file = "categories.json"

# Initialize categories in session state if not already present
if "categories" not in st.session_state:
    st.session_state.categories = {
        "Uncategorized": []
    }

# Load saved categories from JSON file
if os.path.exists(category_file):
    with open(category_file, "r") as f:
        st.session_state.categories = json.load(f)

# Save categories to the JSON file
def save_categories():
    with open(category_file, "w")  as f:
        json.dump(st.session_state.categories, f)

# Categorize each transaction based on known keywords
def categorize_transactions(df):
    df["Category"] = "Uncategorized"
    for category, keywords in st.session_state.categories.items():
        if category == "Uncategorized" or not keywords:
            continue
        lower_keywords = [keyword.lower().strip() for keyword in keywords]
        for idx, row in df.iterrows():
            details = row["Details"].lower().strip()
            if details in lower_keywords:
                df.at[idx, "Category"] = category 
    return df

# Load and clean transaction CSV
def load_transactions(file):
    try:
        df = pd.read_csv(file)
        df.columns = [col.strip() for col in df.columns]
        df["Amount"] = df["Amount"].str.replace(",", "").astype(float)
        df["Date"] = pd.to_datetime(df["Date"], format="%d %b %Y")
        return categorize_transactions(df)
    except Exception as e:
        st.error(f"Error processing file: {str(e)}")
        return None

# Add keyword to a given category
def add_keyword_to_category(category, keyword):
    keyword = keyword.strip()
    if keyword and keyword not in st.session_state.categories[category]:
        st.session_state.categories[category].append(keyword)
        save_categories()
        return True

# Main app logic
def main():
    st.title("Finance Dashboard")

    upload_file = st.file_uploader("Upload your transaction CSV file", type=["csv"])

    if upload_file is not None:
        df = load_transactions(upload_file)

        if df is not None:
            debits_df = df[df["Debit/Credit"]== "Debit"].copy()
            credits_df = df[df["Debit/Credit"]== "Credit"].copy()

            st.session_state.debits_df = debits_df.copy()

            tab1, tab2 = st.tabs(["Expenses (Debits)", "Payements (Credits)"])

            # Tab 1: Debits / Expenses
            with tab1:
                new_category = st.text_input("New category Name")
                add_button = st.button("Add Category")

                if add_button and new_category:
                    if new_category not in st.session_state.categories:
                        st.session_state.categories[new_category] = []
                        save_categories()
                        st.rerun()

                st.subheader("Your Expenses")

                # Allow user to edit categories
                edited_df = st.data_editor(
                    st.session_state.debits_df[["Date", "Details", "Amount", "Category"]],
                    column_config={
                        "Date": st.column_config.DateColumn("Date", format="DD/MM/YYYY"),
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED"),
                        "Category": st.column_config.SelectboxColumn(
                            "Category",
                            options=list(st.session_state.categories.keys())
                        )
                    },
                    hide_index=True,
                    use_container_width=True,
                    key="category_editor"
                )

                save_button = st.button("Apply Changes", type="primary")
                if save_button:
                    for idx, row in edited_df.iterrows():
                        new_category = row["Category"]
                        if new_category == st.session_state.debits_df.at[idx, "Category"]:
                            continue
                        details = row["Details"]
                        st.session_state.debits_df.at[idx, "Category"] = new_category
                        add_keyword_to_category(new_category, details)

                st.subheader('Expense Summary')
                category_totals = st.session_state.debits_df.groupby("Category")["Amount"].sum().reset_index()
                category_totals = category_totals.sort_values("Amount", ascending=False)

                st.dataframe(category_totals,
                    column_config={
                        "Amount": st.column_config.NumberColumn("Amount", format="%.2f AED")
                    },
                    use_container_width=True,
                    hide_index=True
                )

                # Plot pie chart
                fig = px.pie(
                    category_totals,
                    values="Amount",
                    names="Category",
                    title="Expenses by Category"
                )
                st.plotly_chart(fig, use_container_width=True)

            # Tab 2: Credits / Payments
            with tab2:
                st.subheader("Payments Summary")

                # Create a copy to avoid modifying the original dataframe
                credits_display_df = credits_df.copy()

                # Combine amount and currency
                credits_display_df["Amount"] = credits_display_df["Amount"].apply(lambda x: f"{x:,.2f}") + " " + credits_display_df["Currency"]

                # Drop the separate Currency column
                credits_display_df.drop(columns=["Currency"], inplace=True)

                # Calculate total payments
                total_payments = credits_df["Amount"].sum()
                st.metric("Total Payments", f"{total_payments:,.2f} AED")

                # Display the updated dataframe
                st.write(credits_display_df[["Date", "Details", "Amount", "Debit/Credit", "Status"]])


main()