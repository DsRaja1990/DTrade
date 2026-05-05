"""
Advanced Notification System for Intelligent Options Hedging Engine
Supports multiple channels: Email, SMS, Telegram, Slack, Discord, and more
"""

import asyncio
import aiohttp
import smtplib
import json
from datetime import datetime
from typing import Dict, Any, List, Optional, Union
from enum import Enum
from dataclasses import dataclass, asdict
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging
import os
from pathlib import Path
import yaml

logger = logging.getLogger(__name__)

class NotificationLevel(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
    TRADE = "TRADE"
    SIGNAL = "SIGNAL"
    RISK = "RISK"

class NotificationChannel(Enum):
    EMAIL = "email"
    SMS = "sms"
    TELEGRAM = "telegram"
    SLACK = "slack"
    DISCORD = "discord"
    WEBHOOK = "webhook"
    CONSOLE = "console"

@dataclass
class NotificationMessage:
    title: str
    message: str
    level: NotificationLevel
    timestamp: datetime
    metadata: Dict[str, Any]
    channels: List[NotificationChannel]
    urgent: bool = False
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'channels': [c.value for c in self.channels]
        }

class EmailNotifier:
    """Email notification handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.smtp_server = config.get('smtp_server', 'smtp.gmail.com')
        self.smtp_port = config.get('smtp_port', 587)
        self.username = config.get('username')
        self.password = config.get('password')
        self.from_email = config.get('from_email', self.username)
        self.to_emails = config.get('to_emails', [])
        
    async def send(self, notification: NotificationMessage):
        """Send email notification"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.from_email
            msg['To'] = ', '.join(self.to_emails)
            msg['Subject'] = f"[{notification.level.value}] {notification.title}"
            
            # Create HTML content
            html_content = self._create_html_content(notification)
            msg.attach(MIMEText(html_content, 'html'))
            
            # Send email
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.username, self.password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email notification sent: {notification.title}")
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            
    def _create_html_content(self, notification: NotificationMessage) -> str:
        """Create HTML email content"""
        color_map = {
            NotificationLevel.INFO: "#17a2b8",
            NotificationLevel.WARNING: "#ffc107",
            NotificationLevel.ERROR: "#dc3545",
            NotificationLevel.CRITICAL: "#dc3545",
            NotificationLevel.TRADE: "#28a745",
            NotificationLevel.SIGNAL: "#007bff",
            NotificationLevel.RISK: "#fd7e14"
        }
        
        color = color_map.get(notification.level, "#6c757d")
        
        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px;">
            <div style="background-color: {color}; color: white; padding: 10px; border-radius: 5px 5px 0 0;">
                <h2 style="margin: 0;">{notification.title}</h2>
                <small>{notification.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</small>
            </div>
            <div style="border: 1px solid {color}; padding: 20px; border-radius: 0 0 5px 5px;">
                <p style="font-size: 16px; line-height: 1.5;">{notification.message}</p>
                
                {self._format_metadata_html(notification.metadata)}
            </div>
        </body>
        </html>
        """
        return html
        
    def _format_metadata_html(self, metadata: Dict[str, Any]) -> str:
        """Format metadata as HTML table"""
        if not metadata:
            return ""
            
        html = "<h3>Details:</h3><table style='border-collapse: collapse; width: 100%;'>"
        for key, value in metadata.items():
            html += f"""
            <tr>
                <td style='border: 1px solid #ddd; padding: 8px; font-weight: bold;'>{key}</td>
                <td style='border: 1px solid #ddd; padding: 8px;'>{value}</td>
            </tr>
            """
        html += "</table>"
        return html

class TelegramNotifier:
    """Telegram notification handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.bot_token = config.get('bot_token')
        self.chat_ids = config.get('chat_ids', [])
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        
    async def send(self, notification: NotificationMessage):
        """Send Telegram notification"""
        if not self.bot_token or not self.chat_ids:
            return
            
        try:
            message_text = self._format_telegram_message(notification)
            
            async with aiohttp.ClientSession() as session:
                for chat_id in self.chat_ids:
                    data = {
                        'chat_id': chat_id,
                        'text': message_text,
                        'parse_mode': 'Markdown',
                        'disable_web_page_preview': True
                    }
                    
                    async with session.post(
                        f"{self.api_url}/sendMessage",
                        json=data
                    ) as response:
                        if response.status == 200:
                            logger.info(f"Telegram notification sent to {chat_id}")
                        else:
                            logger.error(f"Failed to send Telegram to {chat_id}: {await response.text()}")
                            
        except Exception as e:
            logger.error(f"Failed to send Telegram notification: {e}")
            
    def _format_telegram_message(self, notification: NotificationMessage) -> str:
        """Format message for Telegram"""
        emoji_map = {
            NotificationLevel.INFO: "ℹ️",
            NotificationLevel.WARNING: "⚠️",
            NotificationLevel.ERROR: "❌",
            NotificationLevel.CRITICAL: "🚨",
            NotificationLevel.TRADE: "💰",
            NotificationLevel.SIGNAL: "📊",
            NotificationLevel.RISK: "⚡"
        }
        
        emoji = emoji_map.get(notification.level, "📢")
        
        message = f"{emoji} *{notification.title}*\n\n"
        message += f"{notification.message}\n\n"
        
        if notification.metadata:
            message += "*Details:*\n"
            for key, value in notification.metadata.items():
                message += f"• *{key}:* {value}\n"
        
        message += f"\n⏰ {notification.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        
        return message

class SlackNotifier:
    """Slack notification handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url')
        self.channel = config.get('channel', '#trading-alerts')
        self.username = config.get('username', 'Options Hedger')
        
    async def send(self, notification: NotificationMessage):
        """Send Slack notification"""
        if not self.webhook_url:
            return
            
        try:
            payload = self._create_slack_payload(notification)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 200:
                        logger.info("Slack notification sent")
                    else:
                        logger.error(f"Failed to send Slack notification: {await response.text()}")
                        
        except Exception as e:
            logger.error(f"Failed to send Slack notification: {e}")
            
    def _create_slack_payload(self, notification: NotificationMessage) -> Dict[str, Any]:
        """Create Slack message payload"""
        color_map = {
            NotificationLevel.INFO: "#36a64f",
            NotificationLevel.WARNING: "#ffcc00",
            NotificationLevel.ERROR: "#ff0000",
            NotificationLevel.CRITICAL: "#ff0000",
            NotificationLevel.TRADE: "#36a64f",
            NotificationLevel.SIGNAL: "#0099ff",
            NotificationLevel.RISK: "#ff6600"
        }
        
        color = color_map.get(notification.level, "#808080")
        
        fields = []
        for key, value in notification.metadata.items():
            fields.append({
                "title": key,
                "value": str(value),
                "short": len(str(value)) < 30
            })
        
        attachment = {
            "color": color,
            "title": notification.title,
            "text": notification.message,
            "fields": fields,
            "footer": "Options Hedging Engine",
            "ts": int(notification.timestamp.timestamp())
        }
        
        return {
            "channel": self.channel,
            "username": self.username,
            "attachments": [attachment]
        }

class DiscordNotifier:
    """Discord notification handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_url = config.get('webhook_url')
        
    async def send(self, notification: NotificationMessage):
        """Send Discord notification"""
        if not self.webhook_url:
            return
            
        try:
            embed = self._create_discord_embed(notification)
            payload = {"embeds": [embed]}
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.webhook_url, json=payload) as response:
                    if response.status == 204:
                        logger.info("Discord notification sent")
                    else:
                        logger.error(f"Failed to send Discord notification: {await response.text()}")
                        
        except Exception as e:
            logger.error(f"Failed to send Discord notification: {e}")
            
    def _create_discord_embed(self, notification: NotificationMessage) -> Dict[str, Any]:
        """Create Discord embed"""
        color_map = {
            NotificationLevel.INFO: 0x17a2b8,
            NotificationLevel.WARNING: 0xffc107,
            NotificationLevel.ERROR: 0xdc3545,
            NotificationLevel.CRITICAL: 0xdc3545,
            NotificationLevel.TRADE: 0x28a745,
            NotificationLevel.SIGNAL: 0x007bff,
            NotificationLevel.RISK: 0xfd7e14
        }
        
        color = color_map.get(notification.level, 0x6c757d)
        
        embed = {
            "title": notification.title,
            "description": notification.message,
            "color": color,
            "timestamp": notification.timestamp.isoformat(),
            "footer": {"text": "Options Hedging Engine"}
        }
        
        if notification.metadata:
            fields = []
            for key, value in notification.metadata.items():
                fields.append({
                    "name": key,
                    "value": str(value),
                    "inline": True
                })
            embed["fields"] = fields
            
        return embed

