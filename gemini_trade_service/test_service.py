import unittest
from unittest.mock import MagicMock, patch
import json
import os

# Set mock env vars before importing main
os.environ["GEMINI_API_KEY"] = "test_key"
os.environ["DHAN_CLIENT_ID"] = "test_id"
os.environ["DHAN_ACCESS_TOKEN"] = "test_token"

from main import app

class TestGeminiTradeService(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    @patch('main.dhan_client')
    @patch('main.call_gemini')
    def test_tick_flow_bullish(self, mock_call_gemini, mock_dhan_client):
        # 1. Mock Dhan Data
        mock_dhan_client.get_nifty_constituents_data.return_value = [{"symbol": "HDFCBANK", "percent_change": 1.5}]
        mock_dhan_client.get_nifty_index_data.return_value = {"current_price": 25000, "rsi": 55}
        mock_dhan_client.get_option_chain_data.return_value = {"pcr": 0.8}
        mock_dhan_client.get_india_vix.return_value = 12.0

        # 2. Mock Gemini Responses
        # Tier 1 Response
        tier1_resp = {
            "weighted_bias": "BULLISH",
            "strength_score": 8,
            "driver_sector": "BANKING",
            "reasoning": "Banks are strong."
        }
        
        # Tier 2 Response
        tier2_resp = {
            "trade_signal": "BUY_CALL",
            "suggested_strike": "25000 CE",
            "confidence": "HIGH"
        }
        
        # Tier 3 Response
        tier3_resp = {
            "final_decision": "GO",
            "veto_reason": None
        }

        # Configure side_effect to return these in order
        mock_call_gemini.side_effect = [tier1_resp, tier2_resp, tier3_resp]

        # 3. Call Endpoint
        response = self.app.post('/tick')
        data = response.get_json()

        # 4. Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(data['final_decision'], "GO")
        self.assertEqual(data['tier1']['weighted_bias'], "BULLISH")
        self.assertEqual(mock_call_gemini.call_count, 3) # Should call all 3 tiers

    @patch('main.dhan_client')
    @patch('main.call_gemini')
    def test_tick_flow_weak_signal(self, mock_call_gemini, mock_dhan_client):
        # 1. Mock Dhan Data
        mock_dhan_client.get_nifty_constituents_data.return_value = []
        
        # 2. Mock Gemini Responses
        # Tier 1 Response (Weak)
        tier1_resp = {
            "weighted_bias": "NEUTRAL",
            "strength_score": 4, # < 7
            "reasoning": "Market is chopping."
        }
        
        mock_call_gemini.side_effect = [tier1_resp]

        # 3. Call Endpoint
        response = self.app.post('/tick')
        data = response.get_json()

        # 4. Assertions
        self.assertEqual(response.status_code, 200)
        self.assertIn("Strength score too low", data['message'])
        self.assertEqual(mock_call_gemini.call_count, 1) # Should only call Tier 1

if __name__ == '__main__':
    unittest.main()
