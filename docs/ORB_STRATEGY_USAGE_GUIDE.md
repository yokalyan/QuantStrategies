# TQQQ Midpoint-Stop ORB Strategy — Complete Beginner's Usage Guide

This guide explains how the **TQQQ Midpoint-Stop Opening Range Breakout (ORB)** intraday strategy works in plain, simple terms, complete with real-number examples and instructions for running it.

---

## 1. The Big Picture (Core Philosophy)

### What is TQQQ?
**TQQQ (ProShares UltraPro QQQ)** is a **3x leveraged ETF** that tracks the Nasdaq 100 index. If tech stocks rally +1%, TQQQ jumps roughly +3%. If tech stocks drop -1%, TQQQ drops roughly -3%. Because of this leverage, the market produces sharp, explosive intraday momentum swings right after the opening bell.

### What is an Opening Range Breakout (ORB)?
When the New York Stock Exchange opens at **9:30 AM ET**, institutional orders, overnight news, and market makers flood the tape. During the first **5 minutes** (9:30 AM – 9:35 AM), price creates a temporary boundary called the **Opening Range (The Box)**:
* **High:** The highest price printed.
* **Low:** The lowest price printed.
* **Midpoint:** Exactly halfway between the High and Low.

The breakout principle states: **When price forcefully breaks out of this initial 5-minute box in the direction of the opening candle, it often triggers a sustained intraday trend.**

```
       9:30 AM                      9:35 AM                                 10:30 AM            15:30 PM
          |----------------------------|---------------------------------------|-------------------|
               First 5 Minutes                      Entry Window                   Cutoff          Auto-Flatten
              (Build the "Box")              (Wait for Breakout Trigger)        (Cancel orders)   (Close to Cash)
```

### The Key Innovation: The "Midpoint Stop"
Traditional ORB strategies place the stop loss all the way at the **opposite side of the box** (e.g. buy at the High, stop at the Low). On a 3x leveraged ETF, that risk is far too wide—a failed breakout inflicts deep losses.

This strategy cuts that risk in half by placing the stop loss at the **Midpoint (`(High + Low) / 2`)**.
* **Cuts dollar risk per share by 50%**.
* Allows us to buy **twice as many shares** while keeping our total dollar risk small and constant.
* Turns what would normally be modest gains into **massive Risk/Reward multiples (up to 10R)**.

---

## 2. Daily Timeline & Rules

| Step | Time (ET) | Action | Rule |
| :--- | :--- | :--- | :--- |
| **1. Measure Range** | 09:30 – 09:35 | Measure the 5-min candle | Calculate `High`, `Low`, and `Midpoint`. Determine direction: **Bullish** if Close ≥ Open, **Bearish** if Close < Open. |
| **2. Volatility Filter** | 09:35 | Check OR / ATR Ratio | Range must be between **15% and 25%** (`0.15 – 0.25`) of the 20-day Average True Range (ATR20). |
| **3. Arm Bracket** | 09:35 – 10:30 | Place Contingent Stop Order | **Bullish:** BUY STOP at High, Stop at Midpoint.<br>**Bearish:** SELL SHORT STOP at Low, Stop at Midpoint. |
| **4. Entry Cutoff** | 10:30 | Cancel unfilled orders | If no breakout occurs by 10:30, cancel order. Do not enter late in the midday chop. |
| **5. Breakeven Shield** | During Trade | Ratchet Stop at +6.0R | If price moves +6.0R in our favor, slide Stop Loss up to Entry price (**Risk = $0**). |
| **6. Profit Target** | During Trade | Limit exit at +10.0R | Capture full 10x reward on the initial risk. |
| **7. EOD Flatten** | 15:30 (3:30 PM) | Liquidate to cash | Close any remaining position. **Never hold overnight.** |

---

## 3. The "Goldilocks" Volatility Filter Explained

The bot evaluates the ratio of the 5-minute range to the 20-day daily ATR:
$$\text{Ratio} = \frac{\text{Opening Range (High} - \text{Low)}}{\text{20-Day Daily ATR}}$$

```
[  < 0.15 : COMPRESSED  ]   |==== 0.15 — 0.25 : SWEET SPOT (TRADE) ====|   [  > 0.25 : EXHAUSTED  ]
     Chop / Low Energy                    High-Probability Trend                  Exhaustion / Too Late
      ⛔ STAND DOWN                              ✅ TRADE ARMED                        ⛔ STAND DOWN
```

1. **Below 0.15 (Compressed / Choppy):**
   * The opening range is unnaturally tight.
   * *Danger:* False breakouts and whipsaws. The engine **stands down**.
