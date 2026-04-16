import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import logging


class CTraderBot:
    def __init__(self, client_id, client_secret, access_token, account_id):
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.account_id = account_id
        self.base_url = "https://api.spotware.com"
        logging.basicConfig(level=logging.INFO)

    def _get_headers(self):
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    def get_access_token(self):
        token_url = f"{self.base_url}/connect/token"
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            self.access_token = response.json()["access_token"]
        else:
            response.raise_for_status()

    def place_order(
        self,
        symbol,
        volume,
        direction,
        order_type="LIMIT",
        price=None,
        take_profit=None,
        stop_loss=None,
    ):
        order_url = f"{self.base_url}/tradingaccounts/{self.account_id}/orders"
        order_data = {
            "direction": direction,
            "symbolName": symbol,
            "volume": volume,
            "orderType": order_type,
        }
        if price:
            order_data["limitPrice"] = price
        if take_profit:
            order_data["takeProfit"] = take_profit
        if stop_loss:
            order_data["stopLoss"] = stop_loss

        response = requests.post(
            order_url, headers=self._get_headers(), data=json.dumps(order_data)
        )
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(
                f"Failed to place order: {response.status_code} {response.text}"
            )
            response.raise_for_status()

    def modify_order(self, order_id, price=None, take_profit=None, stop_loss=None):
        modify_url = (
            f"{self.base_url}/tradingaccounts/{self.account_id}/orders/{order_id}"
        )
        order_data = {}
        if price:
            order_data["limitPrice"] = price
        if take_profit:
            order_data["takeProfit"] = take_profit
        if stop_loss:
            order_data["stopLoss"] = stop_loss

        response = requests.put(
            modify_url, headers=self._get_headers(), data=json.dumps(order_data)
        )
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(
                f"Failed to modify order: {response.status_code} {response.text}"
            )
            response.raise_for_status()

    def cancel_order(self, order_id):
        cancel_url = (
            f"{self.base_url}/tradingaccounts/{self.account_id}/orders/{order_id}"
        )
        response = requests.delete(cancel_url, headers=self._get_headers())
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(
                f"Failed to cancel order: {response.status_code} {response.text}"
            )
            response.raise_for_status()

    def fetch_dataframe(self, symbol, start_time, end_time, timeframe="H1"):
        candles_url = f"{self.base_url}/chart/v1/candles"
        params = {
            "symbolName": symbol,
            "startTime": int(start_time.timestamp() * 1000),
            "endTime": int(end_time.timestamp() * 1000),
            "timeFrame": timeframe,
        }

        response = requests.get(candles_url, headers=self._get_headers(), params=params)
        if response.status_code == 200:
            data = response.json()
            candles = data["candles"]
            df = pd.DataFrame(candles)
            df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
            df.set_index("timestamp", inplace=True)
            return df
        else:
            logging.error(
                f"Failed to fetch data: {response.status_code} {response.text}"
            )
            response.raise_for_status()

    def get_account_equity(self):
        equity_url = f"{self.base_url}/tradingaccounts/{self.account_id}/balance"
        response = requests.get(equity_url, headers=self._get_headers())
        if response.status_code == 200:
            return response.json()["equity"]
        else:
            logging.error(
                f"Failed to fetch account equity: {response.status_code} {response.text}"
            )
            response.raise_for_status()

    def get_account_information(self):
        account_url = f"{self.base_url}/tradingaccounts/{self.account_id}"
        response = requests.get(account_url, headers=self._get_headers())
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(
                f"Failed to fetch account information: {response.status_code} {response.text}"
            )
            response.raise_for_status()

    def get_open_positions(self):
        positions_url = f"{self.base_url}/tradingaccounts/{self.account_id}/positions"
        response = requests.get(positions_url, headers=self._get_headers())
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(
                f"Failed to fetch open positions: {response.status_code} {response.text}"
            )
            response.raise_for_status()

    def get_open_orders(self):
        orders_url = f"{self.base_url}/tradingaccounts/{self.account_id}/orders"
        response = requests.get(orders_url, headers=self._get_headers())
        if response.status_code == 200:
            return response.json()
        else:
            logging.error(
                f"Failed to fetch open orders: {response.status_code} {response.text}"
            )
            response.raise_for_status()

    def calculate_technical_indicators(self, df):
        # Example: Calculate Moving Average
        df["MA20"] = df["close"].rolling(window=20).mean()
        return df
