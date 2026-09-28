import datetime
import random

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

# Show app title and description.
st.set_page_config(page_title="Support tickets", page_icon="🎫")
st.title("🎫 Support tickets")
st.write(
    """
    This app shows how you can build an internal tool in Streamlit. Here, we are 
    implementing a support ticket workflow. The user can create a ticket, edit 
    existing tickets, delete tickets, assign team members, mark completion dates, and view statistics.
    """
)

# List of team members for ticket assignment
TEAM_MEMBERS = ["Alice Johnson", "Bob Smith", "Charlie Brown", "Diana Prince", "Unassigned"]

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

    # Generate 100 sample tickets with random dates, assignees, and completion dates.
    data = []
    for i in range(1100, 1000, -1):
        status = np.random.choice(["Open", "In Progress", "Closed"])
        date_submitted = datetime.date(2023, 6, 1) + datetime.timedelta(days=random.randint(0, 120))
        
        # If status is Closed, assign a completed date after the submitted date
        if status == "Closed":
            completed_date = date_submitted + datetime.timedelta(days=random.randint(1, 14))
        else:
            completed_date = None

        data.append(
            {
                "ID": f"TICKET-{i}",
                "Issue": np.random.choice(issue_descriptions),
                "Status": status,
                "Priority": np.random.choice(["High", "Medium", "Low"]),
                "Assigned To": np.random.choice(TEAM_MEMBERS),
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
    col_a, col_b = st.columns(2)
    with col_a:
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
    with col_b:
        assigned_to = st.selectbox("Assigned To", TEAM_MEMBERS, index=TEAM_MEMBERS.index("Unassigned"))
    
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
    st.session_state.df = pd.concat([df_new, st.session_state.df], axis=0).reset_index(drop=True)

# Show section to view, edit, and delete existing tickets.
st.header("Existing tickets")
st.write(f"Number of tickets: `{len(st.session_state.df)}`")

st.info(
    "Double click cells to edit status, priority, assignee, or completed date. "
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
            options=TEAM_MEMBERS,
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
    ticket_ids = st.session_state.df["ID"].tolist() if not st.session_state.df.empty else []
    if ticket_ids:
        ticket_to_delete = st.selectbox("Select Ticket ID to delete", options=ticket_ids)
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

    col_chart1, col_chart2 = st.columns(2)

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
        st.write("##### Tickets assigned per team member")
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
