import os
import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Union

# Optional: for DataFrame support in getters
try:
    import pandas as pd
except ImportError:
    pd = None


class PaperTrading:
    def __init__(
        self,
        data_dir: str,
        file_format: str = "json",
        logging_level: int = logging.INFO,
    ):
        """
        Initialize the paper trading system.
          - data_dir: directory to store account and trade data.
          - file_format: format used for persistence (currently JSON for objects).
          - logging_level: set the logging level.
        Creates the directory if it does not exist.
        If persisted data exists, recovers balances, portfolio, positions, and orders.
        """
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        logging.basicConfig(level=logging_level)

        # Define file paths for persistence
        self.settings_file = os.path.join(self.data_dir, "settings.json")
        self.account_transactions_file = os.path.join(self.data_dir, "account_transactions.json")
        self.position_ledger_file = os.path.join(self.data_dir, "position_ledger.json")
        self.positions_file = os.path.join(self.data_dir, "positions.json")
        self.open_limit_orders_file = os.path.join(self.data_dir, "open_limit_orders.json")

        # Account funds and transactions
        self.cash_balance: float = 0.0
        self.account_transactions: List[Dict[str, Any]] = []  # credit/debit ledger

        # Ledger for executed orders, limit orders, cancellations, etc.
        self.position_ledger: List[Dict[str, Any]] = []

        # Positions: mapping symbol -> dict {qty, average_cost, current_price}
        self.positions: Dict[str, Dict[str, Any]] = {}

        # Open limit orders (both buy and sell) waiting to be filled.
        self.open_limit_orders: List[Dict[str, Any]] = []

        # Unique order id counter
        self.next_order_id: int = 1

        # Load previously saved state, if available.
        self._load_state()

    # ----------------------
    # Persistence Methods
    # ----------------------
    def _save_state(self) -> None:
        """Save current state to files in the data directory."""
        settings = {"cash_balance": self.cash_balance, "next_order_id": self.next_order_id}
        with open(self.settings_file, "w") as f:
            json.dump(settings, f)

        with open(self.account_transactions_file, "w") as f:
            json.dump(self.account_transactions, f, default=str)

        with open(self.position_ledger_file, "w") as f:
            json.dump(self.position_ledger, f, default=str)

        with open(self.positions_file, "w") as f:
            json.dump(self.positions, f, default=str)

        with open(self.open_limit_orders_file, "w") as f:
            json.dump(self.open_limit_orders, f, default=str)

    def _load_state(self) -> None:
        """Load saved state from files if they exist."""
        if os.path.exists(self.settings_file):
            with open(self.settings_file, "r") as f:
                settings = json.load(f)
                self.cash_balance = settings.get("cash_balance", 0.0)
                self.next_order_id = settings.get("next_order_id", 1)

        if os.path.exists(self.account_transactions_file):
            with open(self.account_transactions_file, "r") as f:
                self.account_transactions = json.load(f)

        if os.path.exists(self.position_ledger_file):
            with open(self.position_ledger_file, "r") as f:
                self.position_ledger = json.load(f)

        if os.path.exists(self.positions_file):
            with open(self.positions_file, "r") as f:
                self.positions = json.load(f)

        if os.path.exists(self.open_limit_orders_file):
            with open(self.open_limit_orders_file, "r") as f:
                self.open_limit_orders = json.load(f)

    # ----------------------
    # 1. Account Methods
    # ----------------------
    def credit(self, amount: float, note: str = "") -> bool:
        """Credits the account by the given amount and records the transaction."""
        self.cash_balance += amount
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "type": "credit",
            "amount": amount,
            "note": note,
        }
        self.account_transactions.append(transaction)
        logging.info(f"Credited {amount}. New balance: {self.cash_balance}.")
        self._save_state()
        return True

    def debit(self, amount: float, note: str = "") -> bool:
        """
        Debits the account by the given amount.
        Returns False if funds are insufficient.
        """
        if self.cash_balance < amount:
            logging.warning("Insufficient funds for debit.")
            return False
        self.cash_balance -= amount
        transaction = {
            "timestamp": datetime.now().isoformat(),
            "type": "debit",
            "amount": amount,
            "note": note,
        }
        self.account_transactions.append(transaction)
        logging.info(f"Debited {amount}. New balance: {self.cash_balance}.")
        self._save_state()
        return True

    # ----------------------
    # 2. Trading Methods
    # ----------------------
    def buy(
        self,
        symbol: str,
        dt: datetime,
        price: float,
        qty: int,
        note: str = "",
        limit: Union[float, None] = None,
        tif: str = "GTC",
    ) -> bool:
        """
        Buys qty shares of symbol at price.
        If limit is provided, creates a limit buy order.
        Otherwise, executes immediately (if funds available).
        """
        if limit is not None:
            order = {
                "order_id": self.next_order_id,
                "symbol": symbol,
                "qty": qty,
                "limit": limit,
                "order_type": "limit_buy",
                "tif": tif,
                "datetime": dt.isoformat(),
                "note": note,
            }
            self.next_order_id += 1
            self.open_limit_orders.append(order)
            self.position_ledger.append({**order, "type": "limit_buy_order"})
            logging.info(f"Created limit buy order: {order}")
            self._save_state()
            return True
        else:
            cost = price * qty
            if self.cash_balance < cost:
                logging.warning("Insufficient funds for immediate buy.")
                return False
            if not self.debit(cost, note=f"Buy {qty} of {symbol} at {price}"):
                return False
            self._update_position(symbol, qty, price)
            trade = {
                "order_id": self.next_order_id,
                "symbol": symbol,
                "qty": qty,
                "price": price,
                "type": "buy",
                "datetime": dt.isoformat(),
                "note": note,
            }
            self.next_order_id += 1
            self.position_ledger.append(trade)
            logging.info(f"Executed immediate buy: {trade}")
            self._save_state()
            return True

    def close(
        self,
        symbol: str,
        dt: datetime,
        price: float,
        qty: int,
        note: str = "",
        limit: Union[float, None] = None,
        tif: str = "GTC",
    ) -> bool:
        """
        Closes (sells) qty shares of symbol at price.
        If limit is provided, creates a limit sell order.
        Otherwise, executes immediately (if shares available).
        """
        if symbol not in self.positions or int(self.positions[symbol].get("qty", 0)) < qty:
            logging.warning("Not enough shares to close.")
            return False

        if limit is not None:
            order = {
                "order_id": self.next_order_id,
                "symbol": symbol,
                "qty": qty,
                "limit": limit,
                "order_type": "limit_sell",
                "tif": tif,
                "datetime": dt.isoformat(),
                "note": note,
            }
            self.next_order_id += 1
            self.open_limit_orders.append(order)
            self.position_ledger.append({**order, "type": "limit_sell_order"})
            logging.info(f"Created limit sell order: {order}")
            self._save_state()
            return True
        else:
            # Immediate execution: reduce shares and credit proceeds.
            self.positions[symbol]["qty"] = int(self.positions[symbol]["qty"]) - qty
            proceeds = price * qty
            self.credit(proceeds, note=f"Close {qty} of {symbol} at {price}")
            trade = {
                "order_id": self.next_order_id,
                "symbol": symbol,
                "qty": qty,
                "price": price,
                "type": "sell",
                "datetime": dt.isoformat(),
                "note": note,
            }
            self.next_order_id += 1
            self.position_ledger.append(trade)
            logging.info(f"Executed immediate close: {trade}")
            self._save_state()
            return True

    def cancel(self, symbol: str, limit_price: float, qty: int, note: str = "") -> bool:
        """
        Cancels a specific open limit order (by symbol, limit price, and qty).
        Returns True if cancellation succeeds, False otherwise.
        """
        order_to_cancel = None
        for order in self.open_limit_orders:
            if order["symbol"] == symbol and order["limit"] == limit_price and order["qty"] == qty:
                order_to_cancel = order
                break
        if order_to_cancel:
            self.open_limit_orders.remove(order_to_cancel)
            cancellation = {
                "order_id": order_to_cancel["order_id"],
                "symbol": symbol,
                "qty": qty,
                "price": limit_price,
                "type": "cancel",
                "datetime": datetime.now().isoformat(),
                "note": note,
            }
            self.position_ledger.append(cancellation)
            logging.info(f"Cancelled order: {cancellation}")
            self._save_state()
            return True
        else:
            logging.warning("Order to cancel not found.")
            return False

    def cancelAll(self, symbol: str, note: str = "") -> bool:
        """
        Cancels all open limit orders for the given symbol.
        Returns True if cancellation succeeds, False otherwise.
        """
        orders_to_cancel = [order for order in self.open_limit_orders if order["symbol"] == symbol]
        if not orders_to_cancel:
            logging.info("No open limit orders found for symbol to cancel.")
            return False
        for order in orders_to_cancel:
            self.open_limit_orders.remove(order)
            cancellation = {
                "order_id": order["order_id"],
                "symbol": symbol,
                "qty": order["qty"],
                "price": order["limit"],
                "type": "cancel",
                "datetime": datetime.now().isoformat(),
                "note": note + " - cancelAll",
            }
            self.position_ledger.append(cancellation)
            logging.info(f"Cancelled order: {cancellation}")
        self._save_state()
        return True

    # ----------------------
    # 3. Getter Methods
    # ----------------------
    def getAccountBalance(self) -> float:
        """Returns the uninvested cash balance."""
        return self.cash_balance

    def getAccountTransactions(self) -> List[Dict[str, Any]]:
        """Returns a list of all credit/debit transactions."""
        return self.account_transactions

    def getPortfolioValue(self) -> float:
        """
        Returns the total market value of open positions.
        Uses the latest current_price if available; otherwise falls back to average_cost.
        """
        total_value = 0.0
        for pos in self.positions.values():
            price = pos.get("current_price", pos.get("average_cost", 0))
            total_value += int(pos.get("qty", 0)) * float(price)
        return total_value

    def getAccountValue(self) -> float:
        """Returns the overall account value (cash + portfolio)."""
        return self.cash_balance + self.getPortfolioValue()

    def getAccountPNL(self) -> Dict[str, float]:
        """
        Returns profit/loss as a dict with keys "value" and "percent".
        PNL is calculated as (account value - net deposits), where net deposits
        equals total credits minus total debits.
        """
        total_credits = sum(tx["amount"] for tx in self.account_transactions if tx["type"] == "credit")
        total_debits = sum(tx["amount"] for tx in self.account_transactions if tx["type"] == "debit")
        net_investment = total_credits - total_debits
        account_value = self.getAccountValue()
        pnl_value = account_value - net_investment
        pnl_percent = (pnl_value / net_investment * 100) if net_investment != 0 else 0.0
        return {"value": pnl_value, "percent": pnl_percent}

    def getSymbols(self, target: str = "all") -> List[str]:
        """
        Returns a unique list of symbols.
          - target="all": All symbols in the position ledger.
          - target="open": Symbols with open positions.
          - target="closed": Symbols with fully closed positions.
          - target="limit": Symbols with open limit orders.
        """
        symbols_set = set()
        if target == "all":
            for entry in self.position_ledger:
                symbols_set.add(entry["symbol"])
        elif target == "open":
            for symbol, pos in self.positions.items():
                if int(pos.get("qty", 0)) > 0:
                    symbols_set.add(symbol)
        elif target == "closed":
            for symbol, pos in self.positions.items():
                if int(pos.get("qty", 0)) == 0:
                    symbols_set.add(symbol)
        elif target == "limit":
            for order in self.open_limit_orders:
                symbols_set.add(order["symbol"])
        return list(symbols_set)

    def getPortfolio(self, as_dict: bool = True) -> Union[List[Dict[str, Any]], Any]:
        """
        Returns portfolio records.
          Each record includes: symbol, quantity held, average cost,
          current market price, market value, and unrealized profit/loss.
          If as_dict is False and pandas is installed, returns a DataFrame.
        """
        portfolio = []
        for symbol, pos in self.positions.items():
            qty = int(pos.get("qty", 0))
            if qty != 0:
                current_price = float(pos.get("current_price", pos.get("average_cost", 0)))
                average_cost = float(pos.get("average_cost", 0))
                market_value = qty * current_price
                cost_basis = qty * average_cost
                unrealized_pl = market_value - cost_basis
                unrealized_pl_percent = (unrealized_pl / cost_basis * 100) if cost_basis != 0 else 0.0
                portfolio.append({
                    "symbol": symbol,
                    "quantity": qty,
                    "average_cost": average_cost,
                    "current_price": current_price,
                    "market_value": market_value,
                    "unrealized_pl": unrealized_pl,
                    "unrealized_pl_percent": unrealized_pl_percent,
                })
        if as_dict:
            return portfolio
        else:
            if pd:
                return pd.DataFrame(portfolio)
            else:
                logging.warning("pandas is not installed; returning list of dicts.")
                return portfolio

    def getOpenLimitOrders(self, as_dict: bool = True) -> Union[List[Dict[str, Any]], Any]:
        """
        Returns open limit orders.
          Each order includes: symbol, limit price, qty, TIF, order_id, notes, timestamp, etc.
          If as_dict is False and pandas is installed, returns a DataFrame.
        """
        orders = self.open_limit_orders.copy()
        if as_dict:
            return orders
        else:
            if pd:
                return pd.DataFrame(orders)
            else:
                logging.warning("pandas is not installed; returning list of dicts.")
                return orders

    # ----------------------
    # 4. Tick Method
    # ----------------------
    def tick(self, data_df: Union[Dict[str, float], Any], current_dt: datetime) -> None:
        """
        Processes a market tick update:
          1. Checks each open limit order against the market price.
             - For limit buys: executes if market_price <= limit.
             - For limit sells: executes if market_price >= limit.
             - No partial fills.
          2. Auto-cancels unfilled "DAY" orders at market close (assumed at 16:00).
          3. Updates the current market price for open positions.
        Parameters:
          - data_df: dict or DataFrame with latest prices (key: symbol, value: price).
          - current_dt: current market datetime.
        """
        # Assume market close at 16:00 local time.
        market_close_time = current_dt.replace(hour=16, minute=0, second=0, microsecond=0)
        orders_to_remove = []

        for order in self.open_limit_orders.copy():
            symbol = order["symbol"]
            # Retrieve market price from dict or DataFrame.
            if isinstance(data_df, dict):
                market_price = data_df.get(symbol)
            else:
                try:
                    market_price = data_df.loc[symbol, "price"]
                except Exception:
                    logging.warning(f"Market price for {symbol} not found in tick data.")
                    continue
            if market_price is None:
                continue

            executed = False

            if order["order_type"] == "limit_buy":
                if market_price <= order["limit"]:
                    cost = order["qty"] * order["limit"]
                    if self.cash_balance >= cost:
                        self.debit(cost, note=f"Limit Buy executed for order {order['order_id']}")
                        self._update_position(symbol, order["qty"], order["limit"])
                        execution = {
                            "order_id": order["order_id"],
                            "symbol": symbol,
                            "qty": order["qty"],
                            "price": order["limit"],
                            "type": "limit_buy_executed",
                            "datetime": current_dt.isoformat(),
                            "note": order.get("note", ""),
                        }
                        self.position_ledger.append(execution)
                        logging.info(f"Executed limit buy: {execution}")
                        executed = True
                    else:
                        logging.warning(f"Insufficient funds to execute limit buy order {order['order_id']}.")

            elif order["order_type"] == "limit_sell":
                if market_price >= order["limit"]:
                    if symbol in self.positions and int(self.positions[symbol].get("qty", 0)) >= order["qty"]:
                        self.positions[symbol]["qty"] = int(self.positions[symbol]["qty"]) - order["qty"]
                        proceeds = order["qty"] * order["limit"]
                        self.credit(proceeds, note=f"Limit Sell executed for order {order['order_id']}")
                        execution = {
                            "order_id": order["order_id"],
                            "symbol": symbol,
                            "qty": order["qty"],
                            "price": order["limit"],
                            "type": "limit_sell_executed",
                            "datetime": current_dt.isoformat(),
                            "note": order.get("note", ""),
                        }
                        self.position_ledger.append(execution)
                        logging.info(f"Executed limit sell: {execution}")
                        executed = True
                    else:
                        logging.warning(f"Not enough shares to execute limit sell order {order['order_id']}.")

            # Auto-cancel DAY orders if market has closed and order is not executed.
            if order["tif"] == "DAY" and current_dt >= market_close_time and not executed:
                cancellation = {
                    "order_id": order["order_id"],
                    "symbol": symbol,
                    "qty": order["qty"],
                    "price": order["limit"],
                    "type": "limit_order_cancelled",
                    "datetime": current_dt.isoformat(),
                    "note": "DAY order auto-cancelled at market close",
                }
                self.position_ledger.append(cancellation)
                logging.info(f"Auto-cancelled DAY order: {cancellation}")
                orders_to_remove.append(order)
            if executed:
                orders_to_remove.append(order)

        # Remove orders that have been executed or cancelled.
        for order in orders_to_remove:
            if order in self.open_limit_orders:
                self.open_limit_orders.remove(order)

        # Update current market prices for all positions.
        for symbol, pos in self.positions.items():
            if isinstance(data_df, dict):
                price = data_df.get(symbol, pos.get("current_price", pos.get("average_cost", 0)))
            else:
                try:
                    price = data_df.loc[symbol, "price"]
                except Exception:
                    price = pos.get("current_price", pos.get("average_cost", 0))
            pos["current_price"] = price

        self._save_state()

    # ----------------------
    # Helper Methods
    # ----------------------
    def _update_position(self, symbol: str, qty: int, price: float) -> None:
        """
        Updates positions when a buy (or limit buy fill) is executed.
        Calculates a new weighted average cost.
        """
        if symbol in self.positions:
            pos = self.positions[symbol]
            current_qty = int(pos.get("qty", 0))
            new_qty = current_qty + qty
            total_cost = float(pos.get("average_cost", 0)) * current_qty + price * qty
            new_avg = total_cost / new_qty if new_qty != 0 else 0.0
            pos["qty"] = new_qty
            pos["average_cost"] = new_avg
            pos["current_price"] = price
        else:
            self.positions[symbol] = {"qty": qty, "average_cost": price, "current_price": price}