2. **0.15 to 0.25 (The Sweet Spot):**
   * Healthy expansion without blowing out the day's total range.
   * *Opportunity:* Clean directional trending. The engine **arms the bracket**.
3. **Above 0.25 (Exhausted / Wild):**
   * Huge opening candle (e.g., massive news gap).
   * *Danger:* The stock already burned through its daily fuel. Entering here often leads to immediate mean-reversion pullbacks. The engine **stands down**.

---

## 4. Real-World Walkthrough Examples

### Example 1: TQQQ Moves UP (Bullish Winning Trade)

Suppose your account has **$5,000** capital, with a **0.6% risk budget** ($30 total risk).

* **09:30 – 09:35 AM Action:**
  * Opens at **$82.00**, dips to **$81.70**, rallies to High of **$82.70**, closes at **$82.50**.
  * Direction: **Bullish** (Close $82.50 > Open $82.00).
  * High = **$82.70**, Low = **$81.70** $\rightarrow$ Range = **$1.00**.
  * Midpoint = $\frac{82.70 + 81.70}{2} = \mathbf{\$82.20}$.
  * 20-day Daily ATR = **$5.00** $\rightarrow$ Ratio = $\frac{\$1.00}{\$5.00} = \mathbf{0.20}$ *(Passes filter!)*.
* **Calculated Bracket Order:**
  * **Risk per Share (1.0R):** $\$82.70 - \$82.20 = \mathbf{\$0.50}$.
  * **Share Size:** $\frac{\$30\text{ budget}}{\$0.50\text{ risk}} = \mathbf{60\text{ shares}}$ (Notional = $4,962, well within 4x leverage).
  * **Entry Trigger:** BUY STOP 60 shares @ **$82.70**.
  * **Initial Stop Loss:** SELL 60 shares @ **$82.20** (1.0R risk = -$30).
  * **Breakeven Trigger:** $\$82.70 + (6.0 \times \$0.50) = \mathbf{\$85.70}$ (+6.0R).
  * **Profit Target:** $\$82.70 + (10.0 \times \$0.50) = \mathbf{\$87.70}$ (+10.0R = +$300).

* **How the trade unfolds:**
  1. **09:42 AM:** Buyers surge into Nasdaq; TQQQ hits **$82.70** $\rightarrow$ **FILLED LONG 60 shares**.
  2. **11:05 AM:** Strong momentum pushes TQQQ to **$85.70** (+6.0R). The engine immediately triggers the **Breakeven Shield**, moving the stop loss from $82.20 up to **$82.70**. The trade is now **100% risk-free**.
  3. **02:15 PM:** TQQQ touches **$87.70** $\rightarrow$ **Target Limit hit!** Engine sells all 60 shares.
  4. **Outcome:** **+$300 profit** on an initial risk of just **$30** (a 10:1 payout).

---

### Example 2: TQQQ Moves DOWN (Bearish Winning Trade)

Suppose tech stocks open weak on hot inflation data:

* **09:30 – 09:35 AM Action:**
  * Opens at **$85.00**, spikes to High of **$85.20**, drops to Low of **$84.20**, closes at **$84.30**.
  * Direction: **Bearish** (Close $84.30 < Open $85.00).
  * High = **$85.20**, Low = **$84.20** $\rightarrow$ Range = **$1.00**.
  * Midpoint = $\frac{85.20 + 84.20}{2} = \mathbf{\$84.70}$.
  * Ratio = **0.20** *(Passes filter!)*.
* **Calculated Bracket Order:**
  * **Risk per Share (1.0R):** $\$84.70 - \$84.20 = \mathbf{\$0.50}$.
  * **Share Size:** 60 shares.
  * **Entry Trigger:** SELL SHORT STOP 60 shares @ **$84.20**.
  * **Initial Stop Loss:** BUY TO COVER @ **$84.70** (Midpoint).
  * **Breakeven Trigger:** $\$84.20 - (6.0 \times \$0.50) = \mathbf{\$81.20}$.
  * **Profit Target:** $\$84.20 - (10.0 \times \$0.50) = \mathbf{\$79.20}$ (+10.0R = +$300).

* **How the trade unfolds:**
  1. **09:38 AM:** Tech sinks and TQQQ crosses below **$84.20** $\rightarrow$ **FILLED SHORT 60 shares**.
  2. **12:30 PM:** Selling intensifies, TQQQ reaches **$81.20** $\rightarrow$ Stop moves to **$84.20** (Breakeven).
  3. **01:45 PM:** TQQQ dumps to **$79.20** $\rightarrow$ **Target Limit hit!** Engine buys to cover.
  4. **Outcome:** **+$300 profit** shorting the drop.

