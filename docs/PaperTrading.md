# Class: `PaperTrading`

## Init
```python
pt = PaperTrading("./trading/data")
```
- Creates or uses the directory `./trading/data` for storing data (e.g., CSV or JSON files).
- If the directory doesn’t exist, create it.
- You may add optional parameters to specify formats, logging level, etc.

---

## Methods

### 1. Account

**`credit(amount)`**  
- Credits the account by `amount`.  
- Always returns `True`.  
- Records a credit transaction in the account ledger.

**`debit(amount)`**  
- Debits the account by `amount`.  
- Returns `False` if `amount` exceeds the current account balance (no partial debit). Otherwise, returns `True`.  
- Records a debit transaction in the account ledger.

---

### 2. Trading

**`buy(symbol, datetime, price, qty, note="", limit=None, tif="GTC")`**  
- Buys `qty` shares of `symbol` at `price`.  
- If `limit` is provided, this becomes a limit buy order; otherwise, it executes immediately (assuming sufficient funds).  
- **No partial fills**: If the account doesn’t have enough balance (`price * qty > account_balance`), the buy fails.  
- Optional `tif` (time-in-force), e.g., `"DAY"` or `"GTC"`:
  - `"DAY"` could auto-cancel at the end of the trading day.
  - `"GTC"` remains open until canceled or filled.
- Records the transaction in the position ledger.

**`close(symbol, datetime, price, qty, note="", limit=None, tif="GTC")`**  
- Closes (sells) `qty` shares of `symbol` at `price`.  
- If `limit` is provided, this becomes a limit sell order; otherwise, executes immediately.  
- **No partial fills**: If the account does not hold enough shares, the close operation fails.  
- Optional `tif` as above.  
- Records the transaction in the position ledger.

**`cancel(symbol, limit_price, qty, note="")`**  
- Cancels a specific open limit order (identified by `symbol`, `limit_price`, and `qty`).  
- Returns `True` if cancellation succeeds, `False` otherwise.  
- Records a cancellation in the position ledger.

**`cancelAll(symbol, note="")`**  
- Cancels **all** open limit orders for `symbol`.  
- Returns `True` if cancellation succeeds, `False` otherwise.  
- Records cancellations in the position ledger.

---

### 3. Getters

**`getAccountBalance()`**  
- Returns the uninvested cash balance as a `float`.

**`getAccountTransactions()`**  
- Returns a list (or DataFrame) of all credit/debit transactions in the account ledger.

**`getPortfolioValue()`**  
- Returns the current total value of the open positions (unrealized P/L).

**`getAccountValue()`**  
- Returns the sum of the cash balance and the portfolio value (i.e., the overall account value).

**`getAccountPNL()`**  
- Returns a dict with keys "value" (profit/loss in value) & "percent" (profit/loss in percent)

**`getSymbols(target="all")`**  
- Returns a unique list of symbols (as an array of strings).
  - `target="all"`: All symbols across open and closed positions.
  - `target="open"`: Symbols with open positions.
  - `target="closed"`: Symbols with fully closed positions.
  - `target="limit"`: Symbols that currently have open limit orders.

**`getPortfolio(as_dict=True)`**  
- If `as_dict=True`, returns a JSON-compatible list of dicts; otherwise returns a DataFrame.  
- Each record should include:
  - Symbol
  - Quantity held
  - Average cost
  - Current market value
  - Unrealized profit/loss (absolute and percentage)

**`getOpenLimitOrders(as_dict=True)`**  
- If `as_dict=True`, returns a JSON-compatible list of dicts; otherwise, a DataFrame.  
- Lists each open limit order with:
  - Symbol
  - Limit price
  - Qty
  - TIF
  - Order ID / any unique identifier
  - Notes, timestamps, etc.

---

### 4. `tick(data_df, datetime)`

- Accepts:
  - `data_df`: a DataFrame or dict-like structure with the latest prices for each symbol.
  - `datetime`: current market datetime for reference.
- **Actions**:
  1. **Execute limit orders** if the market price meets the limit condition (no partial fills):
     - Buy limit triggers if `market_price <= limit`.
     - Sell limit triggers if `market_price >= limit`.
     - If TIF is `"DAY"` and the trading day ends, auto-cancel any unfilled DAY orders.
  2. **Update the portfolio**:
     - Recalculate the value of open positions based on the new prices.
     - Track any realized gains/losses from fully executed orders.
- Records fills or cancellations in the position ledger as needed.

---

## Data Tracking

1. **Account Ledger**:
   - Stores all credits/debits with timestamps and amounts.
   - Reflects the current balance.

2. **Position Ledger**:
   - Records each buy, close, or cancel (and any limit orders).
   - Fields might include:
     - Unique `order_id`
     - `symbol`
     - `qty`
     - `price`
     - `type` (buy, sell, cancel, limit buy, limit sell)
     - `datetime`
     - `note`
   - Use these records to reconstruct trades and calculate realized P/L.

3. **Portfolio Records**:
   - Aggregates open positions:
     - Symbol, total qty, average cost, current market price, unrealized P/L
   - Could store or derive realized P/L for closed trades (or keep in a separate ledger).

4. **Format & Persistence**:
   - Data can be stored in CSV, JSON, or a small database.
   - You may store a “snapshot” after each transaction for easy restoration of state if needed.

---

## Advanced Considerations (Optional / Future)

- **Stop or Stop-Limit Orders**: Expand beyond just limit orders.  
- **Commissions & Slippage**: Deduct fixed or percentage-based fees, or simulate slippage for more realistic paper trading.  
- **Time In Force (Full Implementation)**: e.g., `DAY` vs. `GTC`, auto-cancel behavior, etc.  
- **Unique Order IDs**: Makes referencing and canceling specific orders easier.  
- **Margin & Short Selling**: Support leveraged accounts or opening short positions.  
- **Corporate Actions**: Handle dividends, splits, spin-offs if needed.  
- **Error Handling**: Decide on raising exceptions vs. returning error codes/booleans for invalid actions.  
