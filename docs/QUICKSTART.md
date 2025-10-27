# Quick Start Guide

## Three Ways to Create a Shopping List

### 1. Load from File (Recommended)

Create a text file with your items:

**simple_list.txt:**
```
Milk
Eggs
Bread
```

Or with quantities:

**shopping_list.txt:**
```
2,Milk
1,Eggs
3,Bread
```

Then run:
```bash
python3 shop.py shopping_list.txt
```

### 2. Interactive Mode

```bash
python3 shop.py
```

Then type items one per line:
```
1. Milk
2. 2,Eggs
3. Bread
```

Press Ctrl+D when done.

### 3. From Clipboard/Pipe

```bash
echo -e "Milk\nEggs\nBread" | python3 shop.py --stdin
```

Or copy items to clipboard and:
```bash
pbpaste | python3 shop.py --stdin
```

## File Format

### Simple Format (newline-separated)
```
Milk
Eggs
Bread
Butter
```
All items default to quantity 1.

### With Quantities
```
quantity,product name
```

Example:
```
2,Milk
1,Eggs
3,Bread
```

### With Comments
```
# Dairy
1,Milk
2,String cheese

# Produce
1,Apples
1,Bananas
```

Lines starting with `#` are ignored.

## What Happens Next

1. Script parses your list
2. Shows summary (X unique items, Y total items)
3. Asks for confirmation
4. Searches Wegmans for each item (~5 seconds per item)
5. Opens web browser at http://localhost:8080
6. You pick the correct products interactively
7. Final list shows all items organized by aisle
8. Edit quantities, delete items, or add more
9. Copy markdown or download

## Example Session

```bash
$ python3 shop.py my_list.txt

📄 Loading shopping list from: my_list.txt
✓ Loaded 5 items

============================================================
📋 Shopping List Summary
============================================================
Unique items: 5
Total items: 7

Search for these items? [Y/n] y

🔍 Searching for 5 items...
[1/5] Searching: Milk (qty: 2)
  ✓ Found 10 options
[2/5] Searching: Eggs (qty: 1)
  ✓ Found 10 options
...

============================================================
🌐 Interactive Shopping List Builder
============================================================

📱 Open in your browser:
   http://localhost:8080
```

## Tips

- **Simple lists**: Just list items, one per line
- **Quantities**: Add `2,` before item name for 2x
- **Comments**: Use `#` for organizing sections
- **Existing results**: If `search_results.json` exists, it skips searching and goes straight to the web UI
- **Fresh search**: Delete `search_results.json` to search again

## Quick Examples

**Simple grocery run:**
```bash
echo -e "Milk\nEggs\nBread\nButter" | python3 shop.py --stdin
```

**From your notes:**
```bash
# Copy your shopping list, then:
pbpaste | python3 shop.py --stdin
```

**Reuse previous search:**
```bash
# Already have search_results.json
python3 shop.py shopping_list.txt
# Instantly opens web UI (no searching)
```