---

### Example 3: The Fakeout (Losing Trade Saved by Midpoint Stop)

What happens when the market tricks everyone?

* The 5-minute candle is Bullish with High = **$82.70** and Midpoint = **$82.20**.
* At **09:39 AM**, price breaks out to **$82.72** $\rightarrow$ You buy 60 shares.
* At **09:43 AM**, a sudden wave of selling appears. TQQQ drops straight back into the box.
* At **09:45 AM**, TQQQ crosses **$82.20**.
* **Result:** The Midpoint Stop fires immediately. You exit with a loss of **-$0.50/share (-$30 total)**.
* **Why the Midpoint saved you:** Under standard ORB rules, your stop would have been at the bottom of the box ($81.70). You would have lost **-$1.00/share (-$60 total)**. The midpoint cut your loss in half and preserved your capital for the next opportunity.

---

### Example 4: Filter Stand-Down (Capital Preserved)

* TQQQ opens at $80.00 and has a sluggish 5-minute range of only **$0.40** against an ATR of $4.00.
* Ratio = $\frac{\$0.40}{\$4.00} = \mathbf{0.10}$.
* The Volatility Filter warns: `Ratio 0.10 < 0.15 Minimum Band — Compressed Chop`.
* The engine prints **STAND DOWN / NO TRADE** and does not place any orders.
* Throughout the day, TQQQ chops sideways inside an erratic range that would have whipsawed standard breakout traders. Your capital was protected by simply doing nothing.

---

## 5. How to Run & Operate the Strategy

### Method A: Web Trading Dashboard (Recommended)

1. **Launch Interactive Brokers TWS or IB Gateway:**
   * Paper Trading Port: `7497`
   * Live Trading Port: `7496`
   * Ensure API settings have **"Enable ActiveX and Socket Clients"** checked and `127.0.0.1` trusted.

2. **Open the Web Terminal:**
   Navigate to:
   ```text
   http://127.0.0.1:8060
   ```

3. **Dashboard Controls:**
   * **[ ▶ START STRATEGY ]**: Connects to IBKR, computes the 5-min opening range, checks the volatility filter, and arms the contingent bracket order.
   * **Dry-Run Mode (Checked)**: Simulates the entire trade without placing real financial orders in IBKR.
   * **Live Transmit Mode (Unchecked)**: Sends live contingent bracket orders directly into your IBKR account.
   * **[ ⏹ STOP STRATEGY ]**: Performs a graceful stop. If stopping takes longer than expected, the button dynamically allows a **[ FORCE KILL ]**.
   * **[ ⚠️ FLATTEN TQQQ ]**: The emergency kill-switch. Instantly cancels open orders and closes any open TQQQ position with an IBKR market order.

---

### Method B: Command Line (CLI)

1. **Compute Today's Signal (Preparation Only):**
   ```bash
   python -m backtest_engine.cli orb-signal configs/midpoint_stop_orb_intraday.yaml --capital 5000
   ```

2. **Run Live IBKR Execution (Paper Port 7497):**
   ```bash
   # Dry-run mode (safe preview)
   python -m backtest_engine.cli live-orb-ibkr configs/midpoint_stop_orb_intraday.yaml --capital 5000

   # Live transmitting mode
   python -m backtest_engine.cli live-orb-ibkr configs/midpoint_stop_orb_intraday.yaml --capital 5000 --transmit
   ```

3. **Backtest Historical Performance:**
   ```bash
   python -m backtest_engine.cli run-intraday-orb configs/midpoint_stop_orb_intraday.yaml
   ```

---

## 6. Summary Cheat Sheet

| Parameter | Value | Meaning |
| :--- | :--- | :--- |
| **Opening Range Window** | `5 minutes` | 09:30 – 09:35 AM ET |
| **OR / ATR Filter Band** | `0.15 — 0.25` | "Goldilocks" ratio required to arm a trade |
| **Risk per Trade** | `0.6%` | Max loss is limited to 0.6% of capital basis |
| **Initial Stop Loss** | `Midpoint` | Halfway between High and Low of opening 5-minute candle |
| **Breakeven Ratchet** | `+6.0R` | Move stop to Entry once profit reaches 6x initial risk |
| **Profit Target** | `+10.0R` | Limit order to capture 10x initial risk |
| **Entry Expiration** | `10:30 AM ET` | Unfilled breakout orders expire automatically |
| **EOD Flatten Time** | `15:30 PM ET` | All positions closed to cash; zero overnight exposure |
