"""
Signal Engine Evaluation Module
================================
Stores and tracks signal outcomes for strategy evaluation.
All signals are logged with market context for later analysis.

Database: evaluation_signals.db (separate from production)
"""

import sqlite3
import json
import logging
import uuid
import os
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# Ensure database directory exists
os.makedirs("database", exist_ok=True)


class EvaluationMode(Enum):
    """Evaluation mode states"""
    ENABLED = "enabled"
    DISABLED = "disabled"


@dataclass
class EvaluationSignal:
    """Signal recorded for evaluation"""
    signal_id: str
    timestamp: str
    instrument: str
    signal_type: str  # BUY, SELL, STRONG_BUY, STRONG_SELL
    confidence: float
    entry_price: float
    target: float
    stop_loss: float
    risk_reward: float
    technical_score: float
    momentum_score: float
    trend_direction: str
    timeframe: str
    indicators: Dict
    ai_validation: bool
    notes: str
    
    # Market context at signal generation
    market_high: float = 0.0
    market_low: float = 0.0
    market_volume: int = 0
    vix_level: float = 0.0
    
    # Outcome tracking
    actual_exit_price: float = 0.0
    actual_pnl: float = 0.0
    actual_pnl_points: float = 0.0
    hit_target: bool = False
    hit_stop_loss: bool = False
    max_favorable_excursion: float = 0.0  # Max profit during trade
    max_adverse_excursion: float = 0.0   # Max drawdown during trade
    exit_reason: str = ""
    exit_time: str = ""
    hold_duration_minutes: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)


