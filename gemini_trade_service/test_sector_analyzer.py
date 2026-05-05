
import asyncio
import logging
import sys
from sector_analyzer import sector_analyzer

# Configure logging to print to stdout
logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)

async def test_analysis():
    print("--- Testing BANKNIFTY Analysis ---")
    try:
        bank_data = await sector_analyzer.analyze_banknifty_stocks()
        if bank_data and 'stocks' in bank_data:
            print(f"Success! Found {len(bank_data['stocks'])} stocks.")
            print(f"Bias: {bank_data.get('weighted_bias')}")
            print(f"Top Movers: {bank_data.get('top_movers')}")
        else:
            print("Failed: No data returned or missing 'stocks' key.")
            print(f"Data: {bank_data}")
    except Exception as e:
        print(f"Exception during BANKNIFTY analysis: {e}")

    print("\n--- Testing FINNIFTY Analysis ---")
    try:
        fin_data = await sector_analyzer.analyze_finnifty_stocks()
        if fin_data and 'stocks' in fin_data:
            print(f"Success! Found {len(fin_data['stocks'])} stocks.")
            print(f"Bias: {fin_data.get('weighted_bias')}")
            print(f"Leading Sector: {fin_data.get('leading_sector')}")
        else:
            print("Failed: No data returned or missing 'stocks' key.")
            print(f"Data: {fin_data}")
    except Exception as e:
        print(f"Exception during FINNIFTY analysis: {e}")

if __name__ == "__main__":
    asyncio.run(test_analysis())
