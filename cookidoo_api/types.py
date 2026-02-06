"""Cookidoo API types."""

from dataclasses import dataclass, field
from enum import StrEnum


class ThermomixMachineType(StrEnum):
    """Thermomix machine types."""

    TM5 = "TM5"
    TM6 = "TM6"
    TM7 = "TM7"
    TM31 = "TM31"


class ThermomixSpeed(StrEnum):
    """Recommended Thermomix speeds."""

    SOFT = "soft"
    SPEED_0_5 = "0.5"
    SPEED_1 = "1"
    SPEED_1_5 = "1.5"
    SPEED_2 = "2"
    SPEED_2_5 = "2.5"
    SPEED_3 = "3"
    SPEED_3_5 = "3.5"
    SPEED_4 = "4"
    SPEED_4_5 = "4.5"
    SPEED_5 = "5"
    SPEED_5_5 = "5.5"
    SPEED_6 = "6"
    SPEED_6_5 = "6.5"
    SPEED_7 = "7"
    SPEED_7_5 = "7.5"
    SPEED_8 = "8"
    SPEED_8_5 = "8.5"
    SPEED_9 = "9"
    SPEED_9_5 = "9.5"
    SPEED_10 = "10"


class ThermomixDirection(StrEnum):
    """Thermomix rotation directions."""

    CW = "CW"
    CCW = "CCW"


class ThermomixTemperature(StrEnum):
    """Recommended Thermomix temperatures (Celsius)."""

    VAROMA = "varoma"
    TEMP_37 = "37"
    TEMP_40 = "40"
    TEMP_45 = "45"
    TEMP_50 = "50"
    TEMP_55 = "55"
    TEMP_60 = "60"
    TEMP_65 = "65"
    TEMP_70 = "70"
    TEMP_75 = "75"
    TEMP_80 = "80"
    TEMP_85 = "85"
    TEMP_90 = "90"
    TEMP_95 = "95"
    TEMP_98 = "98"
    TEMP_100 = "100"
    TEMP_105 = "105"
    TEMP_110 = "110"
    TEMP_115 = "115"
    TEMP_120 = "120"


class ThermomixMode(StrEnum):
    """Thermomix guided cooking modes."""

    DOUGH = "dough"
    BROWNING = "browning"
    TURBO = "turbo"
    STEAMING = "steaming"
    BLEND = "blend"
    WARM_UP = "warm_up"
    RICE_COOKER = "rice_cooker"


class ThermomixBrowningPower(StrEnum):
    """Browning mode power levels."""

    GENTLE = "Gentle"
    INTENSE = "Intense"


class ThermomixSteamingAccessory(StrEnum):
    """Accessories for steaming mode."""

    VAROMA = "Varoma"
    SIMMERING_BASKET = "SimmeringBasket"
    VAROMA_AND_SIMMERING_BASKET = "VaromaAndSimmeringBasket"


@dataclass
class CookidooLocalizationConfig:
    """A localization config class."""

    country_code: str = "ch"
    language: str = "de-CH"
    url: str = "https://cookidoo.ch/foundation/de-CH"


@dataclass
class CookidooConfig:
    """Cookidoo config type.

    Attributes
    ----------
    localization
        The localization for the api including country, language and url
    email
        The email to login
    password
        The password to login

    """

    localization: CookidooLocalizationConfig = field(
        default_factory=CookidooLocalizationConfig
    )
    email: str = "your@email"
    password: str = "1234password!"


@dataclass
class CookidooUserInfo:
    """A user info class."""

    id: str
    username: str
    description: str | None
    picture: str | None


@dataclass
class CookidooSubscription:
    """A subscription class."""

    active: bool
    expires: str
    start_date: str
    status: str
    subscription_level: str
    subscription_source: str
    type: str
    extended_type: str


@dataclass
class CookidooIngredient:
    """Cookidoo ingredient type.

    Attributes
    ----------
    id
        The id of the ingredient
    name
        The label of the ingredient
    description
        The description of the item, including the quantity or other helpful information

    """

    id: str
    name: str
    description: str


@dataclass
class CookidooItem:
    """Cookidoo item type.

    Attributes
    ----------
    id
        The id of the item
    name
        The label of the item

    """

    id: str
    name: str
    is_owned: bool


@dataclass
class CookidooIngredientItem(CookidooItem):
    """Cookidoo ingredient item type.

    Attributes
    ----------
    description
        The description of the item, including the quantity or other helpful information

    """

    description: str


@dataclass
class CookidooAdditionalItem(CookidooItem):
    """Cookidoo additional item type."""

    pass


@dataclass
class CookidooShoppingRecipe:
    """Cookidoo shopping recipe type.

    Attributes
    ----------
    id
        The id of the recipe
    name
        The label of the recipe
    ingredients
        The ingredients of the recipe
    thumbnail
        The thumbnail image URL (small preview)
    image
        The full-size image URL
    url
        The URL of the recipe

    """

    id: str
    name: str
    ingredients: list[CookidooIngredient]
    thumbnail: str | None
    image: str | None
    url: str


@dataclass
class CookidooSearchRecipeHit:
    """A single recipe hit from Cookidoo search.

    Attributes
    ----------
    id
        The id of the recipe
    name
        The title of the recipe
    thumbnail
        The thumbnail image URL (small preview)
    image
        The full-size image URL
    url
        The URL of the recipe

    """

    id: str
    name: str
    thumbnail: str | None
    image: str | None
    url: str


