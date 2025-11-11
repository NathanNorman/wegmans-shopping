# Wegmans Store Directory

**Last Updated:** November 11, 2025
**Total Active Stores:** 110

## Purpose

This directory lists all valid Wegmans store numbers found in the Algolia product search API. Each store number corresponds to a specific Wegmans location. **Store numbers are critical** - they determine which aisle locations are returned for products.

## Known Locations

| Store # | Location | Address | Verified |
|---------|----------|---------|----------|
| 108 | Raleigh, NC | 1200 Wake Towne Drive, Raleigh, NC 27609 | ✅ Yes |
| 86 | Unknown | (Not Raleigh - has different aisles) | ❌ Wrong for Raleigh |
| 120 | Unknown | | ❓ Unverified |

## All Valid Store Numbers

The following 110 store numbers are active in the Wegmans Algolia API (tested November 2025):

```
1, 3, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 22, 24, 25, 26, 30, 31,
32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 53,
54, 55, 56, 57, 58, 59, 60, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 73, 74, 75, 76,
77, 78, 79, 80, 82, 83, 84, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95, 96, 97, 98, 104,
105, 108, 111, 115, 119, 120, 124, 125, 126, 127, 128, 129, 130, 133, 134, 135, 139,
140, 141, 142, 143, 145, 146, 148
```

## How to Find Your Store Number

### Method 1: Test Product Location (Recommended)

1. Go to https://shop.wegmans.com and select your store
2. Search for "Kraft Mac and Cheese Original"
3. Note the aisle location shown (e.g., "03B-R-4")
4. Run this test in your terminal:

```bash
python3 << 'EOF'
import requests

# Replace with your observed aisle (e.g., "03B" from "03B-R-4")
YOUR_AISLE = "03B"

test_stores = [86, 104, 105, 108, 111, 115, 119, 120, 124, 125, 126, 127, 128]  # Common NC/VA stores

for store in test_stores:
    payload = {
        "requests": [{
            "indexName": "products",
            "query": "kraft mac and cheese original",
            "hitsPerPage": 1,
            "filters": f"storeNumber:{store} AND fulfilmentType:instore"
        }]
    }

    response = requests.post(
        "https://qgppr19v8v-dsn.algolia.net/1/indexes/*/queries",
        json=payload,
        headers={
            "x-algolia-api-key": "9a10b1401634e9a6e55161c3a60c200d",
            "x-algolia-application-id": "QGPPR19V8V"
        }
    )

    if response.status_code == 200:
        hits = response.json()['results'][0]['hits']
        if hits:
            aisle = hits[0].get('planogram', {}).get('aisle', '')
            if YOUR_AISLE in aisle:
                print(f"✅ MATCH! Store {store}: Aisle {aisle}")
            else:
                print(f"   Store {store}: Aisle {aisle}")
EOF
```

### Method 2: Browser Developer Tools

1. Go to https://shop.wegmans.com
2. Open Developer Tools (F12)
3. Go to Network tab
4. Search for any product
5. Look for requests to `algolia.net`
6. Check the request payload for `storeNumber:XXX`

## Updating Your App's Store Number

### For Development:

Edit `config/settings.py`:
```python
ALGOLIA_STORE_NUMBER = int(os.getenv("ALGOLIA_STORE_NUMBER", "108"))  # Your store number
```

### For Production (Render):

1. Go to Render dashboard
2. Select your service (wegmans-shopping)
3. Environment tab
4. Add/update: `ALGOLIA_STORE_NUMBER=108` (your store number)
5. Save changes (triggers auto-deploy)

### For Database:

Update existing user accounts:
```sql
UPDATE users SET store_number = 108 WHERE id = 'your-user-id';
```

Clear old cached searches:
```sql
DELETE FROM search_cache WHERE store_number = 86;  -- Old wrong store
DELETE FROM search_cache WHERE store_number = 108; -- Force fresh fetch
```

## Store Number Impact

**Critical:** Using the wrong store number causes:
- ❌ Incorrect aisle locations
- ❌ Products shown as "out of stock" when they're available
- ❌ Wrong prices (store-specific pricing)
- ❌ Missing products (store-specific inventory)

**Example:** Kraft Mac & Cheese at different stores:
- Store 108 (Raleigh): Aisle 03B-R-4 ✅ Correct
- Store 86 (Unknown): Aisle 14A-L-9 ❌ Wrong for Raleigh
- Store 120 (Unknown): Aisle 07B-R-5 ❌ Wrong for Raleigh

## Contributing

If you verify a store location, please update this file:

```markdown
| Store # | Location | Address | Verified |
|---------|----------|---------|----------|
| 108 | Raleigh, NC | 1200 Wake Towne Drive | ✅ Yes |
```

## Technical Notes

- Store numbers are used in Algolia API filter: `storeNumber:108 AND fulfilmentType:instore`
- Planogram data (aisle/shelf/side/section) is store-specific
- Some products may not have planogram data (shows "Unknown" aisle)
- Store numbers are NOT sequential (many gaps in the range)
- Tested range: 1-150 (110 active stores found)

## See Also

- `config/settings.py` - Default store number configuration
- `migrations/013_multi_store_support.sql` - Multi-store database schema
- `CLAUDE.md` - Project documentation
