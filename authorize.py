import os
import requests
import json
from dotenv import load_dotenv, set_key

def authorize():
    load_dotenv()
    app_id = os.getenv("CT_APP_ID")
    app_secret = os.getenv("CT_APP_SECRET")
    
    if not app_id or not app_secret:
        print("Error: CT_APP_ID and CT_APP_SECRET must be set in .env")
        return

    redirect_uri = "http://localhost"
    
    # Generate OAuth URL
    auth_url = f"https://openapi.ctrader.com/apps/auth?client_id={app_id}&redirect_uri={redirect_uri}&scope=trading"
    
    print("\n" + "="*60)
    print("STEP 1: CTrader Open API Authorization")
    print("="*60)
    print("\nPlease open the following URL in your web browser:")
    print(f"\n{auth_url}\n")
    print("Log in to your Demo Account and click 'Allow access'.")
    print("You will be redirected back to an address that looks like:")
    print("http://localhost/?code=abc123xyz...")
    print("\n(Your browser might say 'This site can’t be reached' — this is fully expected!)")
    
    code = input("\nSTEP 2: Look at the URL in your browser and paste ONLY the exact code (e.g., abc123xyz): ").strip()
    
    if not code:
        print("No code entered. Aborting.")
        return
        
    print("\nExchanging code for Access Token...")
    token_url = "https://openapi.ctrader.com/apps/token"
    payload = {
        "grant_type": "authorization_code",
        "client_id": app_id,
        "client_secret": app_secret,
        "redirect_uri": redirect_uri,
        "code": code
    }
    
    response = requests.post(token_url, data=payload)
    if response.status_code != 200:
        print(f"Failed to get token. Error {response.status_code}: {response.text}")
        return
        
    data = response.json()
    access_token = data.get("accessToken")
    refresh_token = data.get("refreshToken")
    
    print("✓ Access Token Acquired.")
    
    # Save tokens
    env_path = ".env"
    set_key(env_path, "CT_ACCESS_TOKEN", access_token)
    set_key(env_path, "CT_REFRESH_TOKEN", refresh_token)
    
    print("\nSTEP 3: Fetching permitted Trading Accounts...")
    # Get Accounts
    accounts_url = f"https://api.spotware.com/connect/tradingaccounts?oauth_token={access_token}"
    
    acc_response = requests.get(accounts_url)
    if acc_response.status_code != 200:
        print(f"Failed to fetch accounts. Error {acc_response.status_code}: {acc_response.text}")
        print("Cannot extract account ID.")
        return
        
    accounts_data = acc_response.json()
    accounts = accounts_data if isinstance(accounts_data, list) else accounts_data.get("accountId", [])
    
    if not accounts:    
        print("No accounts associated with this authorize. Please ensure you have a demo account.")
        return
        
    print(f"Found Accounts: {accounts}")
    
    target_account = None
    if isinstance(accounts, list) and isinstance(accounts[0], dict):
       # E.g. [{"accountId": 123456}]
       target_account = accounts[0].get("accountId")
    elif isinstance(accounts, list) and isinstance(accounts[0], int):
       target_account = accounts[0]
       
    if target_account:
        print(f"✓ Selecting Account ID: {target_account}")
        set_key(env_path, "CT_ACCOUNT_ID", str(target_account))
        print("\nAll Credentials Successfully Saved to .env!")
        print("You are ready to run the Backtester!")
    else:
        print("Could not parse account ID from response", accounts_data)

if __name__ == "__main__":
    authorize()
