# Cookidoo Recipe Creator Skill

Create and manage custom recipes on Cookidoo (Thermomix recipe platform) programmatically.

## Quick Start

```python
import asyncio
from cookidoo_api import Cookidoo, CookidooConfig, CookidooLocalizationConfig
from cookidoo_api.types import CookidooCreateCustomRecipe

EMAIL = "your@email.com"
PASSWORD = "yourpassword"

cfg = CookidooConfig(
    email=EMAIL,
    password=PASSWORD,
    localization=CookidooLocalizationConfig(
        country_code="gr",
        language="el-GR",
        url="https://cookidoo.gr/foundation/el-GR"
    )
)

async def create_recipe():
    async with aiohttp.ClientSession() as session:
        api = Cookidoo(session, cfg)
        await api.login()
        
        recipe = CookidooCreateCustomRecipe(
            name="My Recipe",
            serving_size=4,
            total_time=3600,
            active_time=1800,
            unit_text="portion",
            tools=["TM6"],
            ingredients=["100g flour", "2 eggs"],
            instructions=["Mix ingredients", "Bake at 180°C"]
        )
        
        result = await api.create_custom_recipe(recipe)
        print(f"Created: {result.id}")

asyncio.run(create_recipe())
```

## Installation

```bash
pip install cookidoo-api
```

Or from source:
```bash
git clone https://github.com/Mariosd23/cookidoo-api.git
cd cookidoo-api
pip install -e .
```

## Key Features

### Create Custom Recipes
```python
recipe = CookidooCreateCustomRecipe(
    name="Recipe Title",
    serving_size=6,
    total_time=95*60,      # seconds
    active_time=30*60,     # prep time in seconds
    unit_text="portion",   # MUST be "portion"
    tools=["TM6", "TM5"],  # Supports multiple Thermomix models
    ingredients=[
        "1 chicken (~1.5kg)",
        "500g pasta",
        "salt and pepper"
    ],
    instructions=[
        "Chop onion: 5 sec / Speed 5",
        "Sauté: 3 min / Varoma / Speed 1",
        "Cook: 35 min / 100°C / Reverse / Speed 0.5"
    ]
)
result = await api.create_custom_recipe(recipe)
```

**Important:** `unit_text` must be exactly `"portion"` (not "portions", "servings", etc.)

### Add Recipe to Collection
```python
# Add to custom collection
await api.add_recipes_to_custom_collection(
    collection_id="01KKW7B0X4VS4X2JFNDVW205GN",
    recipe_ids=[result.id]
)
```

### Edit Existing Recipe
```python
from cookidoo_api.types import CookidooEditCustomRecipe

updates = CookidooEditCustomRecipe(
    name="Updated Title",
    serving_size=8,
    ingredients=["new", "ingredients"],
    instructions=["new", "steps"]
)
result = await api.edit_custom_recipe(recipe_id, updates)
```

### List Custom Recipes
```python
recipes = await api.get_custom_recipes()
for r in recipes:
    print(f"{r.id}: {r.name}")
```

### Delete Recipe
```python
await api.remove_custom_recipe(recipe_id)
```

## Recipe Format Tips

### Thermomix Parameters (Auto-detected)
Use these patterns in instructions for device recognition:
- Time: `5 δευτ.` / `3 λεπτά` / `35 min`
- Speed: `ταχύτητα 5` / `Speed 1`
- Temperature: `70°C` / `100°C` / `Varoma`
- Direction: `αντίστροφη` / `reverse`

Example:
```
"Mix: 20 δευτ. / ταχύτητα 4"
"Cook: 35 λεπτά / 100°C / αντίστροφη / ταχύτητα 0.5"
```

### Device Compatibility
Recipes can be marked as compatible with multiple Thermomix models:
```python
tools=["TM6", "TM5"]  # Works with both TM6 and TM5
# or
tools=["TM6", "TM5", "TM31"]  # Works with TM6, TM5, and TM31
```

Available model codes: `"TM6"`, `"TM5"`, `"TM31"`

## Data Formats

### Ingredients
List of strings with quantities:
```python
ingredients=[
    "1 κοτόπουλο ολόκληρο (~1,5 κιλό)",
    "500 γρ. χυλοπίτες",
    "2 σκελίδες σκόρδο",
    "αλάτι και πιπέρι κατά βούληση"
]
```

### Time Values
All times in **seconds**:
- `total_time`: Total recipe time (cooking + prep)
- `active_time`: Active/prep time only

### API Flow
Creating a recipe uses 3 steps internally:
1. `POST /created-recipes/{lang}` - Create blank recipe
2. `PATCH /created-recipes/{lang}/{id}` - Add full details
3. `GET /created-recipes/{lang}/{id}` - Retrieve final format

## Environment Variables

```bash
export EMAIL="your@email.com"
export PASSWORD="yourpassword"
```

## Localization

Available country/language combinations:
- Greece: `country_code="gr"`, `language="el-GR"`
- Cyprus: `country_code="cy"`, `language="el-GR"`
- Germany: `country_code="de"`, `language="de-DE"`
- etc.

## Examples

See `example.py` for full working examples.

## License

MIT License - See LICENSE file
