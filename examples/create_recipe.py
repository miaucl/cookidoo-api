"""
Example: Create a recipe and add it to a collection
"""
import asyncio
import aiohttp
from cookidoo_api import Cookidoo, CookidooConfig, CookidooLocalizationConfig
from cookidoo_api.types import CookidooCreateCustomRecipe

# Your Cookidoo credentials
EMAIL = "your@email.com"
PASSWORD = "yourpassword"

# Collection to add recipe to (find yours with get_custom_collections())
COLLECTION_ID = "your-collection-id"


async def main():
    """Create a recipe and add it to a collection."""
    
    # Setup config for Greece
    cfg = CookidooConfig(
        email=EMAIL,
        password=PASSWORD,
        localization=CookidooLocalizationConfig(
            country_code="gr",
            language="el-GR",
            url="https://cookidoo.gr/foundation/el-GR"
        )
    )
    
    async with aiohttp.ClientSession() as session:
        api = Cookidoo(session, cfg)
        await api.login()
        print("✅ Logged in")
        
        # Create a custom recipe
        recipe = CookidooCreateCustomRecipe(
            name="Κοτόπουλο με Χυλοπίτες (Thermomix)",
            serving_size=6,
            total_time=95*60,     # 95 minutes total
            active_time=30*60,    # 30 minutes active prep
            unit_text="portion",  # IMPORTANT: Must be exactly "portion"
            tools=["TM6", "TM5"],  # Works with both TM6 and TM5 models
            ingredients=[
                "1 κοτόπουλο ολόκληρο (~1,5 κιλό), κομμένο σε 10 μερίδες",
                "500 γρ. χυλοπίτες (ή ψιλό χυλοπιτάκι)",
                "1 κρεμμύδι",
                "2 σκελίδες σκόρδο",
                "2-3 κλαδάκια ρίγανη",
                "2-3 κλαδάκια θυμάρι",
                "4-6 κ.σ. ελαιόλαδο",
                "6 κόκκοι μπαχάρι",
                "1 στικ κανέλας",
                "1 κύβος κότας",
                "½ κ.σ. κρυσταλλική ζάχαρη",
                "1 κ.σ. πελτές ντομάτας",
                "100 γρ. λευκό κρασί",
                "1 λίτρο νερό βραστό",
                "500 γρ. τριμμένες ντομάτες",
                "αλάτι και πιπέρι κατά βούληση",
                "φέτα τριμμένη (για σερβίρισμα)",
                "ψιλοκομμένος μαϊντανός (για σερβίρισμα)"
            ],
            instructions=[
                "Ψιλόκοψε κρεμμύδι + σκόρδο: Βάλε στον κάδο. 5 δευτ. / Ταχύτητα 5. Κατέβασε από τα τοιχώματα.",
                "Σοτάρισμα αρωματικών: Πρόσθεσε 2-3 κ.σ. ελαιόλαδο, ρίγανη, θυμάρι. 3 λεπτά / Varoma / Ταχύτητα 1.",
                "Σοτάρισμα κοτόπουλου: Βγάλε τα αρωματικά. Σοτάρισε τα κομμάτια κοτόπουλου σε τηγάνι με λίγο ελαιόλαδο 2-3 λεπτά ανά πλευρά. Βάλε στον κάδο με αλάτι, πιπέρι, μπαχάρι, κανέλα. 5 λεπτά / Varoma / αντίστροφη / Ταχύτητα 0.5.",
                "Σάλτσα & βράσιμο: Πρόσθεσε ζάχαρη, πελτέ, κρασί, 400 γρ. νερό, τριμμένες ντομάτες, κύβο κότας. 35 λεπτά / 100°C / αντίστροφη / Ταχύτητα 0.5.",
                "Προθέρμανε φούρνο στους 200°C αέρα. Σε ταψί 30x40 βάλε τις χυλοπίτες + 600 γρ. νερό + κοτόπουλο με τη σάλτσα. Ανακάτεψε.",
                "Ψήσε στους 200°C για 20-25 λεπτά μέχρι να απορροφηθεί η υγρασία και να ροδίσουν οι χυλοπίτες.",
                "Σερβίρισμα: Πρόσθεσε τριμμένη φέτα και ψιλοκομμένο μαϊντανό από πάνω. Καλή όρεξη!"
            ]
        )
        
        result = await api.create_custom_recipe(recipe)
        print(f"✅ Recipe created: {result.id}")
        print(f"   Name: {result.name}")
        print(f"   Ingredients: {len(result.ingredients)}")
        print(f"   Instructions: {len(result.instructions)}")
        
        # Add to collection
        await api.add_recipes_to_custom_collection(
            COLLECTION_ID,
            [result.id]
        )
        print(f"✅ Added to collection")
        
        print(f"\n🎉 Done!")
        print(f"   URL: https://cookidoo.gr/created-recipes/el-GR/{result.id}")


if __name__ == "__main__":
    asyncio.run(main())
