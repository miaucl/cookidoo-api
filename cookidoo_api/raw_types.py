"""Cookidoo API raw json types."""

from typing import Literal, TypedDict


class AuthResponseJSON(TypedDict):
    """An auth response class."""

    sub: str
    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int


class UserInfoJSON(TypedDict):
    """The json for a user info in the API."""

    username: str
    description: str | None
    picture: str | None


class SubscriptionJSON(TypedDict):
    """The json for a subscription in the API."""

    active: bool
    expires: str
    startDate: str
    status: str
    subscriptionLevel: str
    subscriptionSource: str
    type: str
    extendedType: str


# class QuantityJSON(TypedDict):
#     """The json for an quantity in the API."""

#     value: int | None
#     from: int | None
#     to: int | None

#  Need to use alternative syntax as "from" is a protected keyword
QuantityJSON = TypedDict(
    "QuantityJSON", {"value": int | None, "from": int | None, "to": int | None}
)


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


class ChapterRecipeJSON(TypedDict):
    """The json for a chapter recipe in the API."""

    id: str
    title: str
    type: Literal["VORWERK"] | Literal["CUSTOM"]
    totalTime: int


class ChapterJSON(TypedDict):
    """The json for a chapter in the API."""

    title: str
    recipes: list[ChapterRecipeJSON]


class CustomCollectionJSON(TypedDict):
    """The json for a custom collection in the API."""

    id: str
    title: str
    chapters: list[ChapterJSON]
    listType: Literal["CUSTOMLIST"]
    author: str


class ManagedCollectionJSON(TypedDict):
    """The json for a managed collection in the API."""

    id: str
    title: str
    description: str
    chapters: list[ChapterJSON]
    listType: Literal["MANAGEDLIST"]
    author: Literal["Vorwerk"]


class CalenderDayRecipeJSON(TypedDict):
    """The json for a calender day recipe in the API."""

    id: str
    title: str
    totalTime: int


class CalendarDayJSON(TypedDict):
    """The json for a calendar day in the API."""

    id: str
    title: str
    dayKey: str
    recipes: list[CalenderDayRecipeJSON]


__all__ = ["QuantityJSON"]
