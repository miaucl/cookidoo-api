"""Cookidoo API types."""

from __future__ import annotations

from dataclasses import dataclass, field


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
class CookidooAuthResponse:
    """An auth response class."""

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    sub: str


@dataclass
class CookidooUserInfo:
    """A user info class."""

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


@dataclass
class CookidooCreateCustomRecipe:
    """Input type for creating a new custom recipe from scratch.

    Attributes
    ----------
    name
        The name of the recipe
    ingredients
        List of ingredient strings (e.g., ["100 g flour", "2 eggs"])
    instructions
        List of instruction steps (strings or CookidooInstruction with settings)
    serving_size
        The number of servings
    total_time
        Total time in seconds
    active_time
        Active/prep time in seconds
    tools
        List of tools needed (e.g., ["TM6", "TM5"])
    unit_text
        The unit text for the yield (e.g., "portion")
    image
        Optional image URL

    """

    name: str
    ingredients: list[str]
    instructions: list[str | CookidooInstruction]
    serving_size: int
    total_time: int
    active_time: int
    tools: list[str] = field(default_factory=list)
    unit_text: str = "portion"
    image: str | None = None


@dataclass
class CookidooStepSettings:
    """Structured settings for a recipe step (for guided cooking).

    Attributes
    ----------
    time
        Time in seconds for the step
    temperature
        Temperature in Celsius (e.g., 100, Varoma)
    speed
        Speed setting (e.g., 1, 2, 0.5)

    """

    time: int | None = None
    temperature: int | str | None = None
    speed: float | None = None


@dataclass
class CookidooInstruction:
    """A recipe instruction with optional structured settings.

    Attributes
    ----------
    text
        The instruction text
    settings
        Optional structured settings for guided cooking

    """

    text: str
    settings: CookidooStepSettings | None = None


@dataclass
class CookidooEditCustomRecipe:
    """Input type for editing an existing custom recipe.

    Attributes
    ----------
    name
        The name of the recipe (optional, keeps existing if None)
    ingredients
        List of ingredient strings (optional, keeps existing if None)
    instructions
        List of instruction steps (strings or CookidooInstruction with settings)
    serving_size
        The number of servings (optional, keeps existing if None)
    total_time
        Total time in seconds (optional, keeps existing if None)
    active_time
        Active/prep time in seconds (optional, keeps existing if None)
    tools
        List of tools needed (optional, keeps existing if None)
    unit_text
        The unit text for the yield (optional, keeps existing if None)
    image
        Image URL (optional, keeps existing if None)

    """

    name: str | None = None
    ingredients: list[str] | None = None
    instructions: list[str | CookidooInstruction] | None = None
    serving_size: int | None = None
    total_time: int | None = None
    active_time: int | None = None
    tools: list[str] | None = None
    unit_text: str | None = None
    image: str | None = None
