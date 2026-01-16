# Failed Symbols Guide

## Failed Symbols from Price Download

The following symbols failed to download:
- **ANSS**, **ATVI**, **BRK.B**, **DM**, **MAG**, **PXD**, **SAND**, **SPLK**, **SQ**, **WBA**

## Analysis & Recommendations

### 1. Format Issues (Fix Required)

#### **BRK.B** → **BRK-B**
- **Issue**: yfinance uses `BRK-B` format, not `BRK.B`
- **Action**: Replace `BRK.B` with `BRK-B` in your watchlist
- **Status**: ✅ Valid symbol, just wrong format

### 2. Delisted/Acquired Companies (Remove)

#### **ATVI** (Activision Blizzard)
- **Status**: Acquired by Microsoft in October 2023
- **Action**: Remove from watchlist
- **Reason**: No longer trades independently

#### **SPLK** (Splunk)
- **Status**: Acquired by Cisco in March 2024
- **Action**: Remove from watchlist
- **Reason**: No longer trades independently

### 3. Invalid/Delisted Symbols (Remove)

#### **ANSS** (ANSYS)
- **Status**: May be delisted or symbol changed
- **Action**: Check if symbol still exists, remove if invalid

#### **DM** (Desktop Metal)
- **Status**: May be delisted or symbol changed
- **Action**: Check if symbol still exists, remove if invalid

#### **MAG** (MAG Silver)
- **Status**: May be delisted or symbol changed
- **Action**: Check if symbol still exists, remove if invalid

#### **PXD** (Pioneer Natural Resources)
- **Status**: Acquired by ExxonMobil in 2023
- **Action**: Remove from watchlist
- **Reason**: No longer trades independently

#### **SAND** (Sandstorm Gold)
- **Status**: May be delisted or symbol changed
- **Action**: Check if symbol still exists, remove if invalid

#### **SQ** (Block, formerly Square)
- **Status**: Symbol may have changed or delisted
- **Action**: Check if symbol still exists, remove if invalid

#### **WBA** (Walgreens Boots Alliance)
- **Status**: May be delisted or symbol changed
- **Action**: Check if symbol still exists, remove if invalid

## Quick Fix Script

To automatically fix these symbols in your watchlist, you can:

1. **Replace BRK.B with BRK-B**:
   ```bash
   # Edit your watchlist and replace BRK.B with BRK-B
   ```

2. **Remove delisted symbols**:
   - Remove: ATVI, SPLK, PXD
   - Check and potentially remove: ANSS, DM, MAG, SAND, SQ, WBA

## How to Fix in GUI

1. Go to **Watchlist Manager**
2. Find the watchlist containing these symbols
3. For each symbol:
   - **BRK.B**: Replace with `BRK-B`
   - **ATVI, SPLK, PXD**: Remove (delisted/acquired)
   - **Others**: Check if they exist, remove if invalid

## Validation

After fixing, you can validate your watchlist:

```bash
python scripts/validate_watchlist_symbols.py <watchlist_name>
```

This will check all symbols and report any remaining issues.

## Prevention

To prevent this in the future:

1. **Regular Validation**: Run validation script periodically
2. **Monitor Mergers**: Keep track of company acquisitions
3. **Use Correct Formats**: Always use yfinance-compatible formats (e.g., `BRK-B` not `BRK.B`)

## Notes

- Some symbols may have been temporarily unavailable during download
- If a symbol is valid but failed, try downloading again
- Always validate symbols before adding to watchlists
