# Python Coding Standards

## 1. Type Hinting
Always type hint the bot instance in `__init__` to ensure Intellisense works.
```python
# ✅ CORRECT
def __init__(self, bot: commands.Bot):
    self.bot = bot

# ❌ INCORRECT
def __init__(self, bot):
    self.bot = bot
```

## 2. Path Handling
Never use string concatenation for paths. Use os.path.join.

```Python
# ✅ CORRECT
DB_FILE = os.path.join("data", "quotes.db")

# ❌ INCORRECT
DB_FILE = "data/quotes.db"
```

## 3. Logging
Do not use print(). Use the logging module with a specific namespace.

```Python
import logging
logger = logging.getLogger("bot.cogs.my_feature")

logger.info("Feature loaded")
logger.error("Database failed", exc_info=True)
```

## 4. SQL Patterns
Use parameterized queries to prevent SQL injection.

```Python
# ✅ CORRECT
await db.execute("SELECT * FROM table WHERE id = ?", (user_id,))

# ❌ INCORRECT (SQL Injection Risk)
await db.execute(f"SELECT * FROM table WHERE id = {user_id}")
```