class WebhookNotifier:
    """Generic webhook notification handler"""
    
    def __init__(self, config: Dict[str, Any]):
        self.webhook_urls = config.get('webhook_urls', [])
        self.headers = config.get('headers', {})
        
    async def send(self, notification: NotificationMessage):
        """Send webhook notification"""
        if not self.webhook_urls:
            return
            
        try:
            payload = notification.to_dict()
            
            async with aiohttp.ClientSession() as session:
                for url in self.webhook_urls:
                    async with session.post(
                        url,
                        json=payload,
                        headers=self.headers
                    ) as response:
                        if response.status in [200, 201, 204]:
                            logger.info(f"Webhook notification sent to {url}")
                        else:
                            logger.error(f"Failed to send webhook to {url}: {await response.text()}")
                            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")

class NotificationManager:
    """Central notification management system"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.enabled_channels = set(config.get('enabled_channels', []))
        self.notification_rules = config.get('notification_rules', {})
        
        # Initialize notifiers
        self.notifiers = {}
        self._initialize_notifiers()
        
        # Message queue and rate limiting
        self.message_queue = asyncio.Queue()
        self.rate_limits = config.get('rate_limits', {})
        self.last_sent = {}
        
        # Start background worker
        asyncio.create_task(self._process_notifications())
        
    def _initialize_notifiers(self):
        """Initialize notification handlers"""
        if NotificationChannel.EMAIL in self.enabled_channels:
            email_config = self.config.get('email', {})
            if email_config:
                self.notifiers[NotificationChannel.EMAIL] = EmailNotifier(email_config)
                
        if NotificationChannel.TELEGRAM in self.enabled_channels:
            telegram_config = self.config.get('telegram', {})
            if telegram_config:
                self.notifiers[NotificationChannel.TELEGRAM] = TelegramNotifier(telegram_config)
                
        if NotificationChannel.SLACK in self.enabled_channels:
            slack_config = self.config.get('slack', {})
            if slack_config:
                self.notifiers[NotificationChannel.SLACK] = SlackNotifier(slack_config)
                
        if NotificationChannel.DISCORD in self.enabled_channels:
            discord_config = self.config.get('discord', {})
            if discord_config:
                self.notifiers[NotificationChannel.DISCORD] = DiscordNotifier(discord_config)
                
        if NotificationChannel.WEBHOOK in self.enabled_channels:
            webhook_config = self.config.get('webhook', {})
            if webhook_config:
                self.notifiers[NotificationChannel.WEBHOOK] = WebhookNotifier(webhook_config)
    
    async def send_notification(self, title: str, message: str,
                              level: NotificationLevel = NotificationLevel.INFO,
                              metadata: Dict[str, Any] = None,
                              channels: List[NotificationChannel] = None,
                              urgent: bool = False):
        """Send notification through specified channels"""
        
        # Apply notification rules
        if not self._should_send_notification(level, title, message):
            return
            
        # Determine channels
        if channels is None:
            channels = self._get_channels_for_level(level)
        
        # Create notification
        notification = NotificationMessage(
            title=title,
            message=message,
            level=level,
            timestamp=datetime.utcnow(),
            metadata=metadata or {},
            channels=channels,
            urgent=urgent
        )
        
        # Add to queue
        await self.message_queue.put(notification)
        
    def _should_send_notification(self, level: NotificationLevel,
                                title: str, message: str) -> bool:
        """Check if notification should be sent based on rules"""
        # Check level filtering
        min_level = self.notification_rules.get('min_level')
        if min_level:
            level_order = {
                NotificationLevel.INFO: 0,
                NotificationLevel.WARNING: 1,
                NotificationLevel.ERROR: 2,
                NotificationLevel.CRITICAL: 3
            }
            if level_order.get(level, 0) < level_order.get(NotificationLevel[min_level], 0):
                return False
        
        # Check rate limiting
        rate_key = f"{level.value}:{title}"
        rate_limit = self.rate_limits.get(level.value, {})
        
        if rate_limit:
            max_per_hour = rate_limit.get('max_per_hour')
            if max_per_hour:
                now = datetime.utcnow()
                last_sent_time = self.last_sent.get(rate_key)
                
                if last_sent_time:
                    time_diff = (now - last_sent_time).total_seconds() / 3600
                    if time_diff < 1:  # Within an hour
                        return False
                        
                self.last_sent[rate_key] = now
        
        return True
    
    def _get_channels_for_level(self, level: NotificationLevel) -> List[NotificationChannel]:
        """Get appropriate channels for notification level"""
        channel_rules = self.notification_rules.get('channels_by_level', {})
        
        if level == NotificationLevel.CRITICAL:
            return channel_rules.get('critical', list(self.enabled_channels))
        elif level == NotificationLevel.ERROR:
            return channel_rules.get('error', [NotificationChannel.EMAIL, NotificationChannel.TELEGRAM])
        elif level == NotificationLevel.WARNING:
            return channel_rules.get('warning', [NotificationChannel.TELEGRAM])
        elif level == NotificationLevel.TRADE:
            return channel_rules.get('trade', [NotificationChannel.TELEGRAM, NotificationChannel.SLACK])
        elif level == NotificationLevel.SIGNAL:
            return channel_rules.get('signal', [NotificationChannel.TELEGRAM])
        else:
            return channel_rules.get('info', [NotificationChannel.CONSOLE])
    
    async def _process_notifications(self):
        """Background worker to process notification queue"""
        while True:
            try:
                notification = await self.message_queue.get()
                
                # Send to each channel
                tasks = []
                for channel in notification.channels:
                    if channel in self.notifiers:
                        tasks.append(self.notifiers[channel].send(notification))
                    elif channel == NotificationChannel.CONSOLE:
                        self._send_console_notification(notification)
                
                if tasks:
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
            except Exception as e:
                logger.error(f"Error processing notification: {e}")
    
    def _send_console_notification(self, notification: NotificationMessage):
        """Send notification to console"""
        timestamp = notification.timestamp.strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [{notification.level.value}] {notification.title}: {notification.message}")
        
        if notification.metadata:
            for key, value in notification.metadata.items():
                print(f"  {key}: {value}")
    
    # Convenience methods
    async def info(self, title: str, message: str, **kwargs):
        await self.send_notification(title, message, NotificationLevel.INFO, **kwargs)
    
    async def warning(self, title: str, message: str, **kwargs):
        await self.send_notification(title, message, NotificationLevel.WARNING, **kwargs)
    
    async def error(self, title: str, message: str, **kwargs):
        await self.send_notification(title, message, NotificationLevel.ERROR, **kwargs)
    
    async def critical(self, title: str, message: str, **kwargs):
        await self.send_notification(title, message, NotificationLevel.CRITICAL, **kwargs)
    
    async def trade_alert(self, title: str, message: str, **kwargs):
        await self.send_notification(title, message, NotificationLevel.TRADE, **kwargs)
    
    async def signal_alert(self, title: str, message: str, **kwargs):
        await self.send_notification(title, message, NotificationLevel.SIGNAL, **kwargs)
    
    async def risk_alert(self, title: str, message: str, **kwargs):
        await self.send_notification(title, message, NotificationLevel.RISK, **kwargs)

# Global notifier instance
_notifier_instance = None

def setup_notifier(config: Dict[str, Any]) -> NotificationManager:
    """Setup global notifier instance"""
    global _notifier_instance
    _notifier_instance = NotificationManager(config)
    return _notifier_instance

def get_notifier() -> NotificationManager:
    """Get global notifier instance"""
    if _notifier_instance is None:
        # Return a dummy notifier if not initialized
        class DummyNotifier:
            async def send_notification(self, *args, **kwargs): pass
            async def info(self, *args, **kwargs): pass
            async def warning(self, *args, **kwargs): pass
            async def error(self, *args, **kwargs): pass
            async def critical(self, *args, **kwargs): pass
            async def trade_alert(self, *args, **kwargs): pass
            async def signal_alert(self, *args, **kwargs): pass
            async def risk_alert(self, *args, **kwargs): pass
        return DummyNotifier()
    return _notifier_instance
