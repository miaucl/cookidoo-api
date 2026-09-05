"""Cookidoo API types."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from cookidoo_api.const import OAUTH_CLIENT_ID, OAUTH_REDIRECT_URI


class ThermomixMachineType(StrEnum):
    """Thermomix machine types."""

    TM5 = "TM5"
    TM6 = "TM6"
    TM7 = "TM7"
    TM31 = "TM31"


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
    client_id
        The OAuth2 client id to run the login flow as
    redirect_uri
        The OAuth2 redirect uri registered for ``client_id``

    The login runs as a public client (authorization code + PKCE, no client
    secret), so both values are public identifiers rather than credentials and
    they default to the ones of the Cookidoo mobile app. Callers do not need to
    set them; see ``docs/oauth-client.md``.

    """

    localization: CookidooLocalizationConfig = field(
        default_factory=CookidooLocalizationConfig
    )
    email: str = "your@email"
    password: str = "1234password!"
    client_id: str = OAUTH_CLIENT_ID
    redirect_uri: str = OAUTH_REDIRECT_URI


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
class CookidooDevice:
    """A paired Thermomix appliance on the account."""

    type: ThermomixMachineType


class CookidooCookState(StrEnum):
    """State of an ongoing remote-monitored cook."""

    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    DONE = "DONE"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    STALE = "STALE"


@dataclass
class CookidooCookingActivity:
    """Live cook state pushed by an appliance's remote monitoring.

    Values the recipe does not provide are ``None`` (the app renders ``"---"``
    for an unset current temperature, which is normalised to ``None`` here).
    """

    device_id: str
    cooking_activity_id: str | None = None
    state: CookidooCookState | None = None
    recipe_id: str | None = None
    recipe_type: str | None = None
    recipe_name: str | None = None
    step: str | None = None
    remaining_seconds: int | None = None
    is_time_estimated: bool = False
    current_temperature: float | None = None
    target_temperature: float | None = None
    message_title: str | None = None
    message_body: str | None = None
    message_criticality: str | None = None
    completed_at: datetime | None = None
    stale_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        """Whether a cook is currently running or paused."""
        return self.state in (CookidooCookState.RUNNING, CookidooCookState.PAUSED)


@dataclass
class CookidooAuthData:
    """OAuth2 tokens obtained from a login, for persistence and restore.

    ``expires_at`` is a POSIX timestamp (seconds) for the access token.
    """

    access_token: str
    refresh_token: str
    expires_at: float


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
class CookidooRecipeStep:
    """Recipe step type.

    Attributes
    ----------
    title
        The title of the step (may be empty)
    formatted_text
        The instruction text for the step, as HTML markup

    """

    title: str
    formatted_text: str


@dataclass
class CookidooRecipeStepGroup:
    """Recipe step group type.

    Attributes
    ----------
    title
        The title of the step group (may be empty)
    recipe_steps
        List of recipe steps in this group

    """

    title: str
    recipe_steps: list[CookidooRecipeStep]


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
    step_groups
        The grouped cooking instructions for the recipe (from API, may be
        empty). Instruction text is returned as HTML markup, as sent by the
        API.

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
    step_groups: list[CookidooRecipeStepGroup]


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
