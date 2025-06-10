# 🎯 IPL Betting Tracker

A modern, robust Streamlit web app to manage, track, and analyze IPL betting activity across multiple accounts.  
Built for transparency, accountability, and ease of use.

---

## 🚀 Features

- **Multi-Account Management:**  
  Track balances, remarks, and transactions for any number of accounts.

- **Bet Placement:**  
  Place bets on IPL matches, assign accounts to teams, and auto-calculate bet amounts based on odds.

- **Active Bets & Results:**  
  View all active bets, apply results (win/loss/cashout), and update balances accordingly.

- **Bet History:**  
  Browse detailed history of all completed bets, including account-level breakdowns.

- **Settings & Data Management:**  
  - Set minimum transfer and default betting values.
  - Backup and restore your database.
  - Reset all data with a single click.

- **Beautiful UI:**  
  Responsive, clean interface with custom CSS for a professional look.

---

## 🛠️ Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/ipl-betting-tracker.git
   cd ipl-betting-tracker
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the app:**
   ```bash
   streamlit run stake.py
   ```

---

## 📂 Project Structure

```
.
├── stake.py         # Main Streamlit app
├── database.py      # Database logic (SQLite)
├── betting_tracker.log  # Log file (auto-generated)
├── data/            # SQLite database and backups
├── requirements.txt # Python dependencies
└── readme.md        # This file
```

---

## ⚡ Usage

- **Accounts:**  
  Add or edit accounts in the sidebar. Each account tracks its own balance and remarks.

- **Placing Bets:**  
  Fill out the form, select teams, odds, and assign accounts. The app checks for sufficient balances before placing bets.

- **Results:**  
  For each active bet, select the result type and apply it. Balances update automatically.

- **Backups & Reset:**  
  Use the sidebar to create database backups or reset all data (be careful—reset is irreversible!).

---

## 📝 Requirements

- Python 3.8+
- [Streamlit](https://streamlit.io/)
- pandas

See `requirements.txt` for the full list.

---

## 🛡️ Disclaimer

This project is for educational and personal tracking purposes only.  
**Gambling can be addictive and is illegal in many jurisdictions. Use responsibly and at your own risk. Moreover, many Gambling website does not appreciate multi-accounts, Be Careful**

---

## 📧 Contact

For issues, suggestions, or contributions, open an [issue](https://github.com/yourusername/ipl-betting-tracker/issues) or contact the maintainer.

---

**Enjoy tracking your IPL bets responsibly!**