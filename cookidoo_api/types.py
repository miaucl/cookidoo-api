"""Cookidoo API types."""

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
        default_factory=lambda: CookidooLocalizationConfig()
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

    """

    id: str
    name: str
    ingredients: list[CookidooIngredient]


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

    """

    difficulty: str
    notes: list[str]
    categories: list[CookidooCategory]
    collections: list[CookidooRecipeCollection]
    utensils: list[str]
    serving_size: str
    active_time: int
    total_time: int


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
