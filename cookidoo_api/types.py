"""Cookidoo API types."""

from typing import TypedDict


class CookidooLocalizationConfig(TypedDict):
    """A localization config class."""

    country_code: str
    language: str
    url: str


class CookidooConfig(TypedDict):
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

    localization: CookidooLocalizationConfig
    email: str
    password: str


class CookidooAuthResponse(TypedDict):
    """An auth response class."""

    username: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class CookidooUserInfo(TypedDict):
    """A user info class."""

    username: str
    description: str | None
    picture: str | None


class CookidooSubscription(TypedDict):
    """A subscription class."""

    active: bool
    expires: str
    startDate: str
    status: str
    subscriptionLevel: str
    subscriptionSource: str
    type: str
    extendedType: str


class CookidooIngredient(TypedDict):
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


class CookidooItem(TypedDict):
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


class CookidooIngredientItem(CookidooItem):
    """Cookidoo ingredient item type.

    Attributes
    ----------
    description
        The description of the item, including the quantity or other helpful information

    """

    description: str


class CookidooAdditionalItem(CookidooItem):
    """Cookidoo additional item type."""

    pass


class CookidooRecipe(TypedDict):
    """Cookidoo recipe type.

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


class CookidooCategory(TypedDict):
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


class CookidooCollection(TypedDict):
    """Cookidoo collection type.

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


class CookidooRecipeDetails(CookidooRecipe):
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
    collections: list[CookidooCollection]
    utensils: list[str]
    serving_size: str
    active_time: int
    total_time: int


class QuantityJSON(TypedDict):
    """The json for an quantity in the API."""

    value: int


class AdditionalItemJSON(TypedDict):
    """The json for an additional item in the API."""

    id: str
    name: str
    isOwned: bool


class ItemJSON(TypedDict):
    """The json for an item in the API."""

    id: str
    ingredientNotation: str
    isOwned: bool
    quantity: QuantityJSON | None
    unitNotation: str | None


class IngredientJSON(TypedDict):
    """The json for an ingredient in the API."""

    localId: str
    ingredientNotation: str
    quantity: QuantityJSON | None
    unitNotation: str | None


class RecipeJSON(TypedDict):
    """The json for a recipe in the API."""

    id: str
    title: str
    recipeIngredientGroups: list[ItemJSON]


class RecipeDetailsAdditionalInformationJSON(TypedDict):
    """The json for a recipe details additional information in the API."""

    content: str


class RecipeDetailsCategoryJSON(TypedDict):
    """The json for a recipe details category in the API."""

    id: str
    title: str
    subtitle: str


class RecipeDetailsCollectionCountJSON(TypedDict):
    """The json for a recipe details collection count in the API."""

    value: int


class RecipeDetailsCollectionJSON(TypedDict):
    """The json for a recipe details collection in the API."""

    id: str
    title: str
    recipesCount: RecipeDetailsCollectionCountJSON


class RecipeDetailsIngredientGroupJSON(TypedDict):
    """The json for a recipe details ingredient group in the API."""

    recipeIngredients: list[IngredientJSON]


class RecipeDetailsStepJSON(TypedDict):
    """The json for a recipe step in the API."""

    formattedText: str
    title: str


class RecipeDetailsStepGroupJSON(TypedDict):
    """The json for a recipe step group in the API."""

    title: str
    recipeSteps: list[RecipeDetailsStepJSON]


class RecipeDetailsUtensilsJSON(TypedDict):
    """The json for a recipe utensils in the API."""

    utensilNotation: str


class RecipeDetailsServingSizeJSON(TypedDict):
    """The json for a recipe serving size in the API."""

    quantity: QuantityJSON
    unitNotation: str


class RecipeDetailsTimeJSON(TypedDict):
    """The json for a recipe time in the API."""

    quantity: QuantityJSON
    type: str
    comment: str


class RecipeDetailsJSON(TypedDict):
    """The json for a recipe details in the API."""

    id: str
    title: str
    difficulty: str
    additionalInformation: list[RecipeDetailsAdditionalInformationJSON]
    categories: list[RecipeDetailsCategoryJSON]
    inCollections: list[RecipeDetailsCollectionJSON]
    recipeIngredientGroups: list[RecipeDetailsIngredientGroupJSON]
    recipeStepGroups: list[RecipeDetailsStepGroupJSON]
    recipeUtensils: list[RecipeDetailsUtensilsJSON]
    servingSize: RecipeDetailsServingSizeJSON
    times: list[RecipeDetailsTimeJSON]
