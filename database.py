import sqlite3
import pandas as pd
from datetime import datetime
import os
import json
from pathlib import Path
import shutil
import threading
from typing import Dict, List, Optional, Union
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('betting_tracker.log'),
        logging.StreamHandler()
    ]
)

class Database:
    def __init__(self, db_path: str = "data/betting.db"):
        """Initialize database with proper error handling and logging."""
        self.db_path = db_path
        self._local = threading.local()
        self._setup_database()
        logging.info(f"Database initialized at {db_path}")

    def _setup_database(self) -> None:
        """Set up database directory and initial connection."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            conn = sqlite3.connect(self.db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("PRAGMA foreign_keys = ON")
            # Only CREATE TABLE IF NOT EXISTS, do NOT drop tables!
            cursor.executescript('''
                -- Accounts table
                CREATE TABLE IF NOT EXISTS accounts (
                    account_id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    balance DECIMAL(10,2) NOT NULL DEFAULT 0.00,
                    remarks TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1
                );

                -- Matches table
                CREATE TABLE IF NOT EXISTS matches (
                    match_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    team1 TEXT NOT NULL,
                    team2 TEXT NOT NULL,
                    match_date DATE NOT NULL,
                    match_time TEXT NOT NULL,
                    status TEXT DEFAULT 'upcoming',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Bets table
                CREATE TABLE IF NOT EXISTS bets (
                    bet_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    match_id INTEGER NOT NULL,
                    team1_odds DECIMAL(5,2) NOT NULL,
                    team2_odds DECIMAL(5,2) NOT NULL,
                    betting_value DECIMAL(10,2) NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (match_id) REFERENCES matches(match_id) ON DELETE CASCADE
                );

                -- Bet accounts table
                CREATE TABLE IF NOT EXISTS bet_accounts (
                    bet_id INTEGER NOT NULL,
                    account_id INTEGER NOT NULL,
                    team_number INTEGER NOT NULL CHECK (team_number IN (1, 2)),
                    bet_amount DECIMAL(10,2) NOT NULL,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (bet_id, account_id),
                    FOREIGN KEY (bet_id) REFERENCES bets(bet_id) ON DELETE CASCADE,
                    FOREIGN KEY (account_id) REFERENCES accounts(account_id) ON DELETE CASCADE
                );

                -- Results table
                CREATE TABLE IF NOT EXISTS results (
                    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bet_id INTEGER NOT NULL,
                    winning_team INTEGER, -- allow NULL for loss/cashout
                    result_type TEXT NOT NULL,
                    profit_amount DECIMAL(10,2),
                    loss_amount DECIMAL(10,2),
                    cashout_details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bet_id) REFERENCES bets(bet_id) ON DELETE CASCADE
                );

                -- Settings table
                CREATE TABLE IF NOT EXISTS settings (
                    setting_id INTEGER PRIMARY KEY CHECK (setting_id = 1),
                    min_transfer DECIMAL(10,2) NOT NULL DEFAULT 250.00,
                    default_betting_value DECIMAL(10,2) NOT NULL DEFAULT 2100.00,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- Indexes
                CREATE INDEX IF NOT EXISTS idx_matches_date ON matches(match_date);
                CREATE INDEX IF NOT EXISTS idx_bets_match ON bets(match_id);
                CREATE INDEX IF NOT EXISTS idx_bet_accounts_bet ON bet_accounts(bet_id);
                CREATE INDEX IF NOT EXISTS idx_bet_accounts_account ON bet_accounts(account_id);
                CREATE INDEX IF NOT EXISTS idx_results_bet ON results(bet_id);
            ''')
            cursor.execute("""
                INSERT OR IGNORE INTO settings (setting_id, min_transfer, default_betting_value)
                VALUES (1, 250.00, 2100.00)
            """)
            conn.commit()
            conn.close()
            logging.info("Database tables and indexes created successfully")
        except Exception as e:
            logging.error(f"Error setting up database: {str(e)}")
            raise

    def _get_connection(self) -> tuple:
        """Get a thread-local database connection with proper error handling."""
        try:
            if not hasattr(self._local, 'conn'):
                self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
                self._local.conn.row_factory = sqlite3.Row
                self._local.cursor = self._local.conn.cursor()
                self._local.cursor.execute("PRAGMA foreign_keys = ON")
            return self._local.conn, self._local.cursor
        except Exception as e:
            logging.error(f"Error getting database connection: {str(e)}")
            raise

    def get_accounts(self) -> pd.DataFrame:
        """Get all active accounts."""
        try:
            conn, _ = self._get_connection()
            return pd.read_sql_query(
                "SELECT * FROM accounts WHERE is_active = 1 ORDER BY account_id",
                conn
            )
        except Exception as e:
            logging.error(f"Error getting accounts: {str(e)}")
            raise

    def save_account(self, account_data: Dict) -> None:
        """Save or update an account with proper validation."""
        try:
            conn, cursor = self._get_connection()
            cursor.execute("""
                INSERT OR REPLACE INTO accounts 
                (account_id, name, balance, remarks, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
            """, (
                account_data['account_id'],
                account_data.get('name', f'Account {account_data["account_id"]}'),
                account_data['balance'],
                account_data.get('remarks', '')
            ))
            conn.commit()
            logging.info(f"Account {account_data['account_id']} saved successfully")
        except Exception as e:
            conn.rollback()
            logging.error(f"Error saving account: {str(e)}")
            raise

    def create_match(self, match_data: Dict) -> int:
        """Create a new match and return its ID."""
        try:
            conn, cursor = self._get_connection()
            cursor.execute("""
                INSERT INTO matches (team1, team2, match_date, match_time)
                VALUES (?, ?, ?, ?)
            """, (
                match_data['team1'],
                match_data['team2'],
                match_data['match_date'],
                match_data['match_time']
            ))
            match_id = cursor.lastrowid
            conn.commit()
            logging.info(f"Match created with ID: {match_id}")
            return match_id
        except Exception as e:
            conn.rollback()
            logging.error(f"Error creating match: {str(e)}")
            raise

    def create_bet(self, bet_data: Dict) -> int:
        """Create a new bet with proper transaction handling."""
        try:
            conn, cursor = self._get_connection()
            cursor.execute("BEGIN TRANSACTION")
            match_id = bet_data.get('match_id')
            if not match_id:
                cursor.execute("""
                    INSERT INTO matches (team1, team2, match_date, match_time)
                    VALUES (?, ?, ?, ?)
                """, (
                    bet_data['team1'],
                    bet_data['team2'],
                    bet_data['match_date'],
                    bet_data['match_time']
                ))
                match_id = cursor.lastrowid
            cursor.execute("""
                INSERT INTO bets (match_id, team1_odds, team2_odds, betting_value)
                VALUES (?, ?, ?, ?)
            """, (
                match_id,
                bet_data['team1_odds'],
                bet_data['team2_odds'],
                bet_data['betting_value']
            ))
            bet_id = cursor.lastrowid
            for acc in bet_data['team1_accounts']:
                cursor.execute("""
                    INSERT INTO bet_accounts (bet_id, account_id, team_number, bet_amount)
                    VALUES (?, ?, 1, ?)
                """, (bet_id, acc, bet_data['bet_amount1']))
            for acc in bet_data['team2_accounts']:
                cursor.execute("""
                    INSERT INTO bet_accounts (bet_id, account_id, team_number, bet_amount)
                    VALUES (?, ?, 2, ?)
                """, (bet_id, acc, bet_data['bet_amount2']))
            conn.commit()
            logging.info(f"Bet created with ID: {bet_id}")
            return bet_id
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            logging.error(f"Error creating bet: {str(e)}")
            raise

    def get_active_bets(self) -> pd.DataFrame:
        """Get all active bets with related information."""
        try:
            conn, _ = self._get_connection()
            return pd.read_sql_query("""
                SELECT 
                    b.bet_id,
                    m.team1,
                    m.team2,
                    m.match_date,
                    m.match_time,
                    b.team1_odds,
                    b.team2_odds,
                    b.betting_value,
                    b.created_at
                FROM bets b
                JOIN matches m ON b.match_id = m.match_id
                WHERE b.status = 'active'
                ORDER BY m.match_date, m.match_time
            """, conn)
        except Exception as e:
            logging.error(f"Error getting active bets: {str(e)}")
            raise

    def get_bet_details(self, bet_id: int) -> Dict:
        """Get detailed information about a specific bet."""
        try:
            conn, cursor = self._get_connection()
            cursor.execute("""
                SELECT 
                    b.*,
                    m.team1,
                    m.team2,
                    m.match_date,
                    m.match_time
                FROM bets b
                JOIN matches m ON b.match_id = m.match_id
                WHERE b.bet_id = ?
            """, (bet_id,))
            bet_info = cursor.fetchone()
            if not bet_info:
                raise ValueError(f"Bet {bet_id} not found")
            cursor.execute("""
                SELECT 
                    ba.team_number,
                    ba.bet_amount,
                    a.account_id,
                    a.name,
                    a.balance
                FROM bet_accounts ba
                JOIN accounts a ON ba.account_id = a.account_id
                WHERE ba.bet_id = ?
                ORDER BY ba.team_number, a.account_id
            """, (bet_id,))
            accounts = [dict(row) for row in cursor.fetchall()]
            return {
                'bet_id': bet_id,
                'team1': bet_info['team1'],
                'team2': bet_info['team2'],
                'match_date': bet_info['match_date'],
                'match_time': bet_info['match_time'],
                'team1_odds': bet_info['team1_odds'],
                'team2_odds': bet_info['team2_odds'],
                'betting_value': bet_info['betting_value'],
                'accounts': accounts
            }
        except Exception as e:
            logging.error(f"Error getting bet details: {str(e)}")
            raise

    def save_result(self, result_data: Dict) -> None:
        """Save bet result with proper transaction handling."""
        try:
            conn, cursor = self._get_connection()
            cursor.execute("BEGIN TRANSACTION")
            cursor.execute("""
                UPDATE bets 
                SET status = 'completed', updated_at = CURRENT_TIMESTAMP
                WHERE bet_id = ?
            """, (result_data['bet_id'],))
            cursor.execute("""
                INSERT INTO results (
                    bet_id, winning_team, result_type,
                    profit_amount, loss_amount, cashout_details
                )
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                result_data['bet_id'],
                result_data.get('winning_team'),  # allow None
                result_data['result_type'],
                result_data.get('profit_amount'),
                result_data.get('loss_amount'),
                json.dumps(result_data.get('cashout_details', []))
            ))
            if result_data['result_type'] == 'win':
                for acc in result_data['winning_accounts']:
                    cursor.execute("""
                        UPDATE accounts 
                        SET balance = balance + ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE account_id = ?
                    """, (acc['profit'], acc['account_id']))
            conn.commit()
            logging.info(f"Result saved for bet {result_data['bet_id']}")
        except Exception as e:
            try:
                conn.rollback()
            except Exception:
                pass
            logging.error(f"Error saving result: {str(e)}")
            raise

    def get_settings(self) -> Dict:
        """Get application settings."""
        try:
            conn, _ = self._get_connection()
            return pd.read_sql_query(
                "SELECT * FROM settings WHERE setting_id = 1",
                conn
            ).iloc[0].to_dict()
        except Exception as e:
            logging.error(f"Error getting settings: {str(e)}")
            return {
                'min_transfer': 250.00,
                'default_betting_value': 2100.00
            }

    def save_settings(self, settings: Dict) -> None:
        """Save application settings."""
        try:
            conn, cursor = self._get_connection()
            cursor.execute("""
                UPDATE settings 
                SET min_transfer = ?,
                    default_betting_value = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE setting_id = 1
            """, (
                settings['min_transfer'],
                settings['default_betting_value']
            ))
            conn.commit()
            logging.info("Settings updated successfully")
        except Exception as e:
            conn.rollback()
            logging.error(f"Error saving settings: {str(e)}")
            raise

    def backup_database(self) -> str:
        """Create a backup of the database."""
        try:
            backup_dir = os.path.join(os.path.dirname(self.db_path), "backups")
            os.makedirs(backup_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(backup_dir, f"backup_{timestamp}.db")
            
            # Create backup
            shutil.copy2(self.db_path, backup_path)
            logging.info(f"Database backup created at {backup_path}")
            return backup_path
        except Exception as e:
            logging.error(f"Error creating backup: {str(e)}")
            raise

    def reset_database(self) -> bool:
        """Reset database to initial state."""
        try:
            # Close any existing connections
            if hasattr(self._local, 'conn'):
                self._local.conn.close()
                del self._local.conn
                del self._local.cursor

            # Delete the database file
            if os.path.exists(self.db_path):
                os.remove(self.db_path)

            # Recreate database
            self._setup_database()
            logging.info("Database reset successfully")
            return True
        except Exception as e:
            logging.error(f"Error resetting database: {str(e)}")
            raise

    def close(self) -> None:
        """Close all database connections."""
        try:
            if hasattr(self._local, 'conn'):
                self._local.conn.close()
                del self._local.conn
                del self._local.cursor
            logging.info("Database connections closed")
        except Exception as e:
            logging.error(f"Error closing database connections: {str(e)}")
            raise

    def get_bet_history(self) -> pd.DataFrame:
        """Get completed bets with results and account details."""
        try:
            conn, cursor = self._get_connection()
            # Get all completed bets with results
            bets = pd.read_sql_query("""
                SELECT 
                    b.bet_id,
                    m.team1,
                    m.team2,
                    m.match_date,
                    m.match_time,
                    b.team1_odds,
                    b.team2_odds,
                    b.betting_value,
                    b.created_at,
                    r.result_type,
                    r.winning_team,
                    r.profit_amount,
                    r.loss_amount,
                    r.cashout_details
                FROM bets b
                JOIN matches m ON b.match_id = m.match_id
                LEFT JOIN results r ON b.bet_id = r.bet_id
                WHERE b.status = 'completed'
                ORDER BY m.match_date DESC, m.match_time DESC
            """, conn)
            # Attach account details for each bet
            all_accounts = []
            for bet_id in bets['bet_id']:
                cursor.execute("""
                    SELECT 
                        ba.team_number,
                        ba.bet_amount,
                        a.account_id,
                        a.name,
                        a.balance
                    FROM bet_accounts ba
                    JOIN accounts a ON ba.account_id = a.account_id
                    WHERE ba.bet_id = ?
                    ORDER BY ba.team_number, a.account_id
                """, (bet_id,))
                accounts = [dict(row) for row in cursor.fetchall()]
                all_accounts.append(accounts)
            bets['accounts'] = all_accounts
            return bets
        except Exception as e:
            logging.error(f"Error getting bet history: {str(e)}")
            return pd.DataFrame()