@dataclass
class CookidooSearchResult:
    """Cookidoo search result type.

    Attributes
    ----------
    recipes
        List of recipe hits matching the search
    total
        Total number of matching recipes

    """

    recipes: list[CookidooSearchRecipeHit]
    total: int


@dataclass
class CookidooCategory:
    """Cookidoo category type.

    Attributes
    ----------
    id
        The id of the category
    name
        The label of the category
    notes
        The additional information of the category

    """

    id: str
    name: str
    notes: str


@dataclass
class CookidooRecipeCollection:
    """Cookidoo recipe collection type.

    Attributes
    ----------
    id
        The id of the collection
    name
        The label of the collection
    additional_information
        The additional information of the collection

    """

    id: str
    name: str
    total_recipes: int


@dataclass
class CookidooNutrition:
    """Nutrition value type.

    Attributes
    ----------
    number
        The value of the nutrition
    type
        The type of nutrition (e.g., protein, fat, kcal, etc.)
    unittype
        The unit of the nutrition value (e.g., g, kcal, kJ)

    """

    number: float
    type: str
    unittype: str


@dataclass
class CookidooRecipeNutrition:
    """Recipe nutrition type.

    Attributes
    ----------
    nutritions
        List of nutrition values
    quantity
        The quantity for which the nutrition applies
    unit_notation
        The unit notation (e.g., 'ración')

    """

    nutritions: list[CookidooNutrition]
    quantity: int
    unit_notation: str


@dataclass
class CookidooNutritionGroup:
    """Nutrition group type.

    Attributes
    ----------
    name
        The name of the nutrition group
    recipe_nutritions
        List of recipe nutrition objects

    """

    name: str
    recipe_nutritions: list[CookidooRecipeNutrition]


@dataclass
class CookidooShoppingRecipeDetails(CookidooShoppingRecipe):
    """Cookidoo recipe details type.

    Attributes
    ----------
    difficulty
        The difficulty of the recipe
    notes
       Hints and additional information about the recipe
    categories
        The categories of the recipe
    collections
        The collections of the recipe
    utensils
        The utensils needed for the recipe
    serving_size
        The service size of the recipe
    active_time
        The time needed preparing the recipe [in seconds]
    total_time
        The time needed until the recipe is ready [in seconds]
    nutrition_groups
        The nutrition groups of the recipe (from API, may be empty)

    """

    difficulty: str
    notes: list[str]
    categories: list[CookidooCategory]
    collections: list[CookidooRecipeCollection]
    utensils: list[str]
    serving_size: int
    active_time: int
    total_time: int
    nutrition_groups: list[CookidooNutritionGroup]


@dataclass
class CookidooChapterRecipe:
    """Cookidoo chapter recipe type.

    Attributes
    ----------
    id
        The id of the recipe
    name
        The label of the recipe
    total_time
        The time for the recipe

    """

    id: str
    name: str
    total_time: int


@dataclass
class CookidooChapter:
    """Cookidoo chapter type.

    Attributes
    ----------
    title
        The title of the chapter
    recipes
        The recipes in the chapter

    """

    name: str
    recipes: list[CookidooChapterRecipe]


@dataclass
class CookidooCustomRecipe:
    """Cookidoo custom recipe type.

    Attributes
    ----------
    id
        The id of the recipe
    name
        The label of the recipe
    ingredients
        The ingredients of the recipe
    instructions
        The instructions of the recipe
    tools
        The tools needed for the recipe
    serving_size
        The service size of the recipe
    active_time
        The time needed preparing the recipe [in seconds]
    total_time
        The time needed until the recipe is ready [in seconds]
    thumbnail
        The thumbnail image URL (small preview)
    image
        The full-size image URL
    url
        The URL of the recipe

    """

    id: str
    name: str
    ingredients: list[str]
    instructions: list[str]
    tools: list[str]
    serving_size: int
    active_time: int
    total_time: int
    thumbnail: str | None
    image: str | None
    url: str


@dataclass
class CookidooCollection:
    """Cookidoo collection type.

    Attributes
    ----------
    id
        The id of the collection
    title
        The title of the collection
    description
        The description of the collection
    chapters
        The recipes in the collection

    """

    id: str
    name: str
    description: str | None
    chapters: list[CookidooChapter]


@dataclass
class CookidooCalendarDayRecipe:
    """Cookidoo calendar day recipe type.

    Attributes
    ----------
    id
        The id of the recipe
    name
        The label of the recipe
    total_time
        The time for the recipe
    thumbnail
        The thumbnail image URL (small preview)
    image
        The full-size image URL
    url
        The URL of the recipe

    """

    id: str
    name: str
    total_time: int
    thumbnail: str | None
    image: str | None
    url: str


@dataclass
class CookidooCalendarDay:
    """Cookidoo calendar day type.

    Attributes
    ----------
    id
        The id of the calendar day
    title
        The title of the calendar day
    recipes
        The recipes in the calendar day
    customer_recipe_ids
        IDs of custom recipes planned for the day (when returned by the API)

    """

    id: str
    title: str
    recipes: list[CookidooCalendarDayRecipe]
    customer_recipe_ids: list[str] = field(default_factory=list)
