import requests

def check_auto_result():
    url = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
    
    # Sila sites-ku POST request thevai padum (eg: {"pageNo": 1, "pageSize": 10})
    # Ithu standard GET request format
    try:
        response = requests.get(url, timeout=5)
        data = response.json()
        
        # JSON-la irunthu latest period & number edukka (Unga site API padi keys-a mathikonga)
        # Example structure logic:
        latest_record = data.get("data", {}).get("list", [])[0]
        
        period = str(latest_record.get("issueNumber"))
        number = int(latest_record.get("number"))
        
        return period, number
    except Exception as e:
        print(f"API Fetch Error: {e}")
        return None, None
