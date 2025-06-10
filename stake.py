import streamlit as st
import pandas as pd
from datetime import datetime, date
import math
import os
from database import Database
import logging
from typing import Dict, List, Optional, Union

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('betting_tracker.log'),
        logging.StreamHandler()
    ]
)

# Constants
@st.cache_data
def get_ipl_teams():
    return [
        "Chennai Super Kings", "Mumbai Indians", "Royal Challengers Bangalore",
        "Kolkata Knight Riders", "Delhi Capitals", "Punjab Kings",
        "Rajasthan Royals", "Sunrisers Hyderabad", "Gujarat Titans",
        "Lucknow Super Giants"
    ]
IPL_TEAMS = get_ipl_teams()

# Page Configuration
st.set_page_config(
    page_title="IPL Betting Tracker",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton>button {
        width: 100%;
        margin: 0.5rem 0;
    }
    .stTextArea>div>div>textarea {
        font-size: 14px;
    }
    .stMarkdown {
        font-size: 14px;
    }
    .stAlert {
        padding: 1rem;
    }
    .css-1d391kg {
        padding: 1rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        color: #000000;
    }
    .metric-card h2, .metric-card h4 {
        color: #000000;
    }
    .team-card {
        background-color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border: 1px solid #e0e0e0;
        color: #000000;
    }
    .team-card h3, .team-card h4, .team-card p {
        color: #000000;
    }
    .account-card {
        background-color: #f8f9fa;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border: 1px solid #e0e0e0;
        color: #000000;
    }
    .account-card h4, .account-card p {
        color: #000000;
    }
    /* Ensure sidebar text is visible */
    .css-1d391kg, .css-1d391kg p, .css-1d391kg h1, .css-1d391kg h2, .css-1d391kg h3, .css-1d391kg h4 {
        color: #000000;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize Database
@st.cache_resource
def get_database():
    return Database()

db = get_database()

# Initialize Session State
def init_session_state():
    """Initialize session state variables."""
    if 'num_accounts' not in st.session_state:
        st.session_state.num_accounts = 2
    
    if 'account_data' not in st.session_state:
        st.session_state.account_data = db.get_accounts()
    
    if 'active_bets' not in st.session_state:
        st.session_state.active_bets = db.get_active_bets()
    
    if 'settings' not in st.session_state:
        settings = db.get_settings()
        # Ensure default values are set
        if 'min_transfer' not in settings:
            settings['min_transfer'] = 250.0
        if 'default_betting_value' not in settings:
            settings['default_betting_value'] = 2100.0
        st.session_state.settings = settings
    
    if 'form_state' not in st.session_state:
        st.session_state.form_state = {
            'selected_team1': 'Chennai Super Kings',
            'selected_team2': 'Mumbai Indians',
            'odds1': 2.0,
            'odds2': 2.0,
            'betting_value': st.session_state.settings.get('default_betting_value', 2100.0),
            'match_date': date.today(),
            'match_time': '3:30 PM',
            'show_accurate': False
        }

init_session_state()

# Helper Functions
def format_currency(amount: float) -> str:
    """Format amount as currency."""
    return f"₹{amount:,.2f}"

def calculate_bet_amount(betting_value: float, odds: float, show_accurate: bool) -> float:
    """Calculate bet amount based on betting value and odds."""
    amount = betting_value / odds
    return amount if show_accurate else math.ceil(amount)

def update_account_balance(account_id: int, amount: float, operation: str = 'add') -> None:
    """Update account balance."""
    try:
        account_data = st.session_state.account_data
        account_row = account_data[account_data['account_id'] == account_id]
        if account_row.empty:
            logging.error(f"Account {account_id} not found.")
            raise ValueError(f"Account {account_id} not found.")
        idx = account_row.index[0]
        if operation == 'add':
            account_data.loc[idx, 'balance'] += amount
        else:
            if account_data.loc[idx, 'balance'] < amount:
                logging.error(f"Insufficient balance in account {account_id}.")
                raise ValueError(f"Insufficient balance in account {account_id}.")
            account_data.loc[idx, 'balance'] -= amount
        db.save_account(account_data.iloc[idx].to_dict())
    except Exception as e:
        logging.error(f"Error updating account balance: {str(e)}")
        raise

# Sidebar
with st.sidebar:
    st.title("🎯 Dashboard")
    
    # Quick Stats
    st.markdown("### 📊 Quick Stats")
    total_balance = st.session_state.account_data['balance'].sum()
    total_accounts = len(st.session_state.account_data)
    
    st.markdown(f"""
        <div class="metric-card">
            <h4>Total Balance</h4>
            <h2>{format_currency(total_balance)}</h2>
        </div>
        <div class="metric-card">
            <h4>Active Accounts</h4>
            <h2>{total_accounts}</h2>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Account Management
    st.markdown("### 👥 Account Management")
    num_accounts = st.number_input(
        "Number of Accounts",
        min_value=1,
        value=st.session_state.num_accounts,
        step=1,
        help="Set the number of accounts you want to manage"
    )
    
    # Advanced Settings
    with st.expander("⚙️ Advanced Settings", expanded=False):
        st.markdown("### Transfer Settings")
        min_transfer = st.number_input(
            "Minimum Transfer Amount",
            min_value=100.0,
            max_value=1000.0,
            value=float(st.session_state.settings['min_transfer']),
            step=50.0,
            help="Set the minimum amount that can be transferred between accounts"
        )
        
        default_betting_value = st.number_input(
            "Default Betting Value",
            min_value=100.0,
            max_value=10000.0,
            value=float(st.session_state.settings['default_betting_value']),
            step=100.0,
            help="Set the default betting value for new bets"
        )
        
        if st.button("💾 Save Settings"):
            try:
                db.save_settings({
                    'min_transfer': min_transfer,
                    'default_betting_value': default_betting_value
                })
                st.session_state.settings = db.get_settings()
                st.success("Settings updated successfully!")
            except Exception as e:
                st.error(f"Error saving settings: {str(e)}")
    
    # Data Management
    with st.expander("💾 Data Management", expanded=False):
        st.markdown("### Data Management")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📦 Create Backup"):
                try:
                    backup_path = db.backup_database()
                    st.success(f"Backup created successfully at {backup_path}!")
                except Exception as e:
                    st.error(f"Error creating backup: {str(e)}")
        
        with col2:
            reset_confirmed = st.checkbox("I understand this will completely wipe all data")
            if st.button("🔄 Reset Data", disabled=not reset_confirmed):
                try:
                    if db.reset_database():
                        # Clear session state
                        for key in list(st.session_state.keys()):
                            del st.session_state[key]
                        init_session_state()
                        st.success("All data has been reset successfully!")
                        st.experimental_rerun()
                except Exception as e:
                    st.error(f"Error resetting data: {str(e)}")
    
    st.markdown("---")
    
    # Account Balances
    st.markdown("### 💰 Account Balances")
    for i in range(1, num_accounts + 1):
        with st.expander(f"Account {i}", expanded=False):
            account_data = st.session_state.account_data
            account = account_data[account_data['account_id'] == i]
            
            if not account.empty:
                current_balance = account.iloc[0]['balance']
                current_remarks = account.iloc[0]['remarks']
            else:
                current_balance = 0.0
                current_remarks = ''
            
            balance = st.number_input(
                "Balance",
                min_value=0.0,
                value=current_balance,
                step=100.0,
                format="%.2f",
                key=f"sidebar_balance_{i}"  # Unique key
            )
            
            remarks = st.text_area(
                "Remarks",
                value=current_remarks,
                key=f"sidebar_remarks_{i}"  # Unique key
            )
            
            if st.button("💾 Save", key=f"sidebar_save_account_{i}"):
                try:
                    db.save_account({
                        'account_id': i,
                        'name': f'Account {i}',
                        'balance': balance,
                        'remarks': remarks
                    })
                    st.session_state.account_data = db.get_accounts()
                    st.success(f"Account {i} updated successfully!")
                except Exception as e:
                    st.error(f"Error saving account: {str(e)}")

# Main Content
st.title("🎲 Place New Bet")

# Betting Form
with st.form("betting_form"):
    st.markdown("### Betting Details")
    
    # Betting Value
    betting_value = st.number_input(
        "Betting Value",
        min_value=100.0,
        max_value=10000.0,
        value=float(st.session_state.form_state['betting_value']),
        step=100.0,
        help="Enter the total betting value for both teams"
    )
    
    show_accurate = st.checkbox(
        "Show Accurate Calculations",
        value=st.session_state.form_state['show_accurate'],
        help="Toggle between rounded and exact calculations"
    )
    
    # Team Selection
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### Team 1")
        team1 = st.selectbox(
            "Select Team",
            options=IPL_TEAMS,
            index=IPL_TEAMS.index(st.session_state.form_state['selected_team1']),
            key="form_team1"
        )
        
        odds1 = st.number_input(
            "Odds",
            min_value=1.0,
            max_value=100.0,
            value=float(st.session_state.form_state['odds1']),
            step=0.01,
            format="%.2f",
            key="form_odds1"
        )
        
        bet_amount1 = calculate_bet_amount(betting_value, odds1, show_accurate)
        st.markdown(f"""
            <div class="team-card">
                <h4>Bet Amount</h4>
                <h3>{format_currency(bet_amount1)}</h3>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("#### Selected Accounts")
        team1_accounts = []
        for i in range(1, num_accounts + 1):
            if st.checkbox(f"Account {i}", key=f"form_team1_acc_{i}"):
                team1_accounts.append(i)

    with col2:
        st.markdown("#### Team 2")
        team2 = st.selectbox(
            "Select Team",
            options=IPL_TEAMS,
            index=IPL_TEAMS.index(st.session_state.form_state['selected_team2']),
            key="form_team2"
        )
        
        odds2 = st.number_input(
            "Odds",
            min_value=1.0,
            max_value=100.0,
            value=float(st.session_state.form_state['odds2']),
            step=0.01,
            format="%.2f",
            key="form_odds2"
        )
        
        bet_amount2 = calculate_bet_amount(betting_value, odds2, show_accurate)
        st.markdown(f"""
            <div class="team-card">
                <h4>Bet Amount</h4>
                <h3>{format_currency(bet_amount2)}</h3>
            </div>
        """, unsafe_allow_html=True)
        
        st.markdown("#### Selected Accounts")
        team2_accounts = []
        for i in range(1, num_accounts + 1):
            disabled = i in team1_accounts
            if st.checkbox(f"Account {i}", key=f"form_team2_acc_{i}", disabled=disabled):
                team2_accounts.append(i)

    # Match Details
    st.markdown("### 📅 Match Details")
    match_col1, match_col2 = st.columns(2)
    
    with match_col1:
        match_date = st.date_input(
            "Match Date",
            value=st.session_state.form_state['match_date'],
            key="match_date"
        )
    
    with match_col2:
        match_time = st.selectbox(
            "Match Time",
            options=["3:30 PM", "7:30 PM"],
            index=["3:30 PM", "7:30 PM"].index(st.session_state.form_state['match_time']),
            key="match_time"
        )
    
    # Submit Button
    submitted = st.form_submit_button("➕ Place Bet")
    
    if submitted:
        # Validate selections
        if not team1_accounts and not team2_accounts:
            st.error("Please select accounts for both teams.")
        elif not team1_accounts:
            st.error("Please select accounts for Team 1.")
        elif not team2_accounts:
            st.error("Please select accounts for Team 2.")
        elif len(team1_accounts) != len(team2_accounts):
            st.error(f"Unequal number of accounts selected: Team 1 ({len(team1_accounts)}) vs Team 2 ({len(team2_accounts)})")
        else:
            try:
                # Validate balances
                insufficient_balance = False
                insufficient_accounts = []
                
                for acc in team1_accounts:
                    account = st.session_state.account_data[st.session_state.account_data['account_id'] == acc].iloc[0]
                    if account['balance'] < bet_amount1:
                        insufficient_balance = True
                        insufficient_accounts.append((acc, bet_amount1, "Team 1"))
                
                for acc in team2_accounts:
                    account = st.session_state.account_data[st.session_state.account_data['account_id'] == acc].iloc[0]
                    if account['balance'] < bet_amount2:
                        insufficient_balance = True
                        insufficient_accounts.append((acc, bet_amount2, "Team 2"))
                
                if insufficient_balance:
                    st.error("Insufficient balance in some accounts:")
                    for acc, required, team in insufficient_accounts:
                        current = st.session_state.account_data[st.session_state.account_data['account_id'] == acc].iloc[0]['balance']
                        st.error(f"Account {acc} ({team}): Current: {format_currency(current)}, Required: {format_currency(required)}")
                else:
                    # Create bet
                    bet_data = {
                        'team1': team1,
                        'team2': team2,
                        'team1_odds': odds1,  # Use consistent naming
                        'team2_odds': odds2,
                        'bet_amount1': bet_amount1,
                        'bet_amount2': bet_amount2,
                        'betting_value': betting_value,
                        'match_date': match_date.strftime('%Y-%m-%d'),
                        'match_time': match_time,
                        'team1_accounts': team1_accounts,
                        'team2_accounts': team2_accounts
                    }
                    
                    # Save bet
                    bet_id = db.create_bet(bet_data)
                    
                    # Update account balances
                    for acc in team1_accounts:
                        update_account_balance(acc, bet_amount1, 'subtract')
                    
                    for acc in team2_accounts:
                        update_account_balance(acc, bet_amount2, 'subtract')
                    
                    # Update session state
                    st.session_state.active_bets = db.get_active_bets()
                    st.session_state.account_data = db.get_accounts()
                    
                    st.success("Bet placed successfully!")
                    
                    # Show deduction summary
                    st.info("Amounts deducted from accounts:")
                    for acc in team1_accounts:
                        st.write(f"Account {acc} ({team1}): {format_currency(bet_amount1)}")
                    for acc in team2_accounts:
                        st.write(f"Account {acc} ({team2}): {format_currency(bet_amount2)}")
                    
                    # Clear form state
                    st.session_state.form_state = {
                        'selected_team1': 'Chennai Super Kings',
                        'selected_team2': 'Mumbai Indians',
                        'odds1': 2.0,
                        'odds2': 2.0,
                        'betting_value': st.session_state.settings['default_betting_value'],
                        'match_date': date.today(),
                        'match_time': '3:30 PM',
                        'show_accurate': False
                    }
                    
                    st.experimental_rerun()
            except Exception as e:
                st.error(f"Error placing bet: {str(e)}")

# Active Bets
st.markdown("### 📊 Active Bets")
if not st.session_state.active_bets.empty:
    for _, bet in st.session_state.active_bets.iterrows():
        with st.expander(f"Bet {bet['bet_id']} - {bet['team1']} vs {bet['team2']}", expanded=False):
            st.markdown(f"""
                <div class="team-card">
                    <h4>Match Details</h4>
                    <p>📅 {bet['match_date']} | 🕒 {bet['match_time']}</p>
                    <p>⏰ Added: {bet['created_at']}</p>
                </div>
            """, unsafe_allow_html=True)
            
            bet_col1, bet_col2 = st.columns(2)
            
            with bet_col1:
                st.markdown(f"""
                    <div class="team-card">
                        <h4>Team 1: {bet['team1']}</h4>
                        <p>Odds: {bet['team1_odds']:.2f}</p>
                        <p>Bet Amount: {format_currency(bet['betting_value'] / bet['team1_odds'])}</p>
                    </div>
                """, unsafe_allow_html=True)
            
            with bet_col2:
                st.markdown(f"""
                    <div class="team-card">
                        <h4>Team 2: {bet['team2']}</h4>
                        <p>Odds: {bet['team2_odds']:.2f}</p>
                        <p>Bet Amount: {format_currency(bet['betting_value'] / bet['team2_odds'])}</p>
                    </div>
                """, unsafe_allow_html=True)
            
            # Result Menu
            st.markdown("### Result")
            result_type = st.selectbox(
                "Select Result Type",
                ["Select Result", "Win", "Loss", "Cashout"],
                key=f"result_type_{bet['bet_id']}"
            )
            
            if result_type == "Win":
                winning_team = st.selectbox(
                    "Select Winning Team",
                    [bet['team1'], bet['team2']],
                    key=f"winning_team_{bet['bet_id']}"
                )
                
                if st.button("Apply Win", key=f"apply_win_{bet['bet_id']}"):
                    try:
                        # Get bet details
                        bet_details = db.get_bet_details(bet['bet_id'])
                        
                        # Calculate profits
                        winning_accounts = []
                        if winning_team == bet['team1']:
                            for acc in bet_details['accounts']:
                                if acc['team_number'] == 1:
                                    profit = acc['bet_amount'] * bet['team1_odds']
                                    update_account_balance(acc['account_id'], profit)
                                    winning_accounts.append({
                                        'account_id': acc['account_id'],
                                        'profit': profit
                                    })
                        else:
                            for acc in bet_details['accounts']:
                                if acc['team_number'] == 2:
                                    profit = acc['bet_amount'] * bet['team2_odds']
                                    update_account_balance(acc['account_id'], profit)
                                    winning_accounts.append({
                                        'account_id': acc['account_id'],
                                        'profit': profit
                                    })
                        
                        # Save result
                        db.save_result({
                            'bet_id': bet['bet_id'],
                            'winning_team': 1 if winning_team == bet['team1'] else 2,
                            'result_type': 'win',
                            'winning_accounts': winning_accounts
                        })
                        
                        # Update session state
                        st.session_state.active_bets = db.get_active_bets()
                        st.session_state.account_data = db.get_accounts()
                        
                        st.success("Win applied successfully!")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error applying win: {str(e)}")
            
            elif result_type == "Loss":
                if st.button("Apply Loss", key=f"apply_loss_{bet['bet_id']}"):
                    try:
                        # Save result
                        db.save_result({
                            'bet_id': bet['bet_id'],
                            'winning_team': 0,
                            'result_type': 'loss'
                        })
                        
                        # Update session state
                        st.session_state.active_bets = db.get_active_bets()
                        
                        st.success("Loss applied successfully!")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error applying loss: {str(e)}")
            
            elif result_type == "Cashout":
                st.markdown("### Cashout Details")
                
                # Get bet details
                bet_details = db.get_bet_details(bet['bet_id'])
                
                cashout_details = []
                for acc in bet_details['accounts']:
                    with st.expander(f"Account {acc['account_id']}", expanded=False):
                        is_cashed_out = st.checkbox("Cashed Out", key=f"cashout_{bet['bet_id']}_{acc['account_id']}")
                        if is_cashed_out:
                            cashout_amount = st.number_input(
                                "Cashout Amount",
                                min_value=0.0,
                                value=0.0,
                                step=100.0,
                                key=f"cashout_amount_{bet['bet_id']}_{acc['account_id']}"
                            )
                            if st.button("Apply Cashout", key=f"apply_cashout_{bet['bet_id']}_{acc['account_id']}"):
                                try:
                                    update_account_balance(acc['account_id'], cashout_amount)
                                    cashout_details.append({
                                        'account_id': acc['account_id'],
                                        'amount': cashout_amount
                                    })
                                    st.success(f"Cashout amount added to Account {acc['account_id']}")
                                except Exception as e:
                                    st.error(f"Error applying cashout: {str(e)}")
                
                if st.button("Complete Cashout", key=f"complete_cashout_{bet['bet_id']}"):
                    try:
                        # Save result
                        db.save_result({
                            'bet_id': bet['bet_id'],
                            'winning_team': 0,
                            'result_type': 'cashout',
                            'cashout_details': cashout_details
                        })
                        
                        # Update session state
                        st.session_state.active_bets = db.get_active_bets()
                        st.session_state.account_data = db.get_accounts()
                        
                        st.success("Cashout completed successfully!")
                        st.experimental_rerun()
                    except Exception as e:
                        st.error(f"Error completing cashout: {str(e)}")
else:
    st.info("No active bets. Add a bet using the form above.")

# Bet History
st.markdown("### 📜 Bet History")
try:
    history = db.get_bet_history()
    if not history.empty:
        for _, bet in history.iterrows():
            with st.expander(f"Bet {bet['bet_id']} - {bet['team1']} vs {bet['team2']}", expanded=False):
                st.markdown(f"""
                    <div class="team-card">
                        <h4>Match Details</h4>
                        <p>📅 {bet['match_date']} | 🕒 {bet['match_time']}</p>
                        <p>⏰ Added: {bet['created_at']}</p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Result details
                st.markdown(f"""
                    <div class="team-card">
                        <h4>Result: {bet['result_type'].title() if bet['result_type'] else 'N/A'}</h4>
                        {f"<p>Winning Team: {bet['winning_team']}</p>" if bet.get('winning_team') else ""}
                        {f"<p>Profit: {format_currency(bet['profit_amount'])}</p>" if bet.get('profit_amount') else ""}
                        {f"<p>Loss: {format_currency(bet['loss_amount'])}</p>" if bet.get('loss_amount') else ""}
                    </div>
                """, unsafe_allow_html=True)
                
                # Account details
                st.markdown("### Account Details")
                for acc in bet['accounts']:
                    st.markdown(f"""
                        <div class="account-card">
                            <h4>Account {acc['account_id']}</h4>
                            <p>Team: {bet['team1'] if acc['team_number'] == 1 else bet['team2']}</p>
                            <p>Bet Amount: {format_currency(acc['bet_amount'])}</p>
                        </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("No bet history available.")
except Exception as e:
    logging.error(f"Error loading bet history: {str(e)}")
    st.error(f"Error loading bet history: {str(e)}")



