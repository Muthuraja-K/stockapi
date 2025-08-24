import json

# Load the data
with open('earningsummary.json', 'r') as f:
    data = json.load(f)

print('📊 Earningsummary.json Status Report:')
print(f'✅ Total stocks: {len(data)}')

if data:
    sample = data[0]
    print('✅ Sample stock analysis:')
    print(f'   Ticker: {sample.get("ticker", "N/A")}')
    print(f'   Current Price: {sample.get("currentPrice", "N/A")}')
    print(f'   Earning Date: {sample.get("earningDate", "N/A")}')
    print(f'   Sector: {sample.get("sector", "N/A")}')
    print(f'   LastTwoEarnings count: {len(sample.get("lastTwoEarnings", []))}')
    
    if sample.get("lastTwoEarnings"):
        first_earning = sample["lastTwoEarnings"][0]
        print('✅ First earning data:')
        print(f'   - actualValue: {first_earning.get("actualValue", "N/A")}')
        print(f'   - expectedValue: {first_earning.get("expectedValue", "N/A")}')
        print(f'   - beatExpectation: {first_earning.get("beatExpectation", "N/A")}')
        print(f'   - percentageDifference: {first_earning.get("percentageDifference", "N/A")}')
        print(f'   - actualRevenue: {first_earning.get("actualRevenue", "N/A")}')
        print(f'   - expectedRevenue: {first_earning.get("expectedRevenue", "N/A")}')
        print(f'   - closeB4EarningPrice: {first_earning.get("closeB4EarningPrice", "N/A")}')
        print(f'   - afterEarningPrice: {first_earning.get("afterEarningPrice", "N/A")}')
else:
    print('❌ No data found in file')
