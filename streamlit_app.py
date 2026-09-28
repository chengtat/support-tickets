import datetime
import random
import sqlite3

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# --- PAGE CONFIG ---
st.set_page_config(page_title="Support Tickets Manager", page_icon="🎫", layout="wide")
st.title("🎫 Support Tickets Manager")
st.write(
    """
    An internal support ticket workflow app built with Streamlit and SQLite. 
    You can create, edit, and delete tickets, manage team members and issue categories, 
    view analytics, and export CSV reports.
    """
)

# --- DATABASE SETUP ---
DB_FILE = "tickets.db"


def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Create tables
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tickets (
            ID TEXT PRIMARY KEY,
            Issue TEXT,
            Issue_Type TEXT,
            Status TEXT,
            Priority TEXT,
            Assigned_To TEXT,
            Date_Submitted TEXT,
            Completed_Date TEXT
        )
    """)
    cursor.execute("CREATE TABLE IF NOT EXISTS team_members (name TEXT PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS issue_types (name TEXT PRIMARY KEY)")
    conn.commit()

    # Seed team members if empty
    cursor.execute("SELECT COUNT(*) FROM team_members")
    if cursor.fetchone()[0] == 0:
        default_members = [
            ("Alice Johnson",),
            ("Bob Smith",),
            ("Charlie Brown",),
            ("Diana Prince",),
            ("Unassigned",),
        ]
        cursor.executemany("INSERT INTO team_members VALUES (?)", default_members)

    # Seed issue types if empty
    cursor.execute("SELECT COUNT(*) FROM issue_types")
    if cursor.fetchone()[0] == 0:
        default_types = [
            ("Hardware",),
            ("Software",),
            ("Network",),
            ("Security",),
            ("Access & Credentials",),
            ("General IT",),
        ]
        cursor.executemany("INSERT INTO issue_types VALUES (?)", default_types)

    # Seed initial tickets if empty
    cursor.execute("SELECT COUNT(*) FROM tickets")
    if cursor.fetchone()[0] == 0:
        np.random.seed(42)
        descriptions = [
            "Network connectivity issues in the office",
            "Software application crashing on startup",
            "Printer not responding to print commands",
            "Email server downtime",
            "Data backup failure",
            "Login authentication problems",
            "VPN connection problems for remote employees",
        ]
        members = ["Alice Johnson", "Bob Smith", "Charlie Brown", "Diana Prince", "Unassigned"]
        types = ["Hardware", "Software", "Network", "Security", "Access & Credentials", "General IT"]

        sample_data = []
        for i in range(1100, 1000, -1):
            status = np.random.choice(["Open", "In Progress", "Closed"])
            date_submitted = datetime.date(2023, 6, 1) + datetime.timedelta(days=random.randint(0, 120))
            completed_date = (
                (date_submitted + datetime.timedelta(days=random.randint(1, 14)))
                if status == "Closed"
                else None
            )

            sample_data.append((
                f"TICKET-{i}",
                np.random.choice(descriptions),
                np.random.choice(types),
                status,
                np.random.choice(["High", "Medium", "Low"]),
                np.random.choice(members),
                str(date_submitted),
                str(completed_date) if completed_date else None,
            ))
        cursor.executemany("INSERT INTO tickets VALUES (?,?,?,?,?,?,?,?)", sample_data)

    conn.commit()
    conn.close()


# Run database initialization
init_db()


def load_data():
    conn = get_db_connection()
    df = pd.read_sql_query(
        """
        SELECT 
            ID, 
            Issue, 
            Issue_Type as "Issue Type", 
            Status, 
            Priority, 
            Assigned_To as "Assigned To", 
            Date_Submitted as "Date Submitted", 
            Completed_Date as "Completed Date" 
        FROM tickets
        """,
        conn,
    )
    team_members = pd.read_sql_query("SELECT name FROM team_members", conn)["name"].tolist()
    issue_types = pd.read_sql_query("SELECT name FROM issue_types", conn)["name"].tolist()
    conn.close()

    # Format date types
    if not df.empty:
        df["Date Submitted"] = pd.to_datetime(df["Date Submitted"]).dt.date
        df["Completed Date"] = pd.to_datetime(df["Completed Date"]).dt.date
    return df, team_members, issue_types


# Sync database state into session state
df_loaded, team_members_loaded, issue_types_loaded = load_data()
st.session_state.df = df_loaded
st.session_state.team_members = team_members_loaded
st.session_state.issue_types = issue_types_loaded


# --- SIDEBAR MANAGEMENT ---
with st.sidebar:
    st.header("⚙️ App Settings")

    # CSV Export
    with st.expander("📥 Export CSV Report", expanded=True):
        st.write("Download filtered or full ticket records.")
        status_filter = st.multiselect(
            "Filter Status for Export",
            options=["Open", "In Progress", "Closed"],
            default=["Open", "In Progress", "Closed"],
        )

        if not st.session_state.df.empty:
            filtered_df = st.session_state.df[st.session_state.df["Status"].isin(status_filter)]
            csv_data = filtered_df.to_csv(index=False).encode("utf-8")
            today_str = datetime.date.today().strftime("%Y-%m-%d")

            st.download_button(
                label="⬇️ Download CSV Report",
                data=csv_data,
                file_name=f"support_tickets_{today_str}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True,
            )
            st.caption(f"Exporting `{len(filtered_df)}` records")
        else:
            st.info("No ticket data available to export.")

    # Team Member Management
    with st.expander("👤 Team Management", expanded=False):
        with st.form("add_member_form", clear_on_submit=True):
            new_member = st.text_input("Add team member")
            if st.form_submit_button("Add Member"):
                cleaned = new_member.strip()
                if cleaned and cleaned not in st.session_state.team_members:
                    conn = get_db_connection()
                    conn.execute("INSERT INTO team_members VALUES (?)", (cleaned,))
                    conn.commit()
                    conn.close()
                    st.success(f"Added **{cleaned}**!")
                    st.rerun()

        st.divider()
        removable_members = [m for m in st.session_state.team_members if m != "Unassigned"]
        if removable_members:
            to_remove = st.selectbox("Remove team member", options=removable_members)
            if st.button("Remove Member", type="secondary"):
                conn = get_db_connection()
                conn.execute("DELETE FROM team_members WHERE name = ?", (to_remove,))
                conn.execute("UPDATE tickets SET Assigned_To = 'Unassigned' WHERE Assigned_To = ?", (to_remove,))
                conn.commit()
                conn.close()
                st.success(f"Removed **{to_remove}**.")
                st.rerun()

    # Issue Type Management
    with st.expander("🏷️ Issue Types Management", expanded=False):
        with st.form("add_type_form", clear_on_submit=True):
            new_type = st.text_input("Add issue type")
            if st.form_submit_button("Add Type"):
                cleaned = new_type.strip()
                if cleaned and cleaned not in st.session_state.issue_types:
                    conn = get_db_connection()
                    conn.execute("INSERT INTO issue_types VALUES (?)", (cleaned,))
                    conn.commit()
                    conn.close()
                    st.success(f"Added **{cleaned}**!")
                    st.rerun()

        st.divider()
        removable_types = [t for t in st.session_state.issue_types if t != "General IT"]
        if removable_types:
            to_remove_type = st.selectbox("Remove issue type", options=removable_types)
            if st.button("Remove Type", type="secondary"):
                conn = get_db_connection()
                conn.execute("DELETE FROM issue_types WHERE name = ?", (to_remove_type,))
                conn.execute("UPDATE tickets SET Issue_Type = 'General IT' WHERE Issue_Type = ?", (to_remove_type,))
                conn.commit()
                conn.close()
                st.success(f"Removed **{to_remove_type}**.")
                st.rerun()


# --- CREATE TICKET FORM ---
st.header("Add a ticket")

with st.form("add_ticket_form", clear_on_submit=True):
    issue_desc = st.text_area("Describe the issue")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        selected_type = st.selectbox("Issue Type", st.session_state.issue_types)
    with col_b:
        selected_priority = st.selectbox("Priority", ["High", "Medium", "Low"], index=1)
    with col_c:
        default_idx = (
            st.session_state.team_members.index("Unassigned")
            if "Unassigned" in st.session_state.team_members
            else 0
        )
        selected_assignee = st.selectbox("Assigned To", st.session_state.team_members, index=default_idx)

    submitted = st.form_submit_button("Submit", type="primary")

if submitted:
    if not issue_desc.strip():
        st.error("Please enter a valid issue description before submitting.")
    else:
        recent_num = (
            int(max(st.session_state.df["ID"]).split("-")[1])
            if not st.session_state.df.empty
            else 1000
        )
        new_id = f"TICKET-{recent_num + 1}"
        today_str = str(datetime.date.today())

        conn = get_db_connection()
        conn.execute(
            "INSERT INTO tickets VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (new_id, issue_desc.strip(), selected_type, "Open", selected_priority, selected_assignee, today_str, None),
        )
        conn.commit()
        conn.close()

        st.success(f"Ticket `{new_id}` submitted successfully!")
        st.rerun()


# --- VIEW & EDIT TICKETS ---
st.header("Existing tickets")
st.write(f"Number of tickets: `{len(st.session_state.df)}`")

st.info(
    "Double click cells to edit status, priority, issue type, assignee, or completed date.",
    icon="✍️",
)

edited_df = st.data_editor(
    st.session_state.df,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    column_config={
        "Issue Type": st.column_config.SelectboxColumn("Issue Type", options=st.session_state.issue_types, required=True),
        "Status": st.column_config.SelectboxColumn("Status", options=["Open", "In Progress", "Closed"], required=True),
        "Priority": st.column_config.SelectboxColumn("Priority", options=["High", "Medium", "Low"], required=True),
        "Assigned To": st.column_config.SelectboxColumn("Assigned To", options=st.session_state.team_members, required=True),
        "Completed Date": st.column_config.DateColumn("Completed Date", format="YYYY-MM-DD"),
        "Date Submitted": st.column_config.DateColumn("Date Submitted", format="YYYY-MM-DD"),
    },
    disabled=["ID", "Date Submitted"],
    key="ticket_editor",
)

# Persist data_editor changes to database
if not edited_df.equals(st.session_state.df):
    conn = get_db_connection()
    save_df = edited_df.rename(columns={
        "Issue Type": "Issue_Type",
        "Assigned To": "Assigned_To",
        "Date Submitted": "Date_Submitted",
        "Completed Date": "Completed_Date",
    })
    save_df.to_sql("tickets", conn, if_exists="replace", index=False)
    conn.close()
    st.session_state.df = edited_df
    st.rerun()

# Delete ticket by ID
with st.expander("🗑️ Delete a ticket by ID"):
    ticket_ids = st.session_state.df["ID"].tolist() if not st.session_state.df.empty else []
    if ticket_ids:
        ticket_to_delete = st.selectbox("Select Ticket ID to delete", options=ticket_ids)
        if st.button("Delete Selected Ticket", type="primary"):
            conn = get_db_connection()
            conn.execute("DELETE FROM tickets WHERE ID = ?", (ticket_to_delete,))
            conn.commit()
            conn.close()
            st.success(f"{ticket_to_delete} has been deleted.")
            st.rerun()
    else:
        st.info("No tickets available to delete.")


# --- METRICS & CHARTS ---
st.header("Statistics")

if not st.session_state.df.empty:
    df_calc = st.session_state.df.copy()

    col1, col2, col3, col4 = st.columns(4)
    num_open = len(df_calc[df_calc["Status"] == "Open"])
    num_closed = len(df_calc[df_calc["Status"] == "Closed"])

    col1.metric(label="Open tickets", value=num_open)
    col2.metric(label="Closed tickets", value=num_closed)
    col3.metric(label="First response time", value="5.2 hrs")
    col4.metric(label="Avg resolution time", value="16 hrs")

    st.write("")
    st.write("##### Ticket status overview")

    col_chart1, col_chart2, col_chart3 = st.columns(3)

    with col_chart1:
        st.write("##### Current ticket priorities")
        priority_plot = (
            alt.Chart(df_calc)
            .mark_arc()
            .encode(theta="count():Q", color="Priority:N")
            .properties(height=300)
        )
        st.altair_chart(priority_plot, use_container_width=True)

    with col_chart2:
        st.write("##### Tickets by Issue Type")
        type_plot = (
            alt.Chart(df_calc)
            .mark_bar()
            .encode(
                x="count():Q",
                y=alt.Y("Issue Type:N", sort="-x"),
                color="Issue Type:N",
            )
            .properties(height=300)
        )
        st.altair_chart(type_plot, use_container_width=True)

    with col_chart3:
        st.write("##### Tickets assigned per member")
        assignee_plot = (
            alt.Chart(df_calc)
            .mark_bar()
            .encode(
                x="count():Q",
                y=alt.Y("Assigned To:N", sort="-x"),
                color="Status:N",
            )
            .properties(height=300)
        )
        st.altair_chart(assignee_plot, use_container_width=True)
else:
    st.info("No ticket data available to render charts.")