class SignalEvaluationExecutor:
    """
    Evaluation executor for Signal Engine Service.
    Tracks all signals and their outcomes without affecting production.
    """
    
    def __init__(self, db_path: str = "database/evaluation_signals.db"):
        self.db_path = db_path
        self.mode = EvaluationMode.DISABLED
        self._active_signals: Dict[str, EvaluationSignal] = {}
        self._init_database()
        logger.info(f"SignalEvaluationExecutor initialized - DB: {db_path}")
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_database(self):
        """Initialize evaluation database tables"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # Evaluation signals table - comprehensive tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluation_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                instrument TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                confidence REAL,
                entry_price REAL,
                target REAL,
                stop_loss REAL,
                risk_reward REAL,
                technical_score REAL,
                momentum_score REAL,
                trend_direction TEXT,
                timeframe TEXT,
                indicators TEXT,
                ai_validation INTEGER,
                notes TEXT,
                
                -- Market context
                market_high REAL DEFAULT 0,
                market_low REAL DEFAULT 0,
                market_volume INTEGER DEFAULT 0,
                vix_level REAL DEFAULT 0,
                
                -- Outcome tracking
                status TEXT DEFAULT 'active',
                actual_exit_price REAL DEFAULT 0,
                actual_pnl REAL DEFAULT 0,
                actual_pnl_points REAL DEFAULT 0,
                hit_target INTEGER DEFAULT 0,
                hit_stop_loss INTEGER DEFAULT 0,
                max_favorable_excursion REAL DEFAULT 0,
                max_adverse_excursion REAL DEFAULT 0,
                exit_reason TEXT,
                exit_time TEXT,
                hold_duration_minutes INTEGER DEFAULT 0,
                
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Price tracking during signal lifetime
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluation_price_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_id TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                price REAL NOT NULL,
                pnl_points REAL DEFAULT 0,
                is_new_high INTEGER DEFAULT 0,
                is_new_low INTEGER DEFAULT 0,
                FOREIGN KEY (signal_id) REFERENCES evaluation_signals(signal_id)
            )
        ''')
        
        # Daily performance aggregation
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluation_daily_performance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                total_signals INTEGER DEFAULT 0,
                buy_signals INTEGER DEFAULT 0,
                sell_signals INTEGER DEFAULT 0,
                strong_signals INTEGER DEFAULT 0,
                closed_signals INTEGER DEFAULT 0,
                winning_signals INTEGER DEFAULT 0,
                losing_signals INTEGER DEFAULT 0,
                total_pnl_points REAL DEFAULT 0,
                avg_confidence REAL DEFAULT 0,
                avg_risk_reward REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                best_signal_pnl REAL DEFAULT 0,
                worst_signal_pnl REAL DEFAULT 0,
                avg_hold_duration INTEGER DEFAULT 0,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Signal analysis - by instrument
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS evaluation_by_instrument (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                instrument TEXT NOT NULL,
                total_signals INTEGER DEFAULT 0,
                winning INTEGER DEFAULT 0,
                losing INTEGER DEFAULT 0,
                total_pnl REAL DEFAULT 0,
                win_rate REAL DEFAULT 0,
                avg_confidence REAL DEFAULT 0,
                last_updated TEXT DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create indexes for fast queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_instrument ON evaluation_signals(instrument)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON evaluation_signals(timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_signals_status ON evaluation_signals(status)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_price_tracking_signal ON evaluation_price_tracking(signal_id)')
        
        conn.commit()
        conn.close()
        logger.info("Evaluation database initialized with all tables")
    
    def enable_evaluation(self) -> Dict:
        """Enable evaluation mode"""
        self.mode = EvaluationMode.ENABLED
        logger.info("🔬 Signal Evaluation Mode ENABLED")
        return {
            "success": True,
            "mode": "evaluation",
            "message": "All signals will be tracked for evaluation"
        }
    
    def disable_evaluation(self) -> Dict:
        """Disable evaluation mode"""
        self.mode = EvaluationMode.DISABLED
        logger.info("📋 Signal Evaluation Mode DISABLED")
        return {
            "success": True,
            "mode": "normal",
            "message": "Evaluation tracking disabled"
        }
    
    def record_signal(
        self,
        signal_id: str,
        instrument: str,
        signal_type: str,
        confidence: float,
        entry_price: float,
        target: float,
        stop_loss: float,
        risk_reward: float,
        technical_score: float,
        momentum_score: float,
        trend_direction: str,
        timeframe: str,
        indicators: Dict,
        ai_validation: bool = False,
        notes: str = "",
        market_context: Dict = None
    ) -> str:
        """Record a signal for evaluation"""
        
        timestamp = datetime.now().isoformat()
        
        eval_signal = EvaluationSignal(
            signal_id=signal_id,
            timestamp=timestamp,
            instrument=instrument,
            signal_type=signal_type,
            confidence=confidence,
            entry_price=entry_price,
            target=target,
            stop_loss=stop_loss,
            risk_reward=risk_reward,
            technical_score=technical_score,
            momentum_score=momentum_score,
            trend_direction=trend_direction,
            timeframe=timeframe,
            indicators=indicators,
            ai_validation=ai_validation,
            notes=notes,
            market_high=market_context.get('high', 0) if market_context else 0,
            market_low=market_context.get('low', 0) if market_context else 0,
            market_volume=market_context.get('volume', 0) if market_context else 0,
            vix_level=market_context.get('vix', 0) if market_context else 0
        )
        
        # Store in memory for active tracking
        self._active_signals[signal_id] = eval_signal
        
        # Store in database
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO evaluation_signals (
                    signal_id, timestamp, instrument, signal_type, confidence,
                    entry_price, target, stop_loss, risk_reward, technical_score,
                    momentum_score, trend_direction, timeframe, indicators,
                    ai_validation, notes, market_high, market_low, market_volume, vix_level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                signal_id, timestamp, instrument, signal_type, confidence,
                entry_price, target, stop_loss, risk_reward, technical_score,
                momentum_score, trend_direction, timeframe, json.dumps(indicators),
                1 if ai_validation else 0, notes,
                eval_signal.market_high, eval_signal.market_low,
                eval_signal.market_volume, eval_signal.vix_level
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"📊 Evaluation signal recorded: {instrument} {signal_type} @ {entry_price}")
            
        except Exception as e:
            logger.error(f"Error recording evaluation signal: {e}")
        
        return signal_id
    
    def update_signal_price(self, signal_id: str, current_price: float):
        """Update price for an active signal - track MFE/MAE"""
        if signal_id not in self._active_signals:
            return
        
        signal = self._active_signals[signal_id]
        
        # Calculate current P&L in points
        if signal.signal_type in ["BUY", "STRONG_BUY"]:
            pnl_points = current_price - signal.entry_price
        else:
            pnl_points = signal.entry_price - current_price
        
        # Update MFE/MAE
        is_new_high = False
        is_new_low = False
        
        if pnl_points > signal.max_favorable_excursion:
            signal.max_favorable_excursion = pnl_points
            is_new_high = True
        
        if pnl_points < -signal.max_adverse_excursion:
            signal.max_adverse_excursion = abs(pnl_points)
            is_new_low = True
        
        # Record price point
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO evaluation_price_tracking (
                    signal_id, timestamp, price, pnl_points, is_new_high, is_new_low
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                signal_id, datetime.now().isoformat(), current_price,
                pnl_points, 1 if is_new_high else 0, 1 if is_new_low else 0
            ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating price tracking: {e}")
    
    def update_active_signals_price(self, instrument: str, current_price: float):
        """Update price for all active signals of an instrument"""
        for signal_id, signal in self._active_signals.items():
            if signal.instrument == instrument:
                self.update_signal_price(signal_id, current_price)
    
    def close_signal(
        self,
        signal_id: str,
        exit_price: float,
        exit_reason: str = "manual"
    ) -> Dict:
        """Close an evaluation signal and record outcome"""
        
        if signal_id not in self._active_signals:
            # Try to load from database
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM evaluation_signals WHERE signal_id = ?", (signal_id,))
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return {"success": False, "error": "Signal not found"}
            
            # Create from database
            signal = EvaluationSignal(
                signal_id=row['signal_id'],
                timestamp=row['timestamp'],
                instrument=row['instrument'],
                signal_type=row['signal_type'],
                confidence=row['confidence'],
                entry_price=row['entry_price'],
                target=row['target'],
                stop_loss=row['stop_loss'],
                risk_reward=row['risk_reward'],
                technical_score=row['technical_score'],
                momentum_score=row['momentum_score'],
                trend_direction=row['trend_direction'],
                timeframe=row['timeframe'],
                indicators=json.loads(row['indicators']) if row['indicators'] else {},
                ai_validation=bool(row['ai_validation']),
                notes=row['notes'] or ""
            )
        else:
            signal = self._active_signals[signal_id]
        
        exit_time = datetime.now()
        
        # Calculate P&L
        if signal.signal_type in ["BUY", "STRONG_BUY"]:
            pnl_points = exit_price - signal.entry_price
        else:
            pnl_points = signal.entry_price - exit_price
        
        # Determine if target/SL was hit
        hit_target = False
        hit_stop_loss = False
        
        if signal.signal_type in ["BUY", "STRONG_BUY"]:
            if exit_price >= signal.target:
                hit_target = True
            elif exit_price <= signal.stop_loss:
                hit_stop_loss = True
        else:
            if exit_price <= signal.target:
                hit_target = True
            elif exit_price >= signal.stop_loss:
                hit_stop_loss = True
        
        # Calculate hold duration
        try:
            entry_time = datetime.fromisoformat(signal.timestamp)
            hold_duration = int((exit_time - entry_time).total_seconds() / 60)
        except:
            hold_duration = 0
        
        # Update database
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE evaluation_signals SET
                    status = 'closed',
                    actual_exit_price = ?,
                    actual_pnl_points = ?,
                    hit_target = ?,
                    hit_stop_loss = ?,
                    max_favorable_excursion = ?,
                    max_adverse_excursion = ?,
                    exit_reason = ?,
                    exit_time = ?,
                    hold_duration_minutes = ?
                WHERE signal_id = ?
            ''', (
                exit_price, pnl_points,
                1 if hit_target else 0, 1 if hit_stop_loss else 0,
                signal.max_favorable_excursion, signal.max_adverse_excursion,
                exit_reason, exit_time.isoformat(), hold_duration, signal_id
            ))
            
            conn.commit()
            conn.close()
            
            # Update daily performance
            self._update_daily_performance()
            
            logger.info(f"📈 Signal closed: {signal.instrument} {signal.signal_type} | "
                       f"P&L: {pnl_points:+.2f} pts | Reason: {exit_reason}")
            
        except Exception as e:
            logger.error(f"Error closing signal: {e}")
            return {"success": False, "error": str(e)}
        
        # Remove from active signals
        if signal_id in self._active_signals:
            del self._active_signals[signal_id]
        
        return {
            "success": True,
            "signal_id": signal_id,
            "instrument": signal.instrument,
            "signal_type": signal.signal_type,
            "entry_price": signal.entry_price,
            "exit_price": exit_price,
            "pnl_points": pnl_points,
            "hit_target": hit_target,
            "hit_stop_loss": hit_stop_loss,
            "hold_duration_minutes": hold_duration,
            "mfe": signal.max_favorable_excursion,
            "mae": signal.max_adverse_excursion
        }
    
    def _update_daily_performance(self):
        """Update daily performance aggregation"""
        today = date.today().isoformat()
        
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Get today's stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN signal_type IN ('BUY', 'STRONG_BUY') THEN 1 ELSE 0 END) as buys,
                    SUM(CASE WHEN signal_type IN ('SELL', 'STRONG_SELL') THEN 1 ELSE 0 END) as sells,
                    SUM(CASE WHEN signal_type IN ('STRONG_BUY', 'STRONG_SELL') THEN 1 ELSE 0 END) as strong,
                    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed,
                    SUM(CASE WHEN status = 'closed' AND actual_pnl_points > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN status = 'closed' AND actual_pnl_points <= 0 THEN 1 ELSE 0 END) as losses,
                    COALESCE(SUM(CASE WHEN status = 'closed' THEN actual_pnl_points ELSE 0 END), 0) as total_pnl,
                    COALESCE(AVG(confidence), 0) as avg_conf,
                    COALESCE(AVG(risk_reward), 0) as avg_rr,
                    COALESCE(MAX(CASE WHEN status = 'closed' THEN actual_pnl_points END), 0) as best_pnl,
                    COALESCE(MIN(CASE WHEN status = 'closed' THEN actual_pnl_points END), 0) as worst_pnl,
                    COALESCE(AVG(CASE WHEN status = 'closed' THEN hold_duration_minutes END), 0) as avg_hold
                FROM evaluation_signals
                WHERE DATE(timestamp) = ?
            ''', (today,))
            
            row = cursor.fetchone()
            
            if row:
                win_rate = (row['wins'] / row['closed'] * 100) if row['closed'] > 0 else 0
                
                cursor.execute('''
                    INSERT OR REPLACE INTO evaluation_daily_performance (
                        date, total_signals, buy_signals, sell_signals, strong_signals,
                        closed_signals, winning_signals, losing_signals, total_pnl_points,
                        avg_confidence, avg_risk_reward, win_rate, best_signal_pnl,
                        worst_signal_pnl, avg_hold_duration, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    today, row['total'], row['buys'], row['sells'], row['strong'],
                    row['closed'], row['wins'], row['losses'], row['total_pnl'],
                    row['avg_conf'], row['avg_rr'], win_rate, row['best_pnl'],
                    row['worst_pnl'], row['avg_hold'], datetime.now().isoformat()
                ))
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error updating daily performance: {e}")
    
    def get_evaluation_signals(
        self,
        limit: int = 100,
        status: str = None,
        instrument: str = None
    ) -> List[Dict]:
        """Get evaluation signals with optional filters"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            query = "SELECT * FROM evaluation_signals WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if instrument:
                query += " AND instrument = ?"
                params.append(instrument.upper())
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            signals = []
            for row in rows:
                signals.append({
                    "signal_id": row['signal_id'],
                    "timestamp": row['timestamp'],
                    "instrument": row['instrument'],
                    "signal_type": row['signal_type'],
                    "confidence": row['confidence'],
                    "entry_price": row['entry_price'],
                    "target": row['target'],
                    "stop_loss": row['stop_loss'],
                    "risk_reward": row['risk_reward'],
                    "technical_score": row['technical_score'],
                    "momentum_score": row['momentum_score'],
                    "trend_direction": row['trend_direction'],
                    "timeframe": row['timeframe'],
                    "status": row['status'],
                    "actual_exit_price": row['actual_exit_price'],
                    "actual_pnl_points": row['actual_pnl_points'],
                    "hit_target": bool(row['hit_target']),
                    "hit_stop_loss": bool(row['hit_stop_loss']),
                    "mfe": row['max_favorable_excursion'],
                    "mae": row['max_adverse_excursion'],
                    "exit_reason": row['exit_reason'],
                    "exit_time": row['exit_time'],
                    "hold_duration_minutes": row['hold_duration_minutes']
                })
            
            return signals
            
        except Exception as e:
            logger.error(f"Error getting evaluation signals: {e}")
            return []
    
    def get_performance_summary(self) -> Dict:
        """Get comprehensive performance summary"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # Overall stats
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_signals,
                    SUM(CASE WHEN status = 'closed' THEN 1 ELSE 0 END) as closed_signals,
                    SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END) as active_signals,
                    SUM(CASE WHEN status = 'closed' AND actual_pnl_points > 0 THEN 1 ELSE 0 END) as winning,
                    SUM(CASE WHEN status = 'closed' AND actual_pnl_points <= 0 THEN 1 ELSE 0 END) as losing,
                    COALESCE(SUM(CASE WHEN status = 'closed' THEN actual_pnl_points ELSE 0 END), 0) as total_pnl,
                    COALESCE(AVG(confidence), 0) as avg_confidence,
                    COALESCE(AVG(risk_reward), 0) as avg_risk_reward,
                    COALESCE(MAX(CASE WHEN status = 'closed' THEN actual_pnl_points END), 0) as best_trade,
                    COALESCE(MIN(CASE WHEN status = 'closed' THEN actual_pnl_points END), 0) as worst_trade,
                    COALESCE(AVG(CASE WHEN status = 'closed' THEN hold_duration_minutes END), 0) as avg_hold,
                    COALESCE(AVG(max_favorable_excursion), 0) as avg_mfe,
                    COALESCE(AVG(max_adverse_excursion), 0) as avg_mae
                FROM evaluation_signals
            ''')
            
            row = cursor.fetchone()
            conn.close()
            
            if not row or row['total_signals'] == 0:
                return {
                    "mode": self.mode.value,
                    "total_signals": 0,
                    "active_signals": 0,
                    "closed_signals": 0,
                    "winning_signals": 0,
                    "losing_signals": 0,
                    "win_rate": 0,
                    "total_pnl_points": 0,
                    "avg_confidence": 0,
                    "message": "No evaluation data yet"
                }
            
            win_rate = (row['winning'] / row['closed_signals'] * 100) if row['closed_signals'] > 0 else 0
            
            return {
                "mode": self.mode.value,
                "total_signals": row['total_signals'],
                "active_signals": row['active_signals'],
                "closed_signals": row['closed_signals'],
                "winning_signals": row['winning'],
                "losing_signals": row['losing'],
                "win_rate": round(win_rate, 2),
                "total_pnl_points": round(row['total_pnl'], 2),
                "avg_pnl_per_trade": round(row['total_pnl'] / row['closed_signals'], 2) if row['closed_signals'] > 0 else 0,
                "best_trade_points": round(row['best_trade'], 2),
                "worst_trade_points": round(row['worst_trade'], 2),
                "avg_confidence": round(row['avg_confidence'], 3),
                "avg_risk_reward": round(row['avg_risk_reward'], 2),
                "avg_hold_duration_minutes": round(row['avg_hold'], 1),
                "avg_mfe": round(row['avg_mfe'], 2),
                "avg_mae": round(row['avg_mae'], 2)
            }
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {"error": str(e)}
    
    def get_daily_performance(self, days: int = 30) -> List[Dict]:
        """Get daily performance breakdown"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM evaluation_daily_performance
                ORDER BY date DESC
                LIMIT ?
            ''', (days,))
            
            rows = cursor.fetchall()
            conn.close()
            
            return [dict(row) for row in rows]
            
        except Exception as e:
            logger.error(f"Error getting daily performance: {e}")
            return []
    
    def get_performance_by_instrument(self) -> Dict:
        """Get performance breakdown by instrument"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    instrument,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'closed' AND actual_pnl_points > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN status = 'closed' AND actual_pnl_points <= 0 THEN 1 ELSE 0 END) as losses,
                    COALESCE(SUM(CASE WHEN status = 'closed' THEN actual_pnl_points ELSE 0 END), 0) as pnl,
                    COALESCE(AVG(confidence), 0) as avg_conf
                FROM evaluation_signals
                GROUP BY instrument
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            result = {}
            for row in rows:
                closed = row['wins'] + row['losses']
                result[row['instrument']] = {
                    "total_signals": row['total'],
                    "winning": row['wins'],
                    "losing": row['losses'],
                    "win_rate": round((row['wins'] / closed * 100) if closed > 0 else 0, 2),
                    "total_pnl_points": round(row['pnl'], 2),
                    "avg_confidence": round(row['avg_conf'], 3)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting performance by instrument: {e}")
            return {}
    
    def get_performance_by_signal_type(self) -> Dict:
        """Get performance breakdown by signal type"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT 
                    signal_type,
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'closed' AND actual_pnl_points > 0 THEN 1 ELSE 0 END) as wins,
                    SUM(CASE WHEN status = 'closed' AND actual_pnl_points <= 0 THEN 1 ELSE 0 END) as losses,
                    COALESCE(SUM(CASE WHEN status = 'closed' THEN actual_pnl_points ELSE 0 END), 0) as pnl
                FROM evaluation_signals
                GROUP BY signal_type
            ''')
            
            rows = cursor.fetchall()
            conn.close()
            
            result = {}
            for row in rows:
                closed = row['wins'] + row['losses']
                result[row['signal_type']] = {
                    "total_signals": row['total'],
                    "winning": row['wins'],
                    "losing": row['losses'],
                    "win_rate": round((row['wins'] / closed * 100) if closed > 0 else 0, 2),
                    "total_pnl_points": round(row['pnl'], 2)
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting performance by signal type: {e}")
            return {}
    
    def export_evaluation_data(self) -> Dict:
        """Export all evaluation data for external analysis"""
        return {
            "signals": self.get_evaluation_signals(limit=10000),
            "performance": self.get_performance_summary(),
            "daily_breakdown": self.get_daily_performance(365),
            "by_instrument": self.get_performance_by_instrument(),
            "by_signal_type": self.get_performance_by_signal_type(),
            "export_timestamp": datetime.now().isoformat()
        }
    
    def clear_all_data(self):
        """Clear all evaluation data"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM evaluation_signals")
            cursor.execute("DELETE FROM evaluation_price_tracking")
            cursor.execute("DELETE FROM evaluation_daily_performance")
            cursor.execute("DELETE FROM evaluation_by_instrument")
            
            conn.commit()
            conn.close()
            
            self._active_signals.clear()
            
            logger.info("🗑️ All evaluation data cleared")
            
        except Exception as e:
            logger.error(f"Error clearing evaluation data: {e}")


# Global instance
_evaluation_executor: Optional[SignalEvaluationExecutor] = None


def get_evaluation_executor() -> SignalEvaluationExecutor:
    """Get or create evaluation executor instance"""
    global _evaluation_executor
    if _evaluation_executor is None:
        _evaluation_executor = SignalEvaluationExecutor()
    return _evaluation_executor
