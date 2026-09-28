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
    An enhanced Streamlit support ticket management dashboard backed by SQLite for 
    persistent storage, automated metrics, dynamic charting, and CSV reporting.
    """
)

DB_FILE = "tickets.db"


def get_db_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)


def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

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
            completed_date = (date_submitted + datetime.timedelta(days=random.randint(1, 14))) if status == "Closed" else None

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

    # Cast date columns
    df["Date Submitted"] = pd.to_datetime(df["Date Submitted"]).dt.date
    df["Completed Date"] = pd.to_datetime(df["Completed Date"]).dt.date
    return df, team_members, issue_types


# Sync DB with Streamlit State
df, team_members, issue_types = load_data()
st.session_state.df = df
st.session_state.team_members = team_members
st.session_state.issue_types = issue_types


# --- SIDEBAR SETTINGS ---
with st.sidebar:
    st.header("⚙️ Settings & Management")

    with st.expander("📥 Export CSV Report", expanded=True):
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

    with st.expander("👤 Team Management", expanded=False):
        with st.form("add_member_form", clear_on_submit=True):
            new_member = st.text_input("New Member Name")
            if st.form_submit_button("Add Member"):
                cleaned = new_member.strip()
                if cleaned and cleaned not in st.session_state.team_members:
                    conn = get_db_connection()
                    conn.execute("INSERT INTO team_members VALUES (?)", (cleaned,))
                    conn.commit()
                    conn.close()
                    st.success(f"Added {cleaned}")
                    st.rerun()

        st.divider()
        removable_members = [m for m in st.session_state.team_members if m != "Unassigned"]
        if removable_members:
            to_remove = st.selectbox("Remove Member", options=removable_members)
            if st.button("Remove Selected Member"):
                conn = get_db_connection()
                conn.execute("DELETE FROM team_members WHERE name = ?", (to_remove,))
                conn.execute("UPDATE tickets SET Assigned_To = 'Unassigned' WHERE Assigned_To = ?", (to_remove,))
                conn.commit()
                conn.close()
                st.success(f"Removed {to_remove}")
                st.rerun()

    with st.expander("🏷️ Issue Types Management", expanded=False):
        with st.form("add_type_form", clear_on_submit=True):
            new_type = st.text_input("New Issue Category")
            if st.form_submit_button("Add Category"):
                cleaned = new_type.strip()
                if cleaned and cleaned not in st.session_state.issue_types:
                    conn = get_db_connection()
                    conn.execute("INSERT INTO issue_types VALUES (?)", (cleaned,))
                    conn.commit()
                    conn.close()
                    st.success(f"Added {cleaned}")
                    st.rerun()


# --- CREATE TICKET SECTION ---
st.header("➕ Create New Ticket")

with st.form("add_ticket_form", clear_on_submit=True):
    issue_desc = st.text_area("Issue Description", placeholder="Describe the problem in detail...")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        selected_type = st.selectbox("Issue Category", st.session_state.issue_types)
    with col_b:
        selected_priority = st.selectbox("Priority", ["High", "Medium", "Low"], index=1)
    with col_c:
        default_idx = st.session_state.team_members.index("Unassigned") if "Unassigned" in st.session_state.team_members else 0
        selected_assignee = st.selectbox("Assign To", st.session_state.team_members, index=default_idx)

    submitted = st.form_submit_button("Submit Ticket", type="primary")

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


# --- TICKET TABLE SECTION ---
st.header("📋 Existing Tickets")
st.caption(f"Total Records: `{len(st.session_state.df)}`")

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

# Persist updates made directly inside st.data_editor back to SQLite
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


# --- DASHBOARD METRICS & ANALYTICS ---
st.header("📊 Statistics & Insights")

if not st.session_state.df.empty:
    df_calc = st.session_state.df.copy()

    # Calculate real SLA metrics from available date data
    df_calc["Date Submitted"] = pd.to_datetime(df_calc["Date Submitted"])
    df_calc["Completed Date"] = pd.to_datetime(df_calc["Completed Date"])

    closed_mask = df_calc["Status"] == "Closed"
    df_closed = df_calc[closed_mask & df_calc["Completed Date"].notnull()]

    if not df_closed.empty:
        avg_res_days = (df_closed["Completed Date"] - df_closed["Date Submitted"]).dt.days.mean()
        avg_res_str = f"{avg_res_days:.1f} days"
    else:
        avg_res_str = "N/A"

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Open Tickets", len(df_calc[df_calc["Status"] == "Open"]))
    col2.metric("In Progress", len(df_calc[df_calc["Status"] == "In Progress"]))
    col3.metric("Closed Tickets", len(df_calc[df_calc["Status"] == "Closed"]))
    col4.metric("Avg Resolution Time", avg_res_str)

    st.write("")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.write("##### Priority Distribution")
        priority_chart = (
            alt.Chart(df_calc)
            .mark_arc(innerRadius=50)
            .encode(
                theta="count():Q",
                color=alt.Color("Priority:N", scale=alt.Scale(domain=["High", "Medium", "Low"], range=["#e74c3c", "#f39c12", "#2ecc71"])),
            )
            .properties(height=300)
        )
        st.altair_chart(priority_chart, use_container_width=True)

    with col_chart2:
        st.write("##### Workload by Assignee & Status")
        assignee_chart = (
            alt.Chart(df_calc)
            .mark_bar()
            .encode(
                x="count():Q",
                y=alt.Y("Assigned To:N", sort="-x"),
                color="Status:N",
            )
            .properties(height=300)
        )
        st.altair_chart(assignee_chart, use_container_width=True)
else:
    st.info("No tickets available to render analytics.")import datetime
import random

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# Show app title and description.
st.set_page_config(page_title="Support tickets", page_icon="🎫", layout="wide")
st.title("🎫 Support tickets")
st.write(
    """
    This app shows how you can build an internal tool in Streamlit. Here, we are 
    implementing a support ticket workflow. The user can create a ticket, edit 
    existing tickets, delete tickets, assign team members, manage issue types, 
    mark completion dates, view statistics, and export CSV reports.
    """
)

# Initialize team members list in session state.
if "team_members" not in st.session_state:
    st.session_state.team_members = [
        "Alice Johnson",
        "Bob Smith",
        "Charlie Brown",
        "Diana Prince",
        "Unassigned",
    ]

# Initialize issue types list in session state.
if "issue_types" not in st.session_state:
    st.session_state.issue_types = [
        "Hardware",
        "Software",
        "Network",
        "Security",
        "Access & Credentials",
        "General IT",
    ]


# --- SIDEBAR: MANAGEMENT PANELS & CSV EXPORT ---
with st.sidebar:
    st.header("⚙️ App Settings")

    # --- CSV REPORT EXPORT SECTION ---
    with st.expander("📥 Export CSV Report", expanded=True):
        st.write("Download filtered or full ticket records.")
        
        status_filter = st.multiselect(
            "Filter Status for Export",
            options=["Open", "In Progress", "Closed"],
            default=["Open", "In Progress", "Closed"],
        )

        if "df" in st.session_state and not st.session_state.df.empty:
            # Filter dataframe based on user selection
            filtered_df_export = st.session_state.df[
                st.session_state.df["Status"].isin(status_filter)
            ]

            # Convert dataframe to CSV byte stream
            csv_data = filtered_df_export.to_csv(index=False).encode("utf-8")

            today_str = datetime.date.today().strftime("%Y-%m-%d")
            st.download_button(
                label="⬇️ Download CSV Report",
                data=csv_data,
                file_name=f"support_tickets_report_{today_str}.csv",
                mime="text/csv",
                type="primary",
                use_container_width=True,
            )
            st.caption(f"Exporting `{len(filtered_df_export)}` records")
        else:
            st.info("No ticket data available to export.")

    # --- TEAM MEMBER MANAGEMENT ---
    with st.expander("👤 Team Management", expanded=False):
        # Form to add a new team member
        with st.form("add_team_member_form", clear_on_submit=True):
            new_member = st.text_input("Add team member")
            add_member_submitted = st.form_submit_button("Add Member")

        if add_member_submitted:
            cleaned_member = new_member.strip()
            if not cleaned_member:
                st.error("Please enter a valid name.")
            elif cleaned_member in st.session_state.team_members:
                st.warning("This team member already exists.")
            else:
                st.session_state.team_members.append(cleaned_member)
                st.success(f"Added **{cleaned_member}**!")
                st.rerun()

        st.divider()

        # Selector to remove an existing team member
        removable_members = [
            m for m in st.session_state.team_members if m != "Unassigned"
        ]

        if removable_members:
            member_to_remove = st.selectbox(
                "Remove team member", options=removable_members
            )
            if st.button("Remove Member", type="secondary"):
                st.session_state.team_members.remove(member_to_remove)

                # Reassign tickets of deleted member to 'Unassigned'
                if "df" in st.session_state and not st.session_state.df.empty:
                    st.session_state.df.loc[
                        st.session_state.df["Assigned To"] == member_to_remove,
                        "Assigned To",
                    ] = "Unassigned"

                st.success(
                    f"Removed **{member_to_remove}**. Tickets reassigned to 'Unassigned'."
                )
                st.rerun()
        else:
            st.info("No custom members to remove.")

    # --- ISSUE TYPE MANAGEMENT ---
    with st.expander("🏷️ Issue Types Management", expanded=False):
        # Form to add a new issue type
        with st.form("add_issue_type_form", clear_on_submit=True):
            new_type = st.text_input("Add issue type")
            add_type_submitted = st.form_submit_button("Add Type")

        if add_type_submitted:
            cleaned_type = new_type.strip()
            if not cleaned_type:
                st.error("Please enter a valid type name.")
            elif cleaned_type in st.session_state.issue_types:
                st.warning("This issue type already exists.")
            else:
                st.session_state.issue_types.append(cleaned_type)
                st.success(f"Added **{cleaned_type}**!")
                st.rerun()

        st.divider()

        # Selector to remove an issue type
        removable_types = [
            t for t in st.session_state.issue_types if t != "General IT"
        ]

        if removable_types:
            type_to_remove = st.selectbox(
                "Remove issue type", options=removable_types
            )
            if st.button("Remove Type", type="secondary"):
                st.session_state.issue_types.remove(type_to_remove)

                # Reset tickets with deleted issue type to 'General IT'
                if "df" in st.session_state and not st.session_state.df.empty:
                    st.session_state.df.loc[
                        st.session_state.df["Issue Type"] == type_to_remove,
                        "Issue Type",
                    ] = "General IT"

                st.success(
                    f"Removed **{type_to_remove}**. Tickets reset to 'General IT'."
                )
                st.rerun()
        else:
            st.info("No custom types to remove.")


# Create a random Pandas dataframe with existing tickets.
if "df" not in st.session_state:

    # Set seed for reproducibility.
    np.random.seed(42)

    # Make up some fake issue descriptions.
    issue_descriptions = [
        "Network connectivity issues in the office",
        "Software application crashing on startup",
        "Printer not responding to print commands",
        "Email server downtime",
        "Data backup failure",
        "Login authentication problems",
        "Website performance degradation",
        "Security vulnerability identified",
        "Hardware malfunction in the server room",
        "Employee unable to access shared files",
        "Database connection failure",
        "Mobile application not syncing data",
        "VoIP phone system issues",
        "VPN connection problems for remote employees",
        "System updates causing compatibility issues",
        "File server running out of storage space",
        "Intrusion detection system alerts",
        "Inventory management system errors",
        "Customer data not loading in CRM",
        "Collaboration tool not sending notifications",
    ]

    # Generate 100 sample tickets with random dates, assignees, types, and completion dates.
    data = []
    for i in range(1100, 1000, -1):
        status = np.random.choice(["Open", "In Progress", "Closed"])
        date_submitted = datetime.date(2023, 6, 1) + datetime.timedelta(
            days=random.randint(0, 120)
        )

        if status == "Closed":
            completed_date = date_submitted + datetime.timedelta(
                days=random.randint(1, 14)
            )
        else:
            completed_date = None

        data.append(
            {
                "ID": f"TICKET-{i}",
                "Issue": np.random.choice(issue_descriptions),
                "Issue Type": np.random.choice(st.session_state.issue_types),
                "Status": status,
                "Priority": np.random.choice(["High", "Medium", "Low"]),
                "Assigned To": np.random.choice(st.session_state.team_members),
                "Date Submitted": date_submitted,
                "Completed Date": completed_date,
            }
        )

    df = pd.DataFrame(data)

    # Save the dataframe in session state.
    st.session_state.df = df


# Show a section to add a new ticket.
st.header("Add a ticket")

with st.form("add_ticket_form"):
    issue = st.text_area("Describe the issue")
    col_a, col_b, col_c = st.columns(3)

    with col_a:
        issue_type = st.selectbox("Issue Type", st.session_state.issue_types)
    with col_b:
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
    with col_c:
        default_assignee_idx = (
            st.session_state.team_members.index("Unassigned")
            if "Unassigned" in st.session_state.team_members
            else 0
        )
        assigned_to = st.selectbox(
            "Assigned To",
            st.session_state.team_members,
            index=default_assignee_idx,
        )

    submitted = st.form_submit_button("Submit")

if submitted:
    recent_ticket_number = (
        int(max(st.session_state.df.ID).split("-")[1])
        if len(st.session_state.df) > 0
        else 1000
    )
    today = datetime.date.today()
    df_new = pd.DataFrame(
        [
            {
                "ID": f"TICKET-{recent_ticket_number+1}",
                "Issue": issue,
                "Issue Type": issue_type,
                "Status": "Open",
                "Priority": priority,
                "Assigned To": assigned_to,
                "Date Submitted": today,
                "Completed Date": None,
            }
        ]
    )

    st.write("Ticket submitted! Here are the ticket details:")
    st.dataframe(df_new, use_container_width=True, hide_index=True)
    st.session_state.df = pd.concat([df_new, st.session_state.df], axis=0).reset_index(
        drop=True
    )

# Show section to view, edit, and delete existing tickets.
st.header("Existing tickets")
st.write(f"Number of tickets: `{len(st.session_state.df)}`")

st.info(
    "Double click cells to edit status, priority, issue type, assignee, or completed date. "
    "Select rows and press Backspace/Delete to remove tickets.",
    icon="✍️",
)

# Show the tickets dataframe with `st.data_editor`.
edited_df = st.data_editor(
    st.session_state.df,
    use_container_width=True,
    hide_index=True,
    num_rows="dynamic",
    column_config={
        "Issue Type": st.column_config.SelectboxColumn(
            "Issue Type",
            help="Category of the ticket issue",
            options=st.session_state.issue_types,
            required=True,
        ),
        "Status": st.column_config.SelectboxColumn(
            "Status",
            help="Ticket status",
            options=["Open", "In Progress", "Closed"],
            required=True,
        ),
        "Priority": st.column_config.SelectboxColumn(
            "Priority",
            help="Priority",
            options=["High", "Medium", "Low"],
            required=True,
        ),
        "Assigned To": st.column_config.SelectboxColumn(
            "Assigned To",
            help="Team member responsible for this ticket",
            options=st.session_state.team_members,
            required=True,
        ),
        "Completed Date": st.column_config.DateColumn(
            "Completed Date",
            help="Date when ticket was closed",
            format="YYYY-MM-DD",
        ),
        "Date Submitted": st.column_config.DateColumn(
            "Date Submitted",
            format="YYYY-MM-DD",
        ),
    },
    disabled=["ID", "Date Submitted"],
)

# Update session state with edits/deletions made inside data_editor
st.session_state.df = edited_df

# Dedicated section to explicitly select and delete a ticket
with st.expander("🗑️ Delete a ticket by ID"):
    ticket_ids = (
        st.session_state.df["ID"].tolist() if not st.session_state.df.empty else []
    )
    if ticket_ids:
        ticket_to_delete = st.selectbox(
            "Select Ticket ID to delete", options=ticket_ids
        )
        if st.button("Delete Selected Ticket", type="primary"):
            st.session_state.df = st.session_state.df[
                st.session_state.df["ID"] != ticket_to_delete
            ].reset_index(drop=True)
            st.success(f"{ticket_to_delete} has been deleted.")
            st.rerun()
    else:
        st.info("No tickets available to delete.")


# Show metrics and charts about tickets.
st.header("Statistics")

col1, col2, col3, col4 = st.columns(4)
num_open_tickets = len(st.session_state.df[st.session_state.df.Status == "Open"])
num_closed_tickets = len(st.session_state.df[st.session_state.df.Status == "Closed"])

col1.metric(label="Open tickets", value=num_open_tickets)
col2.metric(label="Closed tickets", value=num_closed_tickets)
col3.metric(label="First response time", value="5.2 hrs")
col4.metric(label="Avg resolution time", value="16 hrs")

# Show Altair charts using `st.altair_chart`.
st.write("")
st.write("##### Ticket status per month")
if not edited_df.empty:
    status_plot = (
        alt.Chart(edited_df)
        .mark_bar()
        .encode(
            x="month(Date Submitted):O",
            y="count():Q",
            xOffset="Status:N",
            color="Status:N",
        )
        .configure_legend(
            orient="bottom", titleFontSize=14, labelFontSize=14, titlePadding=5
        )
    )
    st.altair_chart(status_plot, use_container_width=True, theme="streamlit")

    col_chart1, col_chart2, col_chart3 = st.columns(3)

    with col_chart1:
        st.write("##### Current ticket priorities")
        priority_plot = (
            alt.Chart(edited_df)
            .mark_arc()
            .encode(theta="count():Q", color="Priority:N")
            .properties(height=300)
            .configure_legend(
                orient="bottom", titleFontSize=14, labelFontSize=14, titlePadding=5
            )
        )
        st.altair_chart(priority_plot, use_container_width=True, theme="streamlit")

    with col_chart2:
        st.write("##### Tickets by Issue Type")
        type_plot = (
            alt.Chart(edited_df)
            .mark_bar()
            .encode(
                x="count():Q",
                y=alt.Y("Issue Type:N", sort="-x"),
                color="Issue Type:N",
            )
            .properties(height=300)
            .configure_legend(
                orient="bottom", titleFontSize=14, labelFontSize=14, titlePadding=5
            )
        )
        st.altair_chart(type_plot, use_container_width=True, theme="streamlit")

    with col_chart3:
        st.write("##### Tickets assigned per member")
        assignee_plot = (
            alt.Chart(edited_df)
            .mark_bar()
            .encode(
                x="count():Q",
                y=alt.Y("Assigned To:N", sort="-x"),
                color="Status:N",
            )
            .properties(height=300)
            .configure_legend(
                orient="bottom", titleFontSize=14, labelFontSize=14, titlePadding=5
            )
        )
        st.altair_chart(assignee_plot, use_container_width=True, theme="streamlit")
else:
    st.info("No ticket data available to render charts.")
