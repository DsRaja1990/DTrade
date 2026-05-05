"""
Notification system for alerts and reports
"""
import logging
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

logger = logging.getLogger(__name__)

class NotificationSystem:
    def __init__(self, email_config=None, telegram_config=None):
        self.email_config = email_config or {
            'enabled': False,
            'smtp_server': os.getenv('SMTP_SERVER', ''),
            'smtp_port': int(os.getenv('SMTP_PORT', 587)),
            'sender_email': os.getenv('SENDER_EMAIL', ''),
            'sender_password': os.getenv('SENDER_PASSWORD', ''),
            'recipient_email': os.getenv('RECIPIENT_EMAIL', '')
        }
        
        self.telegram_config = telegram_config or {
            'enabled': False,
            'bot_token': os.getenv('TELEGRAM_BOT_TOKEN', ''),
            'chat_id': os.getenv('TELEGRAM_CHAT_ID', '')
        }
    
    def send_alert(self, message, level="info"):
        """Send an alert notification"""
        try:
            # Format the message
            formatted_message = f"[{level.upper()}] {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n{message}"
            
            # Send via configured channels
            if self.email_config['enabled'] and level in ["warning", "error"]:
                self._send_email(f"Trading Alert: {level.upper()}", formatted_message)
            
            if self.telegram_config['enabled']:
                self._send_telegram(formatted_message)
            
            # Log the alert
            if level == "error":
                logger.error(f"ALERT: {message}")
            elif level == "warning":
                logger.warning(f"ALERT: {message}")
            else:
                logger.info(f"ALERT: {message}")
                
            return True
        
        except Exception as e:
            logger.error(f"Failed to send alert: {e}", exc_info=True)
            return False
    
    def send_trade_notification(self, trade):
        """Send notification about a trade"""
        try:
            # Format trade details
            action = trade.get('action', 'UNKNOWN')
            symbol = trade.get('symbol', 'UNKNOWN')
            quantity = trade.get('quantity', 0)
            price = trade.get('price', 0)
            strategy = trade.get('strategy', 'UNKNOWN')
            
            message = f"TRADE: {action} {quantity} {symbol} @ ₹{price:.2f}\nStrategy: {strategy}"
            
            if 'reason' in trade:
                message += f"\nReason: {trade['reason']}"
            
            # Send via configured channels
            if self.telegram_config['enabled']:
                self._send_telegram(message)
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to send trade notification: {e}", exc_info=True)
            return False
    
    def send_eod_report(self, report):
        """Send end of day report"""
        try:
            # Format EOD report
            date = report.get('date', datetime.now().strftime('%Y-%m-%d'))
            account_value = report.get('account_value', 0)
            daily_change = report.get('daily_change', 0)
            daily_change_pct = report.get('daily_change_pct', 0)
            open_positions = report.get('open_positions', 0)
            closed_positions = report.get('closed_positions', 0)
            
            message = f"EOD REPORT: {date}\n"
            message += f"Account Value: ₹{account_value:,.2f}\n"
            message += f"Daily P&L: ₹{daily_change:,.2f} ({daily_change_pct:.2f}%)\n"
            message += f"Positions: {open_positions} open, {closed_positions} closed today\n\n"
            
            # Add performance metrics
            if 'performance' in report:
                perf = report['performance']
                message += f"Win Rate: {perf.get('win_rate', 0) * 100:.1f}%\n"
                message += f"Profit Factor: {perf.get('profit_factor', 0):.2f}\n"
                message += f"Max Drawdown: {perf.get('max_drawdown', 0) * 100:.1f}%\n"
            
            # Send via configured channels
            if self.email_config['enabled']:
                self._send_email(f"Trading EOD Report: {date}", message)
            
            if self.telegram_config['enabled']:
                self._send_telegram(message)
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to send EOD report: {e}", exc_info=True)
            return False
    
    def _send_email(self, subject, body):
        """Send email notification"""
        if not self.email_config['enabled']:
            return False
            
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['sender_email']
            msg['To'] = self.email_config['recipient_email']
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            server = smtplib.SMTP(
                self.email_config['smtp_server'], 
                self.email_config['smtp_port']
            )
            server.starttls()
            server.login(
                self.email_config['sender_email'], 
                self.email_config['sender_password']
            )
            text = msg.as_string()
            server.sendmail(
                self.email_config['sender_email'],
                self.email_config['recipient_email'],
                text
            )
            server.quit()
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to send email: {e}", exc_info=True)
            return False
    
    def _send_telegram(self, message):
        """Send telegram notification"""
        if not self.telegram_config['enabled']:
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.telegram_config['bot_token']}/sendMessage"
            data = {
                'chat_id': self.telegram_config['chat_id'],
                'text': message
            }
            
            response = requests.post(url, data=data)
            response.raise_for_status()
            
            return True
        
        except Exception as e:
            logger.error(f"Failed to send telegram message: {e}", exc_info=True)
            return False