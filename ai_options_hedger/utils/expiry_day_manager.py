"""
Expiry Day Trading Restrictions Module
Prevents trading on expiry days after 11:30 AM unless ultra-high confidence
"""

from datetime import datetime, time
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)

class ExpiryDayManager:
    """Manages expiry day restrictions for options trading"""
    
    def __init__(self, cutoff_time: str = "11:30", min_confidence_on_expiry: float = 0.98):
        """
        Initialize expiry day manager
        
        Args:
            cutoff_time: Time after which trading is restricted on expiry days (HH:MM format)
            min_confidence_on_expiry: Minimum confidence required for trades after cutoff
        """
        self.cutoff_time = self._parse_time(cutoff_time)
        self.min_confidence_on_expiry = min_confidence_on_expiry
        self.instrument_expiry_dates: Dict[str, datetime] = {}
        
        logger.info(f"ExpiryDayManager initialized: cutoff={cutoff_time}, min_confidence={min_confidence_on_expiry}")
    
    def _parse_time(self, time_str: str) -> time:
        """Parse time string to time object"""
        try:
            hour, minute = map(int, time_str.split(':'))
            return time(hour=hour, minute=minute)
        except Exception as e:
            logger.error(f"Error parsing time {time_str}: {e}")
            return time(hour=11, minute=30)  # Default to 11:30
    
    def update_expiry_dates(self, options_chain_data: Dict[str, any]):
        """
        Update expiry dates from options chain data
        
        Args:
            options_chain_data: Options chain data containing expiry information
        """
        try:
            for instrument, chain_data in options_chain_data.items():
                if isinstance(chain_data, dict) and 'expiry' in chain_data:
                    expiry_date = chain_data['expiry']
                    if isinstance(expiry_date, str):
                        # Parse expiry date string (format: YYYY-MM-DD or DD-MMM-YYYY)
                        try:
                            expiry_dt = datetime.strptime(expiry_date, '%Y-%m-%d')
                        except:
                            try:
                                expiry_dt = datetime.strptime(expiry_date, '%d-%b-%Y')
                            except:
                                logger.warning(f"Could not parse expiry date {expiry_date} for {instrument}")
                                continue
                    elif isinstance(expiry_date, datetime):
                        expiry_dt = expiry_date
                    else:
                        continue
                    
                    self.instrument_expiry_dates[instrument] = expiry_dt
                    logger.debug(f"Updated expiry for {instrument}: {expiry_dt.date()}")
        
        except Exception as e:
            logger.error(f"Error updating expiry dates: {e}")
    
    def is_expiry_day(self, instrument: str, current_time: Optional[datetime] = None) -> bool:
        """
        Check if today is expiry day for the instrument
        
        Args:
            instrument: Instrument name (NIFTY, BANKNIFTY, SENSEX, FINNIFTY)
            current_time: Current datetime (defaults to now)
        
        Returns:
            True if today is expiry day
        """
        if current_time is None:
            current_time = datetime.now()
        
        if instrument not in self.instrument_expiry_dates:
            logger.warning(f"No expiry date found for {instrument}")
            return False
        
        expiry_date = self.instrument_expiry_dates[instrument]
        return current_time.date() == expiry_date.date()
    
    def is_trading_restricted(self, instrument: str, signal_confidence: float, 
                             current_time: Optional[datetime] = None) -> tuple[bool, str]:
        """
        Check if trading is restricted for the instrument
        
        Args:
            instrument: Instrument name
            signal_confidence: Confidence level of the trading signal
            current_time: Current datetime (defaults to now)
        
        Returns:
            Tuple of (is_restricted, reason)
        """
        if current_time is None:
            current_time = datetime.now()
        
        # Check if it's expiry day
        if not self.is_expiry_day(instrument, current_time):
            return False, "Not expiry day"
        
        # Check if current time is after cutoff
        current_time_only = current_time.time()
        if current_time_only < self.cutoff_time:
            return False, f"Before cutoff time ({self.cutoff_time})"
        
        # After cutoff on expiry day - check confidence
        if signal_confidence < self.min_confidence_on_expiry:
            reason = (f"Expiry day after {self.cutoff_time}: "
                     f"Confidence {signal_confidence:.2%} < required {self.min_confidence_on_expiry:.2%}")
            logger.warning(f"Trading restricted for {instrument}: {reason}")
            return True, reason
        
        # High confidence signal allowed even after cutoff
        logger.info(f"High confidence signal ({signal_confidence:.2%}) allowed on expiry day for {instrument}")
        return False, f"High confidence ({signal_confidence:.2%}) overrides expiry restriction"
    
    def get_expiry_info(self, instrument: str) -> Dict[str, any]:
        """Get expiry information for instrument"""
        if instrument not in self.instrument_expiry_dates:
            return {
                'has_expiry': False,
                'expiry_date': None,
                'is_expiry_day': False,
                'days_to_expiry': None
            }
        
        expiry_date = self.instrument_expiry_dates[instrument]
        current_time = datetime.now()
        is_expiry = current_time.date() == expiry_date.date()
        days_to_expiry = (expiry_date.date() - current_time.date()).days
        
        return {
            'has_expiry': True,
            'expiry_date': expiry_date,
            'is_expiry_day': is_expiry,
            'days_to_expiry': days_to_expiry,
            'cutoff_time': self.cutoff_time,
            'min_confidence_required': self.min_confidence_on_expiry if is_expiry else 0.95
        }
    
    def get_all_expiry_info(self) -> Dict[str, Dict]:
        """Get expiry information for all instruments"""
        return {
            instrument: self.get_expiry_info(instrument)
            for instrument in self.instrument_expiry_dates.keys()
        }
