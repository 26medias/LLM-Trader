# LLM Trader

## Plan
### Code

- Data Context:
    - Earnings dates
    - Current prices
    - Price context
    - MarketCycle Context
    - News
    - Portfolio
    - Reddit Mentions
- Trading Sim
    - Buy
    - Sell
    - Call
    - Put
    - Value Tracking
    - Portfolio output

### Checks

- Earning Bets using Earnings dates
- EOD Bets
- Market Cycle Status & alerts

### Chain of Thoughts

#### Daily moves

- Stocks of interest:
    - Inputs:
        - News
        - Reddit Mentions
        - Current prices
        - Price context
        - MarketCycle Context
    - Outputs:
        - Stocks of interest:
            - symbol
            - reason
- Financial Screening:
    - For each symbol
        - Inputs:
            - Current prices
            - Price context
            - MarketCycle Context
            - Portfolio?
            - Earnings dates
            - Financials
        - Outputs:
            - Action:
                - Buy
                - Close
                - CancelLimit
                - CancelAllLimit
                - None

#### Portfolio
    - For each symbol
        - Inputs:
            - News
            - Current prices
            - Price context
            - MarketCycle Context
            - Portfolio Positions
            - Earnings dates
            - Financials
        - Outputs:
            - Action:
                - Buy
                - Close
                - CancelLimit
                - CancelAllLimit
                - None

## UI

Tabs        Actions
table       News
table       Charts
positions   Charts

### Tabs

- Reddit
    - Table:
        - Rank (Rank Change)
        - Ticker
        - Name
        - Mentions (Mention Change)
        - Upvotes
    - View:
        - News
        - MarketCycles
        - AI Recommendation
    - Actions:
        - Watchlist add/remove
        - Trading Buy(qty)/Sell(qty)/Close(qty)
    - Needs
        - RedditTracker.refresh()
        - RedditTracker.all()
            - MarketCycle.data()
- News
    - Table
        - Ticker
        - Name
        - Mentions
    - View
        - News
        - MarketCycles
        - AI Recommendations
- Watchlist
    - Table
        - Ticker
        - Name
        - MarketCycles
        - Reddit Rank (Rank Change)
        - Reddit Mentions (Mention Change)
        - Reddit Upvotes

Needs:
    - Init
        - Load News
        - Load Reddit
    - Views
        - Reddit
            - Reddit.all()

#### Classes

- GPT
- Screener
- MarketCycle
- PaperTrading
- NewsLoader
- WatchlistManager(data_dir)
    - add(ticker)
    - remove(ticker)
    - list() -> list of tickers
- RedditTracker
    - refresh()
    - all()
    - get()

#### Dashboard Class

Methods
    - Reddit
        - .reddit.refresh()
        - .reddit.all()
        - .reddit.get()
    - News
        - getAllNews()
        - getTickerNews()
    - MarketCycle
        - refresh()
        - build()
        - getMarketCycles()


## UI

Buttons
- Trending
    Selected:
        - [AI: Summary]
        - [AI: Actions]
        - [Buy]
        - [Sell]
        - [Add to watchlist] -> 
        - [Remove watchlist]

## tasks

- [ ] Integrate the watchlist
    - [ ] Load symbols
    - [ ] Load data related to symbols, write `buildWatchlist()` in `Dashboard`
- [ ] Download market data for SP500
    - [ ] Create SP500 watchlist
    - [ ] Load data related to symbols