# ----------------------
# Example of Use
# ----------------------
if __name__ == "__main__":
    # Initialize paper trading system (state will be stored in "./trading/data")
    pt = PaperTrading("./trading/data", logging_level=logging.DEBUG)

    # Credit the account with $10,000
    pt.credit(10000, note="Initial deposit")

    # Execute an immediate buy: 10 shares of AAPL at $150 each.
    pt.buy("AAPL", datetime.now(), 150, 10, note="Buy AAPL immediate")

    # Place a limit buy order: 1 share of GOOG with a limit price of $2750, valid for the day.
    pt.buy("GOOG", datetime.now(), 2800, 1, note="Limit buy GOOG", limit=2750, tif="DAY")

    # Execute an immediate sell (close) of 5 shares of AAPL at $155 each.
    pt.close("AAPL", datetime.now(), 155, 5, note="Sell some AAPL immediate")

    # Simulate a market tick update.
    tick_data = {"GOOG": 2745, "AAPL": 156}
    pt.tick(tick_data, datetime.now())

    # Print account balance, portfolio details, and open limit orders.
    print("Account Balance:", pt.getAccountBalance())
    print("Portfolio:", pt.getPortfolio())
    print("Open Limit Orders:", pt.getOpenLimitOrders())
    print("Account PNL:", pt.getAccountPNL())
