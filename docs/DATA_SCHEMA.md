# Data Schema

The cache uses one Parquet file per ticker:

```text
data/cache/<SYMBOL>.parquet
```

Required columns:

| Column | Type | Meaning |
| --- | --- | --- |
| date | datetime64 | Trading session date |
| open | float | Adjusted open |
| high | float | Adjusted high |
| low | float | Adjusted low |
| close | float | Adjusted close |
| volume | int/float | Volume |

All files must be sorted by date, with no duplicate dates and positive OHLC prices.

