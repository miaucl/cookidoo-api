"""Test response for cookidoo-api."""

from typing import Final

from tests.conftest import UUID

COOKIDOO_TEST_RESPONSE_AUTH_RESPONSE: Final = {
    "access_token": "eyJhbGciOiJ<redacted>",
    "expires_in": 43199,
    "id_token": "eyJhbGciOiJSUzI1Ni<redacted>",
    "iss": "https://eu.login.vorwerk.com/",
    "jti": "9f97a234-3f80-4e35-bf48-2e3e9e7e8720",
    "refresh_token": "eyJhbGciOiJSUzI1Ni<redacted>",
    "scope": "marcossapi openid profile email Online offline_access",
    "token_type": "bearer",
    "sub": "sub_uuid",
}

COOKIDOO_TEST_RESPONSE_USER_INFO: Final = {
    "id": UUID,
    "isPublic": False,
    "userInfo": {
        "username": "Test User",
        "description": "",
        "picture": "",
        "pictureTemplate": "",
    },
    "savedSearches": [
        {
            "id": "default",
            "search": {
                "countries": ["ch"],
                "languages": ["de"],
                "accessories": [
                    "includingFriend",
                    "includingBladeCover",
                    "includingBladeCoverWithPeeler",
                    "includingCutter",
                    "includingSensor",
                ],
            },
        }
    ],
    "foodPreferences": [],
    "meta": {
        "cloudinaryPublicId": "61c22d8465a60c86de8ca7ce045665bfa35546d78ba6f971ffbed3780d4fa026"
    },
    "thermomixes": [],
}

COOKIDOO_TEST_RESPONSE_ACTIVE_SUBSCRIPTION: Final = [
    {
        "active": True,
        "startDate": "2024-09-15T00:00:00Z",
        "expires": "2024-10-15T23:59:00Z",
        "type": "TRIAL",
        "extendedType": "TRIAL",
        "autoRenewalProduct": "Cookidoo 1 Month Free",
        "autoRenewalProductCode": None,
        "countryOfResidence": "ch",
        "subscriptionLevel": "NONE",
        "status": "RUNNING",
        "marketMismatch": False,
        "subscriptionSource": "COMMERCE",
        "_created": "2024-10-30T15:38:26.496029003Z",
        "_modified": None,
    }
]

COOKIDOO_TEST_RESPONSE_INACTIVE_SUBSCRIPTION: Final = [
    {
        "active": False,
        "startDate": "2024-09-15T00:00:00Z",
        "expires": "2024-10-15T23:59:00Z",
        "type": "TRIAL",
        "extendedType": "TRIAL",
        "autoRenewalProduct": "Cookidoo 1 Month Free",
        "autoRenewalProductCode": None,
        "countryOfResidence": "ch",
        "subscriptionLevel": "NONE",
        "status": "ENDED",
        "marketMismatch": False,
        "subscriptionSource": "COMMERCE",
        "_created": "2024-10-30T15:38:26.496029003Z",
        "_modified": None,
    }
]

COOKIDOO_TEST_RESPONSE_GET_RECIPE_DETAILS = {
    "id": "r907015",
    "tags": [
        {"id": "40-recipetag-rdpf3", "name": "Fingerfood"},
        {"id": "143-recipetag-rdpf3", "name": "Vegetarisch"},
        {"id": "166-recipetag-rdpf3", "name": "alkoholfrei"},
        {"id": "167-recipetag-rdpf3", "name": "Glutenfrei"},
        {"id": "212-marketingtag-rdpf3", "name": "Weihnachten"},
        {"id": "233-marketingtag-rdpf3", "name": "Winter"},
        {"id": "247-marketingtag-rdpf3", "name": "Geschenk"},
        {"id": "8-marketingtag-rdpf3", "name": "Europäisch"},
        {"id": "209-marketingtag-rdpf3", "name": "Herbst"},
        {"id": "230-marketingtag-rdpf3", "name": "Sommer"},
        {"id": "228-marketingtag-rdpf3", "name": "Frühling"},
        {"id": "238-marketingtag-rdpf3", "name": "Geburtstag"},
        {"id": "253-marketingtag-rdpf3", "name": "Party"},
    ],
    "times": [
        {"type": "activeTime", "comment": "", "quantity": {"value": 2700}},
        {"type": "totalTime", "comment": "", "quantity": {"value": 32400}},
    ],
    "title": "Kokos Pralinen",
    "locale": "ch",
    "status": "ok",
    "markets": ["ch"],
    "language": "de",
    "categories": [
        {
            "id": "VrkNavCategory-RPF-011",
            "title": "Desserts, Pâtisserie und Süssigkeiten",
            "subtitle": "",
            "defaultTitle": "Desserts and sweets",
        },
        {
            "id": "VrkNavCategory-RPF-020",
            "title": "Snacks",
            "subtitle": "",
            "defaultTitle": "Snacks and finger food",
        },
    ],
    "difficulty": "easy",
    "exportDate": "2024-10-28T16:08:56Z",
    "ingredients": [
        {
            "id": "com.vorwerk.ingredients.Ingredient-rpf-322",
            "title": "Kokosraspeln",
            "defaultTitle": "coconut, dried, grated, unsweetened",
            "primaryNotation": "Kokosnuss, getrocknet, geraspelt, ungesüsst",
            "shoppingCategory_ref": "com.vorwerk.categories.ShoppingCategory-rpf-6",
        },
        {
            "id": "com.vorwerk.ingredients.Ingredient-rpf-319",
            "title": "gezuckerte Kondensmilch",
            "defaultTitle": "condensed milk, sweetened",
            "primaryNotation": "gezuckerte Kondensmilch",
            "shoppingCategory_ref": "com.vorwerk.categories.ShoppingCategory-rpf-2",
        },
        {
            "id": "com.vorwerk.ingredients.Ingredient-rpf-17",
            "title": "Butter",
            "defaultTitle": "butter, unsalted (from cows' milk)",
            "primaryNotation": "Butter",
            "shoppingCategory_ref": "com.vorwerk.categories.ShoppingCategory-rpf-2",
        },
    ],
    "servingSize": {"quantity": {"value": 50}, "unitNotation": "Stück"},
    "recipeUtensils": [
        {"utensilRef": "5460-utensil-rdpf3", "utensilNotation": "Kühlschrank"}
    ],
    "categories_refs": ["VrkNavCategory-RPF-011", "VrkNavCategory-RPF-020"],
    "nutritionGroups": [
        {
            "name": "",
            "recipeNutritions": [
                {
                    "quantity": 1,
                    "nutritions": [
                        {"type": "kJ", "number": 275, "unittype": "kJ"},
                        {"type": "kcal", "number": 65.7, "unittype": "kcal"},
                        {"type": "protein", "number": 1, "unittype": "g"},
                        {"type": "carb2", "number": 5.6, "unittype": "g"},
                        {"type": "fat", "number": 4.7, "unittype": "g"},
                        {"type": "dietaryFibre", "number": 0.8, "unittype": "g"},
                    ],
                    "unitNotation": "Stück",
                }
            ],
        }
    ],
    "optionalDevices": [],
    "publicationDate": "2024-10-29T06:00:00Z",
    "targetCountries": ["ch"],
    "recipeStepGroups": [
        {
            "title": "",
            "recipeSteps": [
                {
                    "title": "1",
                    "formattedText": "<NOBR>200 g Kokosraspeln</NOBR> in den Mixtopf geben und <nobr>15 Sek./Stufe 8</nobr> zerkleinern. In eine Schüssel umfüllen und beiseitestellen.",
                },
                {
                    "title": "2",
                    "formattedText": "Kondensmilch und Butter in den Mixtopf geben und <nobr>6 Min./100°C/Stufe 2</nobr> kochen.",
                },
                {
                    "title": "3",
                    "formattedText": "Gemahlene Kokosraspeln zugeben und <nobr>2 Min./Stufe 4</nobr> vermischen. In eine Schüssel umfüllen und mindestens 8 Stunden, am besten über Nacht, in den Kühlschrank stellen.",
                },
                {
                    "title": "4",
                    "formattedText": "60 g Kokosraspeln auf einen Teller geben. Aus der Kokos-Milch-Mischung kleine Kugeln formen <NOBR>(ca. Ø 1 cm)</NOBR>, in den Kokosraspeln wälzen und bis zum Servieren kühl stellen.",
                },
            ],
        }
    ],
    "additionalDevices": [],
    "descriptiveAssets": [
        {
            "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
            "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
            "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
        },
        {
            "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/4c59187077a8767c919bd168a066c224/Derivates/dd52ed01ce418450cb05f7ef7eb9caf32d934b6f",
            "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/4c59187077a8767c919bd168a066c224/Derivates/dd52ed01ce418450cb05f7ef7eb9caf32d934b6f",
            "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/4c59187077a8767c919bd168a066c224/Derivates/dd52ed01ce418450cb05f7ef7eb9caf32d934b6f",
        },
    ],
    "thermomixVersions": ["TM5", "TM6"],
    "additionalInformation": [
        {
            "type": "VrkRecipeAdditionalInformationType",
            "content": "Die Pralinen sollen kühl aufbewahrt und gegessen werden. Sie können auch eingefroren werden.",
        }
    ],
    "recipeIngredientGroups": [
        {
            "title": "",
            "recipeIngredients": [
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-322",
                    "optional": False,
                    "quantity": {"wrong_value": 260},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-322",
                    "ingredientNotation": "Kokosraspeln",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-319",
                    "optional": False,
                    "quantity": {"value": 400},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-319",
                    "ingredientNotation": "gezuckerte Kondensmilch",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-17",
                    "optional": False,
                    "quantity": {"from": 40, "to": 60},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": ", in Stücken",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-17",
                    "ingredientNotation": "Butter",
                },
            ],
        }
    ],
    "inCollections": [
        {
            "id": "col500561",
            "title": "Schneeweiss und Zuckersüss",
            "recipesCount": {"value": 6, "text": "other"},
            "market": "ch",
            "descriptiveAssets": [
                {
                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/collection/ras/Assets/38cf56dff995c01c9a4ce2ce3b9f0bf8/Derivates/d8d563384bbd2652791aedfcb3200dde0e6221cb"
                }
            ],
        }
    ],
}

COOKIDOO_TEST_RESPONSE_GET_CUSTOM_RECIPE = {
    "recipeId": "01K2CVHD1DXG1PVETNVV3JPKWW",
    "authorId": "2d336b56-6c23-49bb-9543-5bdf0344eedf",
    "modifiedAt": "2025-08-11T17:03:20.415Z",
    "createdAt": "2025-08-11T15:21:15.566Z",
    "status": "ACTIVE",
    "workStatus": "PUBLIC",
    "recipeContent": {
        "name": "Vongole alla marinara",
        "image": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/29F42E5A-098A-46BC-87C5-59CF7C81E44D/Derivates/43ADC698-B45F-41E2-A479-FA5BC32702C6",
        "isBasedOn": "https://cookidoo.ch/recipes/recipe/en/r166987",
        "totalTime": "PT30M",
        "prepTime": "PT10M",
        "tool": ["TM7", "TM6", "TM5"],
        "recipeYield": {"value": 6, "unitText": "portion"},
        "recipeIngredient": [
            "130 g di cipolla",
            "1 ¼ - 2 ¼ spicchi di aglio",
            "65 g di olio extravergine di oliva",
            "1500 g di vongole fresche, pulite",
            "1 pizzico di pepe macinato",
            "65 g di vino bianco",
            "190 g di brodo di pesce",
            "2 ½ cucchiaini di prezzemolo fresco, tritato, sole le foglioline",
            "1 ¼ cucchiaino di pangrattato",
            "⅔ cucchiaino di sale",
        ],
        "recipeInstructions": [
            "Mettere nel boccale le cipolle, gli spicchi di aglio e l’olio extravergine di oliva, tritare: 4 sec./vel. 5. Insaporire: 10 min./120°C/vel. 1. Nel frattempo, mettere le vongole nel Varoma e risciacquarle in acqua calda. Tenere da parte.",
            "Aggiungere nel boccale il pepe, il vino bianco e il brodo. Posizionare il Varoma e cuocere a vapore: 14 min./Varoma/vel. 2.",
            "Togliere il Varoma. Aggiungere i prezzemolo, il pangrattato e il sale, mescolare: 15 sec./vel. 2. Trasferire le vongole in un piatto da portata, versare sopra la salsa e spolverizzare con il prezzemolo. Servire subito.",
        ],
    },
}

COOKIDOO_TEST_RESPONSE_ADD_CUSTOM_RECIPE = {
    "recipeId": "01K2CTJ9Y1BABRG5MXK44CFZS4",
    "authorId": "2d336b56-6c23-49bb-9543-5bdf0344eedf",
    "modifiedAt": "2025-08-11T15:04:16.577Z",
    "createdAt": "2025-08-11T15:04:16.577Z",
    "status": "ACTIVE",
    "workStatus": "PRIVATE",
    "recipeContent": {
        "name": "Vongole alla marinara",
        "image": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/29F42E5A-098A-46BC-87C5-59CF7C81E44D/Derivates/43ADC698-B45F-41E2-A479-FA5BC32702C6",
        "isBasedOn": "https://cookidoo.ch/recipes/recipe/en/r166987",
        "totalTime": "PT30M",
        "prepTime": "PT10M",
        "tool": ["TM7", "TM6", "TM5"],
        "recipeYield": {"value": 6, "unitText": "portion"},
        "recipeIngredient": [
            "130 g di cipolla",
            "1 ¼ - 2 ¼ spicchi di aglio",
            "65 g di olio extravergine di oliva",
            "1500 g di vongole fresche, pulite",
            "1 pizzico di pepe macinato",
            "65 g di vino bianco",
            "190 g di brodo di pesce",
            "2 ½ cucchiaini di prezzemolo fresco, tritato, sole le foglioline",
            "1 ¼ cucchiaino di pangrattato",
            "⅔ cucchiaino di sale",
        ],
        "recipeInstructions": [
            "Mettere nel boccale le cipolle, gli spicchi di aglio e l’olio extravergine di oliva, tritare: 4 sec./vel. 5. Insaporire: 10 min./120°C/vel. 1. Nel frattempo, mettere le vongole nel Varoma e risciacquarle in acqua calda. Tenere da parte.",
            "Aggiungere nel boccale il pepe, il vino bianco e il brodo. Posizionare il Varoma e cuocere a vapore: 14 min./Varoma/vel. 2.",
            "Togliere il Varoma. Aggiungere i prezzemolo, il pangrattato e il sale, mescolare: 15 sec./vel. 2. Trasferire le vongole in un piatto da portata, versare sopra la salsa e spolverizzare con il prezzemolo. Servire subito.",
        ],
    },
}

COOKIDOO_TEST_RESPONSE_GET_SHOPPING_LIST_RECIPES = {
    "recipes": [
        {
            "id": "r907016",
            "ulid": "01JBQFM448MWF37WM0CQ763MQ8",
            "title": "Mini-Pavlova mit Orangen",
            "locale": "ch",
            "status": "ok",
            "language": "de",
            "hasVariants": False,
            "isCustomerRecipe": False,
            "descriptiveAssets": [
                {
                    "something_else": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                    "broken": None,
                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                },
                {
                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c7868b18e43639134880b2777d7fcd9f/Derivates/f7e9031db49d24e9e8e37e98618a830dda45b596",
                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c7868b18e43639134880b2777d7fcd9f/Derivates/f7e9031db49d24e9e8e37e98618a830dda45b596",
                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c7868b18e43639134880b2777d7fcd9f/Derivates/f7e9031db49d24e9e8e37e98618a830dda45b596",
                },
            ],
            "recipeIngredientGroups": [
                {
                    "id": "01JBQFM44769BTC1P25CNDWJK9",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-9",
                    "optional": False,
                    "quantity": {"value": 200},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-9",
                    "ingredientNotation": "Zucker",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-6",
                },
                {
                    "id": "01JBQFM447GYJYP0QR4EYSEX75",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-116",
                    "optional": False,
                    "quantity": {"value": 4},
                    "unit_ref": "",
                    "preparation": ", kalt",
                    "unitNotation": "",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-116",
                    "ingredientNotation": "Eiweisse",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                },
                {
                    "id": "01JBQFM447EDC3NKF6RZAQ9FQV",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-269",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "65-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "Prise",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-269",
                    "ingredientNotation": "Salz",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-5",
                },
                {
                    "id": "01JBQFM44772YQA0204VFQZTG9",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-46",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "23-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "TL",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-46",
                    "ingredientNotation": "Zitronensaft",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-9",
                },
                {
                    "id": "01JBQFM447TKG7A721C375CF0P",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-288",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "25-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "EL",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-288",
                    "ingredientNotation": "Maizena",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-7",
                },
                {
                    "id": "01JBQFM447HKJH45AWGHHG87Q9",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-316",
                    "optional": False,
                    "quantity": {"value": 4},
                    "unit_ref": "",
                    "preparation": ", geschält, filetiert",
                    "unitNotation": "",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-316",
                    "ingredientNotation": "Orangen",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-8",
                },
                {
                    "id": "01JBQFM4476W1BN6VZBSTZ50KG",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-620",
                    "optional": False,
                    "quantity": {"value": 180},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-620",
                    "ingredientNotation": "Crème fraîche",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-2",
                },
            ],
        },
        {
            "id": "r59322",
            "ulid": "01JBQFM447FVYJP9YP0F35PNY9",
            "title": "Vollwert-Brötchen/Baguettes",
            "locale": "de",
            "status": "ok",
            "language": "de",
            "clusterId": "043293bf-82be-4548-b2c2-6bb651574c6e",
            "hasVariants": True,
            "servingSize": {"quantity": {"value": 12}, "unitNotation": "Stück"},
            "isCustomerRecipe": False,
            "descriptiveAssets": [
                {
                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/665554F6-0147-480B-9CB6-36CC5181140F/Derivates/5D3D75B4-8136-4E6A-8096-861037D5CA12",
                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/665554F6-0147-480B-9CB6-36CC5181140F/Derivates/5D3D75B4-8136-4E6A-8096-861037D5CA12",
                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/665554F6-0147-480B-9CB6-36CC5181140F/Derivates/5D3D75B4-8136-4E6A-8096-861037D5CA12",
                }
            ],
            "recipeIngredientGroups": [
                {
                    "id": "01JBQFM446FATGVE3EXT8YXSRJ",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-181",
                    "optional": False,
                    "quantity": {"value": 100},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-181",
                    "ingredientNotation": "Weizenkörner",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-7",
                    "recipeAlternativeIngredient": {
                        "localId": "com.vorwerk.ingredients.Ingredient-rpf-185",
                        "optional": False,
                        "quantity": {"value": 100},
                        "unit_ref": "11-unit-rdpf3",
                        "preparation": "",
                        "unitNotation": "g",
                        "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-185",
                        "ingredientNotation": "Dinkelkörner",
                    },
                },
                {
                    "id": "01JBQFM446JK3AW6S781AQ69NE",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-40",
                    "optional": False,
                    "quantity": {"value": 400},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-40",
                    "ingredientNotation": "Weizenmehl",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-7",
                },
                {
                    "id": "01JBQFM447X5SPZX7N1EXJAJKB",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-269",
                    "optional": False,
                    "quantity": {"value": 1.5},
                    "unit_ref": "23-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "TL",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-269",
                    "ingredientNotation": "Salz",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-5",
                },
                {
                    "id": "01JBQFM4472Z498TSDDE11C2EG",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-54",
                    "optional": False,
                    "quantity": {"value": 220},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-54",
                    "ingredientNotation": "Wasser",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-9",
                },
                {
                    "id": "01JBQFM447GRGV27DW8JZRWQNX",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-151",
                    "optional": False,
                    "quantity": {"value": 40},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-151",
                    "ingredientNotation": "Öl",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-11",
                },
                {
                    "id": "01JBQFM44709X31KCPYZ1YJ2NS",
                    "isOwned": True,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-345",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "132-unit-rdpf3",
                    "preparation": "(40 g)",
                    "unitNotation": "Würfel",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-345",
                    "ownedTimestamp": 1730586218,
                    "ingredientNotation": "Hefe",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                },
                {
                    "id": "01JBQFM447DFBB3B109XJ82EGM",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-9",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "65-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "Prise",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-9",
                    "ingredientNotation": "Zucker",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-6",
                },
            ],
        },
    ],
    "customerRecipes": [],
    "additionalItems": [],
}


COOKIDOO_TEST_RESPONSE_GET_INGREDIENTS_FOR_RECIPES = {
    "recipes": [
        {
            "id": "r907016",
            "ulid": "01JBQFM448MWF37WM0CQ763MQ8",
            "title": "Mini-Pavlova mit Orangen",
            "locale": "ch",
            "status": "ok",
            "language": "de",
            "hasVariants": False,
            "isCustomerRecipe": False,
            "descriptiveAssets": [
                {
                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                },
                {
                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c7868b18e43639134880b2777d7fcd9f/Derivates/f7e9031db49d24e9e8e37e98618a830dda45b596",
                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c7868b18e43639134880b2777d7fcd9f/Derivates/f7e9031db49d24e9e8e37e98618a830dda45b596",
                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c7868b18e43639134880b2777d7fcd9f/Derivates/f7e9031db49d24e9e8e37e98618a830dda45b596",
                },
            ],
            "recipeIngredientGroups": [
                {
                    "id": "01JBQFM44769BTC1P25CNDWJK9",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-9",
                    "optional": False,
                    "quantity": {"value": 200},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-9",
                    "ingredientNotation": "Zucker",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-6",
                },
                {
                    "id": "01JBQFM447GYJYP0QR4EYSEX75",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-116",
                    "optional": False,
                    "quantity": {"value": 4},
                    "unit_ref": "",
                    "preparation": ", kalt",
                    "unitNotation": "",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-116",
                    "ingredientNotation": "Eiweisse",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                },
                {
                    "id": "01JBQFM447EDC3NKF6RZAQ9FQV",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-269",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "65-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "Prise",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-269",
                    "ingredientNotation": "Salz",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-5",
                },
                {
                    "id": "01JBQFM44772YQA0204VFQZTG9",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-46",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "23-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "TL",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-46",
                    "ingredientNotation": "Zitronensaft",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-9",
                },
                {
                    "id": "01JBQFM447TKG7A721C375CF0P",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-288",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "25-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "EL",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-288",
                    "ingredientNotation": "Maizena",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-7",
                },
                {
                    "id": "01JBQFM447HKJH45AWGHHG87Q9",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-316",
                    "optional": False,
                    "quantity": {"value": 4},
                    "unit_ref": "",
                    "preparation": ", geschält, filetiert",
                    "unitNotation": "",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-316",
                    "ingredientNotation": "Orangen",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-8",
                },
                {
                    "id": "01JBQFM4476W1BN6VZBSTZ50KG",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-620",
                    "optional": False,
                    "quantity": {"value": 180},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-620",
                    "ingredientNotation": "Crème fraîche",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-2",
                },
            ],
        },
        {
            "id": "r59322",
            "ulid": "01JBQFM447FVYJP9YP0F35PNY9",
            "title": "Vollwert-Brötchen/Baguettes",
            "locale": "de",
            "status": "ok",
            "language": "de",
            "clusterId": "043293bf-82be-4548-b2c2-6bb651574c6e",
            "hasVariants": True,
            "servingSize": {"quantity": {"value": 12}, "unitNotation": "Stück"},
            "isCustomerRecipe": False,
            "descriptiveAssets": [
                {
                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/665554F6-0147-480B-9CB6-36CC5181140F/Derivates/5D3D75B4-8136-4E6A-8096-861037D5CA12",
                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/665554F6-0147-480B-9CB6-36CC5181140F/Derivates/5D3D75B4-8136-4E6A-8096-861037D5CA12",
                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/665554F6-0147-480B-9CB6-36CC5181140F/Derivates/5D3D75B4-8136-4E6A-8096-861037D5CA12",
                }
            ],
            "recipeIngredientGroups": [
                {
                    "id": "01JBQFM446FATGVE3EXT8YXSRJ",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-181",
                    "optional": False,
                    "quantity": {"value": 100},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-181",
                    "ingredientNotation": "Weizenkörner",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-7",
                    "recipeAlternativeIngredient": {
                        "localId": "com.vorwerk.ingredients.Ingredient-rpf-185",
                        "optional": False,
                        "quantity": {"value": 100},
                        "unit_ref": "11-unit-rdpf3",
                        "preparation": "",
                        "unitNotation": "g",
                        "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-185",
                        "ingredientNotation": "Dinkelkörner",
                    },
                },
                {
                    "id": "01JBQFM446JK3AW6S781AQ69NE",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-40",
                    "optional": False,
                    "quantity": {"value": 400},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-40",
                    "ingredientNotation": "Weizenmehl",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-7",
                },
                {
                    "id": "01JBQFM447X5SPZX7N1EXJAJKB",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-269",
                    "optional": False,
                    "quantity": {"value": 1.5},
                    "unit_ref": "23-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "TL",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-269",
                    "ingredientNotation": "Salz",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-5",
                },
                {
                    "id": "01JBQFM4472Z498TSDDE11C2EG",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-54",
                    "optional": False,
                    "quantity": {"value": 220},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-54",
                    "ingredientNotation": "Wasser",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-9",
                },
                {
                    "id": "01JBQFM447GRGV27DW8JZRWQNX",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-151",
                    "optional": False,
                    "quantity": {"value": 40},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-151",
                    "ingredientNotation": "Öl",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-11",
                },
                {
                    "id": "01JBQFM44709X31KCPYZ1YJ2NS",
                    "isOwned": True,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-345",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "132-unit-rdpf3",
                    "preparation": "(40 g)",
                    "unitNotation": "Würfel",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-345",
                    "ownedTimestamp": 1730586218,
                    "ingredientNotation": "Hefe",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                },
                {
                    "id": "01JBQFM447DFBB3B109XJ82EGM",
                    "isOwned": False,
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-9",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "65-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "Prise",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-9",
                    "ingredientNotation": "Zucker",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-6",
                },
            ],
        },
    ],
    "customerRecipes": [],
    "additionalItems": [],
}

COOKIDOO_TEST_RESPONSE_GET_INGREDIENTS_FOR_CUSTOM_RECIPES = {
    "recipes": [],
    "customerRecipes": [
        {
            "id": "01K2CVHD1DXG1PVETNVV3JPKWW",
            "ulid": "01K2CVHK2NP5WF73D0YKTJB6M2",
            "title": "Vongole alla marinara",
            "status": "ACTIVE",
            "isCustomerRecipe": True,
            "descriptiveAssets": [
                {
                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/29F42E5A-098A-46BC-87C5-59CF7C81E44D/Derivates/43ADC698-B45F-41E2-A479-FA5BC32702C6"
                }
            ],
            "recipeIngredientGroups": [
                {
                    "id": "01K2CVHK2FPHMN9J2HYWMHTCCC",
                    "isOwned": False,
                    "ingredientNotation": "130 g di cipolla",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                },
                {
                    "id": "01K2CVHK2F18DK6JH3CTG22YJP",
                    "isOwned": False,
                    "ingredientNotation": "1 ¼ - 2 ¼ spicchi di aglio",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                },
                {
                    "id": "01K2CVHK2FA9D0C2952PGKZ3TM",
                    "isOwned": False,
                    "ingredientNotation": "65 g di olio extravergine di oliva",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                },
                {
                    "id": "01K2CVHK2F7YW0AVG89QMWJHHH",
                    "isOwned": False,
                    "ingredientNotation": "1500 g di vongole fresche, pulite",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                },
                {
                    "id": "01K2CVHK2F3M0B47FYE6FBQHTH",
                    "isOwned": False,
                    "ingredientNotation": "1 pizzico di pepe macinato",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                },
                {
                    "id": "01K2CVHK2G5ESTXM37R28QZY29",
                    "isOwned": False,
                    "ingredientNotation": "65 g di vino bianco",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                },
                {
                    "id": "01K2CVHK2GWSCX4RGK4RWE2K6K",
                    "isOwned": False,
                    "ingredientNotation": "190 g di brodo di pesce",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                },
                {
                    "id": "01K2CVHK2GY5BM0MMX299YHMMB",
                    "isOwned": False,
                    "ingredientNotation": "2 ½ cucchiaini di prezzemolo fresco, tritato, sole le foglioline",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                },
                {
                    "id": "01K2CVHK2GPGEMQTQNW353KX18",
                    "isOwned": False,
                    "ingredientNotation": "1 ¼ cucchiaino di pangrattato",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                },
                {
                    "id": "01K2CVHK2G4KMDXX8BRYCRYYG7",
                    "isOwned": False,
                    "ingredientNotation": "⅔ cucchiaino di sale",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                },
            ],
        }
    ],
    "additionalItems": [],
}


COOKIDOO_TEST_RESPONSE_ADD_INGREDIENTS_FOR_RECIPES: Final = {
    "data": [
        {
            "id": "r59322",
            "title": "Vollwert-Brötchen/Baguettes",
            "locale": "de",
            "language": "de",
            "status": "ok",
            "ulid": "01JBQEYRFQ219DZVSFEG59AWYS",
            "clusterId": "043293bf-82be-4548-b2c2-6bb651574c6e",
            "hasVariants": True,
            "servingSize": {"quantity": {"value": 12}, "unitNotation": "Stück"},
            "descriptiveAssets": [
                {
                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/665554F6-0147-480B-9CB6-36CC5181140F/Derivates/5D3D75B4-8136-4E6A-8096-861037D5CA12",
                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/665554F6-0147-480B-9CB6-36CC5181140F/Derivates/5D3D75B4-8136-4E6A-8096-861037D5CA12",
                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/665554F6-0147-480B-9CB6-36CC5181140F/Derivates/5D3D75B4-8136-4E6A-8096-861037D5CA12",
                }
            ],
            "isCustomerRecipe": False,
            "recipeIngredientGroups": [
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-181",
                    "optional": False,
                    "quantity": {"value": 100},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-181",
                    "ingredientNotation": "Weizenkörner",
                    "recipeAlternativeIngredient": {
                        "localId": "com.vorwerk.ingredients.Ingredient-rpf-185",
                        "optional": False,
                        "quantity": {"value": 100},
                        "unit_ref": "11-unit-rdpf3",
                        "preparation": "",
                        "unitNotation": "g",
                        "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-185",
                        "ingredientNotation": "Dinkelkörner",
                    },
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-7",
                    "id": "01JBQEYRFQWG8ZQ20SMKB1JP6S",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-40",
                    "optional": False,
                    "quantity": {"value": 400},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-40",
                    "ingredientNotation": "Weizenmehl",
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-7",
                    "id": "01JBQEYRFQEVSSW39WFJVNH18Y",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-269",
                    "optional": False,
                    "quantity": {"value": 1.5},
                    "unit_ref": "23-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "TL",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-269",
                    "ingredientNotation": "Salz",
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-5",
                    "id": "01JBQEYRFQF6E7VNRPVDHMW9ET",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-54",
                    "optional": False,
                    "quantity": {"value": 220},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-54",
                    "ingredientNotation": "Wasser",
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-9",
                    "id": "01JBQEYRFQ4F96ZZ039H8868VW",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-151",
                    "optional": False,
                    "quantity": {"value": 40},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-151",
                    "ingredientNotation": "Öl",
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-11",
                    "id": "01JBQEYRFQ10JYVGWPS3E89WKR",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-345",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "132-unit-rdpf3",
                    "preparation": "(40 g)",
                    "unitNotation": "Würfel",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-345",
                    "ingredientNotation": "Hefe",
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "id": "01JBQEYRFQHK543XN78Z622J92",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-9",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "65-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "Prise",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-9",
                    "ingredientNotation": "Zucker",
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-6",
                    "id": "01JBQEYRFQRZT6XF19N3QDK16J",
                },
            ],
        },
        {
            "id": "r907016",
            "title": "Mini-Pavlova mit Orangen",
            "locale": "ch",
            "language": "de",
            "status": "ok",
            "ulid": "01JBQEYRFRD37Z0F4JB23WAAJR",
            "hasVariants": False,
            "descriptiveAssets": [
                {
                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                },
                {
                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c7868b18e43639134880b2777d7fcd9f/Derivates/f7e9031db49d24e9e8e37e98618a830dda45b596",
                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c7868b18e43639134880b2777d7fcd9f/Derivates/f7e9031db49d24e9e8e37e98618a830dda45b596",
                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c7868b18e43639134880b2777d7fcd9f/Derivates/f7e9031db49d24e9e8e37e98618a830dda45b596",
                },
            ],
            "isCustomerRecipe": False,
            "recipeIngredientGroups": [
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-9",
                    "optional": False,
                    "quantity": {"value": 200},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-9",
                    "ingredientNotation": "Zucker",
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-6",
                    "id": "01JBQEYRFQAH4W0NEC6KNPBAC9",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-116",
                    "optional": False,
                    "quantity": {"value": 4},
                    "unit_ref": "",
                    "preparation": ", kalt",
                    "unitNotation": "",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-116",
                    "ingredientNotation": "Eiweisse",
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "id": "01JBQEYRFQCWZWG0KY02BAMB3P",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-269",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "65-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "Prise",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-269",
                    "ingredientNotation": "Salz",
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-5",
                    "id": "01JBQEYRFQFVEJZYT1MSQJ147H",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-46",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "23-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "TL",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-46",
                    "ingredientNotation": "Zitronensaft",
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-9",
                    "id": "01JBQEYRFQQ39D3HZS4W6RP4D1",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-288",
                    "optional": False,
                    "quantity": {"value": 1},
                    "unit_ref": "25-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "EL",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-288",
                    "ingredientNotation": "Maizena",
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-7",
                    "id": "01JBQEYRFR908830YPYSE5NECB",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-316",
                    "optional": False,
                    "quantity": {"value": 4},
                    "unit_ref": "",
                    "preparation": ", geschält, filetiert",
                    "unitNotation": "",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-316",
                    "ingredientNotation": "Orangen",
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-8",
                    "id": "01JBQEYRFRRJKKDPJ39403ATTT",
                },
                {
                    "localId": "com.vorwerk.ingredients.Ingredient-rpf-620",
                    "optional": False,
                    "quantity": {"value": 180},
                    "unit_ref": "11-unit-rdpf3",
                    "preparation": "",
                    "unitNotation": "g",
                    "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-620",
                    "ingredientNotation": "Crème fraîche",
                    "isOwned": False,
                    "shoppingCategory_ref": "ShoppingCategory-rpf-2",
                    "id": "01JBQEYRFRJVE95ETRRZABSH57",
                },
            ],
        },
    ]
}

COOKIDOO_TEST_RESPONSE_EDIT_INGREDIENTS_OWNERSHIP = {
    "data": [
        {
            "id": "01JBQG02JQD3XPFMM5CXE51K25",
            "isOwned": True,
            "localId": "com.vorwerk.ingredients.Ingredient-rpf-345",
            "optional": False,
            "quantity": {"value": 1},
            "unit_ref": "132-unit-rdpf3",
            "preparation": "(40 g)",
            "unitNotation": "Würfel",
            "ingredient_ref": "com.vorwerk.ingredients.Ingredient-rpf-345",
            "ingredientNotation": "Hefe",
            "shoppingCategory_ref": "ShoppingCategory-rpf-10",
            "ownedTimestamp": 1730586610,
        }
    ]
}

COOKIDOO_TEST_RESPONSE_ADD_INGREDIENTS_FOR_CUSTOM_RECIPES = {
    "data": [
        {
            "id": "01K2CTJ9Y1BABRG5MXK44CFZS4",
            "title": "Vongole alla marinara",
            "status": "ACTIVE",
            "ulid": "01K2CTZSSKFKJWPM71017SJYMC",
            "descriptiveAssets": [
                {
                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/29F42E5A-098A-46BC-87C5-59CF7C81E44D/Derivates/43ADC698-B45F-41E2-A479-FA5BC32702C6"
                }
            ],
            "isCustomerRecipe": True,
            "recipeIngredientGroups": [
                {
                    "id": "01K2CTZSSCR2DTKBKJ4ATG9XGG",
                    "ingredientNotation": "130 g di cipolla",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                    "isOwned": False,
                },
                {
                    "id": "01K2CTZSSC52YNH2A5Z900VHCM",
                    "ingredientNotation": "1 ¼ - 2 ¼ spicchi di aglio",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                    "isOwned": False,
                },
                {
                    "id": "01K2CTZSSCV9A1HG9VBZEHJMM6",
                    "ingredientNotation": "65 g di olio extravergine di oliva",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                    "isOwned": False,
                },
                {
                    "id": "01K2CTZSSC707ACTRF4CHX3WA7",
                    "ingredientNotation": "1500 g di vongole fresche, pulite",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                    "isOwned": False,
                },
                {
                    "id": "01K2CTZSSC7RVAX5PMDRMB7XT0",
                    "ingredientNotation": "1 pizzico di pepe macinato",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                    "isOwned": False,
                },
                {
                    "id": "01K2CTZSSC72ZA53Z0PYT21XYN",
                    "ingredientNotation": "65 g di vino bianco",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                    "isOwned": False,
                },
                {
                    "id": "01K2CTZSSC6WRA31EN9656EW7D",
                    "ingredientNotation": "190 g di brodo di pesce",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                    "isOwned": False,
                },
                {
                    "id": "01K2CTZSSC5J3Z0CAVY20Z08SZ",
                    "ingredientNotation": "2 ½ cucchiaini di prezzemolo fresco, tritato, sole le foglioline",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                    "isOwned": False,
                },
                {
                    "id": "01K2CTZSSCWQ0RVV3SNXSCJK0T",
                    "ingredientNotation": "1 ¼ cucchiaino di pangrattato",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                    "isOwned": False,
                },
                {
                    "id": "01K2CTZSSC7CYHWPZH00HS238C",
                    "ingredientNotation": "⅔ cucchiaino di sale",
                    "shoppingCategory_ref": "ShoppingCategory-rpf-10",
                    "isCustomerRecipeIngredient": True,
                    "isOwned": False,
                },
            ],
        }
    ]
}

COOKIDOO_TEST_RESPONSE_GET_ADDITIONAL_ITEMS = {
    "recipes": [],
    "customerRecipes": [],
    "additionalItems": [
        {"id": "01JBQGAG2VEJM15JWW9C7BQN5W", "name": "Fleisch", "isOwned": False},
        {
            "id": "01JBQGAG2WH9EQ9GHH7XN7NWGP",
            "name": "Vogel",
            "isOwned": True,
            "ownedTimestamp": 1730586951,
        },
    ],
}

COOKIDOO_TEST_RESPONSE_ADD_ADDITIONAL_ITEMS = {
    "data": [
        {"id": "01JBQGDMRMR7RJW1C8AWDGD6YP", "name": "Fleisch", "isOwned": False},
        {"id": "01JBQGDMRNHAM7AMCR6YKPYKJQ", "name": "Fisch", "isOwned": False},
    ]
}

COOKIDOO_TEST_RESPONSE_EDIT_ADDITIONAL_ITEMS_OWNERSHIP = {
    "data": [
        {
            "id": "01JBQGMGMY4KD9ZGTKAS6GQME0",
            "name": "Fisch",
            "isOwned": True,
            "ownedTimestamp": 1730587279,
        }
    ]
}

COOKIDOO_TEST_RESPONSE_EDIT_ADDITIONAL_ITEMS = {
    "data": [
        {
            "id": "01JBQGT72WP8Z31VCPQPT5VC6F",
            "name": "Vogel",
            "isOwned": True,
            "ownedTimestamp": 1730587466,
        }
    ]
}

COOKIDOO_TEST_RESPONSE_GET_MANAGED_COLLECTIONS = {
    "managedlists": [
        {
            "id": "col500561",
            "created": "2024-11-06T22:28:13.202+00:00",
            "modified": "2024-11-06T22:28:13.202+00:00",
            "title": "Schneeweiss und Zuckersüss",
            "description": "Schneeweisse Delikatessen wie Pralinen und cremige Desserts sind ein wahres Fest für den Gaumen. In dieser Kollektion entdeckst du einige zuckersüsse Ideen, die mühelos mit deinem Thermomix® zubereitet werden können.",
            "chapters": [
                {
                    "title": "Schneeweiss und Zuckersüss",
                    "recipes": [
                        {
                            "id": "r907016",
                            "title": "Mini-Pavlova mit Orangen",
                            "type": "VORWERK",
                            "totalTime": "6600.0",
                            "locale": "",
                            "assets": {
                                "images": {
                                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                                }
                            },
                        },
                        {
                            "id": "r907015",
                            "title": "Kokos Pralinen",
                            "type": "VORWERK",
                            "totalTime": "32400.0",
                            "locale": "",
                            "assets": {
                                "images": {
                                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
                                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
                                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
                                }
                            },
                        },
                        {
                            "id": "r907014",
                            "title": "Quarkcreme mit weisser Schoggi",
                            "type": "VORWERK",
                            "totalTime": "4200.0",
                            "locale": "",
                            "assets": {
                                "images": {
                                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485",
                                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485",
                                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485",
                                }
                            },
                        },
                        {
                            "id": "r907013",
                            "title": "Pannacotta mit Ananaskompott",
                            "type": "VORWERK",
                            "totalTime": "16800.0",
                            "locale": "",
                            "assets": {
                                "images": {
                                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb",
                                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb",
                                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb",
                                }
                            },
                        },
                        {
                            "id": "r437886",
                            "title": "Zimtsterne",
                            "type": "VORWERK",
                            "totalTime": "5400.0",
                            "locale": "",
                            "assets": {
                                "images": {
                                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d",
                                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d",
                                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d",
                                }
                            },
                        },
                        {
                            "id": "r907056",
                            "title": "Weisse Schoggimilch",
                            "type": "VORWERK",
                            "totalTime": "480.0",
                            "locale": "",
                            "assets": {
                                "images": {
                                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7",
                                    "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7",
                                    "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7",
                                }
                            },
                        },
                    ],
                }
            ],
            "version": 0,
            "author": "Vorwerk",
            "assets": {
                "images": {
                    "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/collection/ras/Assets/38cf56dff995c01c9a4ce2ce3b9f0bf8/Derivates/d8d563384bbd2652791aedfcb3200dde0e6221cb",
                    "portrait": "",
                    "landscape": "",
                }
            },
            "listType": "MANAGEDLIST",
        }
    ],
    "page": {"page": 0, "totalPages": 1, "totalElements": 1},
    "links": {"self": "/organize/de-CH/api/managed-list?page=0"},
}

COOKIDOO_TEST_RESPONSE_ADD_MANAGED_COLLECTION = {
    "message": "Kollektion wurde in Meine Rezepte gespeichert!",
    "content": {
        "id": "col500561",
        "userId": "4a74c102-3ee6-4bcd-9227-2c403900b8de",
        "collectionId": "col500561",
        "created": "2024-11-06T22:28:13.202+00:00",
        "modified": "2024-11-06T22:28:13.202+00:00",
        "title": "Schneeweiss und Zuckersüss",
        "asciiTitle": "Schneeweiss und Zuckersuss",
        "description": "Schneeweisse Delikatessen wie Pralinen und cremige Desserts sind ein wahres Fest für den Gaumen. In dieser Kollektion entdeckst du einige zuckersüsse Ideen, die mühelos mit deinem Thermomix® zubereitet werden können.",
        "chapters": [
            {
                "title": "Schneeweiss und Zuckersüss",
                "recipeIds": [
                    "r907016",
                    "r907015",
                    "r907014",
                    "r907013",
                    "r437886",
                    "r907056",
                ],
                "recipes": [
                    {
                        "id": "r907016",
                        "title": "Mini-Pavlova mit Orangen",
                        "type": "VORWERK",
                        "asciiTitle": "Mini-Pavlova mit Orangen",
                        "favoriteCount": None,
                        "portion": None,
                        "prepTime": "1200.0",
                        "totalTime": "6600.0",
                        "locale": "",
                        "assets": {
                            "images": {
                                "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                                "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                                "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006",
                            }
                        },
                        "squareRetinaImage": "https://assets.tmecosys.com/image/upload/t_web72x72@2x/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006.jpg",
                        "squareImageSrcSet": "https://assets.tmecosys.com/image/upload/t_web72x72/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006.jpg 1x, https://assets.tmecosys.com/image/upload/t_web72x72@2x/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006.jpg 2x",
                        "responsiveImageSizes": "(min-width: 1333px) 276px, (min-width: 1024px) 286px, (min-width: 768px) 220px, 140px",
                        "landscapeImage": "https://assets.tmecosys.com/image/upload/t_web276x230/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006.jpg",
                        "squareImage": "https://assets.tmecosys.com/image/upload/t_web72x72/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006.jpg",
                        "responsiveImageSrcset": "https://assets.tmecosys.com/image/upload/t_web276x230@2x/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006.jpg 552w, https://assets.tmecosys.com/image/upload/t_web378x315/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006.jpg 378w, https://assets.tmecosys.com/image/upload/t_web276x230/img/recipe/ras/Assets/1659a7ed225400e0378dfc0071fa4045/Derivates/a9a2a24272093f7aa636d4afa84d99cff10ac006.jpg 276w",
                    },
                    {
                        "id": "r907015",
                        "title": "Kokos Pralinen",
                        "type": "VORWERK",
                        "asciiTitle": "Kokos Pralinen",
                        "favoriteCount": None,
                        "portion": None,
                        "prepTime": "2700.0",
                        "totalTime": "32400.0",
                        "locale": "",
                        "assets": {
                            "images": {
                                "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
                                "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
                                "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
                            }
                        },
                        "squareRetinaImage": "https://assets.tmecosys.com/image/upload/t_web72x72@2x/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e.jpg",
                        "squareImageSrcSet": "https://assets.tmecosys.com/image/upload/t_web72x72/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e.jpg 1x, https://assets.tmecosys.com/image/upload/t_web72x72@2x/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e.jpg 2x",
                        "responsiveImageSizes": "(min-width: 1333px) 276px, (min-width: 1024px) 286px, (min-width: 768px) 220px, 140px",
                        "landscapeImage": "https://assets.tmecosys.com/image/upload/t_web276x230/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e.jpg",
                        "squareImage": "https://assets.tmecosys.com/image/upload/t_web72x72/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e.jpg",
                        "responsiveImageSrcset": "https://assets.tmecosys.com/image/upload/t_web276x230@2x/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e.jpg 552w, https://assets.tmecosys.com/image/upload/t_web378x315/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e.jpg 378w, https://assets.tmecosys.com/image/upload/t_web276x230/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e.jpg 276w",
                    },
                    {
                        "id": "r907014",
                        "title": "Quarkcreme mit weisser Schoggi",
                        "type": "VORWERK",
                        "asciiTitle": "Quarkcreme mit weisser Schoggi",
                        "favoriteCount": None,
                        "portion": None,
                        "prepTime": "600.0",
                        "totalTime": "4200.0",
                        "locale": "",
                        "assets": {
                            "images": {
                                "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485",
                                "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485",
                                "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485",
                            }
                        },
                        "squareRetinaImage": "https://assets.tmecosys.com/image/upload/t_web72x72@2x/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485.jpg",
                        "squareImageSrcSet": "https://assets.tmecosys.com/image/upload/t_web72x72/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485.jpg 1x, https://assets.tmecosys.com/image/upload/t_web72x72@2x/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485.jpg 2x",
                        "responsiveImageSizes": "(min-width: 1333px) 276px, (min-width: 1024px) 286px, (min-width: 768px) 220px, 140px",
                        "landscapeImage": "https://assets.tmecosys.com/image/upload/t_web276x230/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485.jpg",
                        "squareImage": "https://assets.tmecosys.com/image/upload/t_web72x72/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485.jpg",
                        "responsiveImageSrcset": "https://assets.tmecosys.com/image/upload/t_web276x230@2x/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485.jpg 552w, https://assets.tmecosys.com/image/upload/t_web378x315/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485.jpg 378w, https://assets.tmecosys.com/image/upload/t_web276x230/img/recipe/ras/Assets/3d143628d95418757a3880f1b0770391/Derivates/0edd5171214ff97caa2aaa0389c1f78321637485.jpg 276w",
                    },
                    {
                        "id": "r907013",
                        "title": "Pannacotta mit Ananaskompott",
                        "type": "VORWERK",
                        "asciiTitle": "Pannacotta mit Ananaskompott",
                        "favoriteCount": None,
                        "portion": None,
                        "prepTime": "2400.0",
                        "totalTime": "16800.0",
                        "locale": "",
                        "assets": {
                            "images": {
                                "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb",
                                "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb",
                                "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb",
                            }
                        },
                        "squareRetinaImage": "https://assets.tmecosys.com/image/upload/t_web72x72@2x/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb.jpg",
                        "squareImageSrcSet": "https://assets.tmecosys.com/image/upload/t_web72x72/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb.jpg 1x, https://assets.tmecosys.com/image/upload/t_web72x72@2x/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb.jpg 2x",
                        "responsiveImageSizes": "(min-width: 1333px) 276px, (min-width: 1024px) 286px, (min-width: 768px) 220px, 140px",
                        "landscapeImage": "https://assets.tmecosys.com/image/upload/t_web276x230/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb.jpg",
                        "squareImage": "https://assets.tmecosys.com/image/upload/t_web72x72/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb.jpg",
                        "responsiveImageSrcset": "https://assets.tmecosys.com/image/upload/t_web276x230@2x/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb.jpg 552w, https://assets.tmecosys.com/image/upload/t_web378x315/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb.jpg 378w, https://assets.tmecosys.com/image/upload/t_web276x230/img/recipe/ras/Assets/8C8D3D2B-32A5-4092-A578-E798CD2FB3D2/Derivates/5cd65bed-d9d9-4c82-b124-95f9204436fb.jpg 276w",
                    },
                    {
                        "id": "r437886",
                        "title": "Zimtsterne",
                        "type": "VORWERK",
                        "asciiTitle": "Zimtsterne",
                        "favoriteCount": None,
                        "portion": None,
                        "prepTime": "2700.0",
                        "totalTime": "5400.0",
                        "locale": "",
                        "assets": {
                            "images": {
                                "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d",
                                "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d",
                                "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d",
                            }
                        },
                        "squareRetinaImage": "https://assets.tmecosys.com/image/upload/t_web72x72@2x/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d.jpg",
                        "squareImageSrcSet": "https://assets.tmecosys.com/image/upload/t_web72x72/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d.jpg 1x, https://assets.tmecosys.com/image/upload/t_web72x72@2x/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d.jpg 2x",
                        "responsiveImageSizes": "(min-width: 1333px) 276px, (min-width: 1024px) 286px, (min-width: 768px) 220px, 140px",
                        "landscapeImage": "https://assets.tmecosys.com/image/upload/t_web276x230/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d.jpg",
                        "squareImage": "https://assets.tmecosys.com/image/upload/t_web72x72/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d.jpg",
                        "responsiveImageSrcset": "https://assets.tmecosys.com/image/upload/t_web276x230@2x/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d.jpg 552w, https://assets.tmecosys.com/image/upload/t_web378x315/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d.jpg 378w, https://assets.tmecosys.com/image/upload/t_web276x230/img/recipe/ras/Assets/C37A9482-EDC2-4A45-AE91-E60B4173B89D/Derivates/b33e52f8c97dfb54e77a07953855f516309fca5d.jpg 276w",
                    },
                    {
                        "id": "r907056",
                        "title": "Weisse Schoggimilch",
                        "type": "VORWERK",
                        "asciiTitle": "Weisse Schoggimilch",
                        "favoriteCount": None,
                        "portion": None,
                        "prepTime": "480.0",
                        "totalTime": "480.0",
                        "locale": "",
                        "assets": {
                            "images": {
                                "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7",
                                "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7",
                                "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7",
                            }
                        },
                        "squareRetinaImage": "https://assets.tmecosys.com/image/upload/t_web72x72@2x/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7.jpg",
                        "squareImageSrcSet": "https://assets.tmecosys.com/image/upload/t_web72x72/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7.jpg 1x, https://assets.tmecosys.com/image/upload/t_web72x72@2x/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7.jpg 2x",
                        "responsiveImageSizes": "(min-width: 1333px) 276px, (min-width: 1024px) 286px, (min-width: 768px) 220px, 140px",
                        "landscapeImage": "https://assets.tmecosys.com/image/upload/t_web276x230/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7.jpg",
                        "squareImage": "https://assets.tmecosys.com/image/upload/t_web72x72/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7.jpg",
                        "responsiveImageSrcset": "https://assets.tmecosys.com/image/upload/t_web276x230@2x/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7.jpg 552w, https://assets.tmecosys.com/image/upload/t_web378x315/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7.jpg 378w, https://assets.tmecosys.com/image/upload/t_web276x230/img/recipe/ras/Assets/4e81853553180b72aa33b758dbbfc778/Derivates/7cf0a02bced35066fc6031d3eefca7c9c6a79ad7.jpg 276w",
                    },
                ],
            }
        ],
        "recipeCount": 6,
        "version": 0,
        "author": "Vorwerk",
        "assets": {
            "images": {
                "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/collection/ras/Assets/38cf56dff995c01c9a4ce2ce3b9f0bf8/Derivates/d8d563384bbd2652791aedfcb3200dde0e6221cb",
                "portrait": "",
                "landscape": "",
            }
        },
        "listType": "MANAGEDLIST",
        "uid": "col500561",
        "listTypeName": "MANAGEDLIST",
    },
    "code": None,
}

COOKIDOO_TEST_RESPONSE_GET_CUSTOM_COLLECTIONS = {
    "customlists": [
        {
            "id": "01JC1SRPRSW0SHE0AK8GCASABX",
            "title": "Testliste1",
            "version": 4,
            "created": "2024-11-06T22:33:18.873+00:00",
            "modified": "2024-11-06T22:36:25.914+00:00",
            "chapters": [{"title": "", "recipes": []}],
            "assets": {"images": {"square": "", "portrait": "", "landscape": ""}},
            "sharedListId": None,
            "shared": False,
            "listType": "CUSTOMLIST",
            "author": "4a74c102-3ee6-4bcd-9227-2c403900b8de",
        }
    ],
    "page": {"page": 0, "totalPages": 1, "totalElements": 1},
    "links": {"self": "/organize/de-CH/api/custom-list?page=0"},
}

COOKIDOO_TEST_RESPONSE_ADD_CUSTOM_COLLECTION = {
    "message": "Rezeptliste wurde erfolgreich erstellt!",
    "content": {
        "id": "01JC1SRPRSW0SHE0AK8GCASABX",
        "title": "Testliste",
        "version": 1,
        "created": "2024-11-06T22:33:18.873+00:00",
        "modified": "2024-11-06T22:33:18.873+00:00",
        "chapters": [{"title": "", "recipes": []}],
        "assets": {"images": {"square": "", "portrait": "", "landscape": ""}},
        "sharedListId": None,
        "author": "4a74c102-3ee6-4bcd-9227-2c403900b8de",
        "listType": "CUSTOMLIST",
        "shared": False,
    },
    "code": None,
}

COOKIDOO_TEST_RESPONSE_ADD_RECIPES_TO_CUSTOM_COLLECTION = {
    "message": "Rezeptliste wurde erfolgreich aktualisiert!",
    "content": {
        "id": "01JC1SRPRSW0SHE0AK8GCASABX",
        "title": "Testliste1",
        "version": 3,
        "created": "2024-11-06T22:33:18.873+00:00",
        "modified": "2024-11-06T22:35:24.467+00:00",
        "chapters": [
            {
                "title": "",
                "recipes": [
                    {
                        "id": "r907015",
                        "title": "Kokos Pralinen",
                        "type": "VORWERK",
                        "totalTime": "32400.0",
                        "locale": "",
                        "assets": {
                            "images": {
                                "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
                                "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
                                "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
                            }
                        },
                    }
                ],
            }
        ],
        "assets": {
            "images": {
                "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
                "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
                "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/94e7404b092f239d09803fdbd4ddbac1/Derivates/ccee0755073a78a95b79d96ba26fd5e3e89c137e",
            }
        },
        "sharedListId": None,
        "shared": False,
        "listType": "CUSTOMLIST",
        "author": "4a74c102-3ee6-4bcd-9227-2c403900b8de",
    },
    "code": None,
}


COOKIDOO_TEST_RESPONSE_REMOVE_RECIPE_FROM_CUSTOM_COLLECTION = {
    "message": "Rezept wurde aus dieser Rezeptliste entfernt!",
    "content": {
        "id": "01JC1SRPRSW0SHE0AK8GCASABX",
        "title": "Testliste1",
        "version": 4,
        "created": "2024-11-06T22:33:18.873+00:00",
        "modified": "2024-11-06T22:36:25.914+00:00",
        "chapters": [{"title": "", "recipes": []}],
        "assets": {"images": {"square": "", "portrait": "", "landscape": ""}},
        "sharedListId": None,
        "author": "4a74c102-3ee6-4bcd-9227-2c403900b8de",
        "listType": "CUSTOMLIST",
        "shared": False,
    },
    "code": None,
}

COOKIDOO_TEST_RESPONSE_CALENDAR_WEEK = {
    "myDays": [
        {
            "id": "2025-03-04",
            "title": "2025-03-04",
            "dayKey": "2025-03-04",
            "created": "2025-03-04T18:56:05.424+00:00",
            "modified": "2025-03-04T18:56:05.424+00:00",
            "recipes": [
                {
                    "id": "r214846",
                    "title": "Waffles",
                    "totalTime": "1500.0",
                    "locale": "gb",
                    "assets": {
                        "images": {
                            "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c6ea15c4-52ab-4119-b886-a7fb1d052f45/Derivates/b18fcddc-3b31-4ae9-9cd1-5a81751d91b3",
                            "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c6ea15c4-52ab-4119-b886-a7fb1d052f45/Derivates/b18fcddc-3b31-4ae9-9cd1-5a81751d91b3",
                            "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c6ea15c4-52ab-4119-b886-a7fb1d052f45/Derivates/b18fcddc-3b31-4ae9-9cd1-5a81751d91b3",
                        }
                    },
                }
            ],
            "customerRecipeIds": [],
            "author": "4a74c102-3ee6-4bcd-9227-2c403900b8de",
        },
        {
            "id": "2025-03-05",
            "title": "2025-03-05",
            "dayKey": "2025-03-05",
            "created": "2025-03-04T19:00:02.773+00:00",
            "modified": "2025-03-04T19:00:02.773+00:00",
            "recipes": [
                {
                    "id": "r338888",
                    "title": "Moroccan Mint Tea",
                    "totalTime": "1500.0",
                    "locale": "gb",
                    "assets": {
                        "images": {
                            "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/47d318332476db821ab3d1c5414f772e/Derivates/8d7d71b9c549cb55b11cc965a6b47be108ab44e5",
                            "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/47d318332476db821ab3d1c5414f772e/Derivates/8d7d71b9c549cb55b11cc965a6b47be108ab44e5",
                            "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/47d318332476db821ab3d1c5414f772e/Derivates/8d7d71b9c549cb55b11cc965a6b47be108ab44e5",
                        }
                    },
                }
            ],
            "customerRecipeIds": [],
            "author": "4a74c102-3ee6-4bcd-9227-2c403900b8de",
        },
    ]
}


COOKIDOO_TEST_RESPONSE_ADD_RECIPES_TO_CALENDAR = {
    "message": "Recipe Waffles planned for 4 Mar 2025!",
    "content": {
        "id": "2025-03-04",
        "title": "2025-03-04",
        "dayKey": "2025-03-04",
        "created": "2025-03-04T18:56:05.424+00:00",
        "modified": "2025-03-04T18:56:05.424+00:00",
        "recipes": [
            {
                "id": "r214846",
                "title": "Waffles",
                "totalTime": "1500.0",
                "locale": "gb",
                "assets": {
                    "images": {
                        "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c6ea15c4-52ab-4119-b886-a7fb1d052f45/Derivates/b18fcddc-3b31-4ae9-9cd1-5a81751d91b3",
                        "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c6ea15c4-52ab-4119-b886-a7fb1d052f45/Derivates/b18fcddc-3b31-4ae9-9cd1-5a81751d91b3",
                        "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c6ea15c4-52ab-4119-b886-a7fb1d052f45/Derivates/b18fcddc-3b31-4ae9-9cd1-5a81751d91b3",
                    }
                },
            }
        ],
        "customerRecipeIds": [],
        "author": "4a74c102-3ee6-4bcd-9227-2c403900b8de",
    },
    "code": None,
}


COOKIDOO_TEST_RESPONSE_REMOVE_RECIPE_FROM_CALENDAR = {
    "message": "Recipe Waffles was removed!",
    "content": {
        "id": "2025-03-04",
        "title": "2025-03-04",
        "dayKey": "2025-03-04",
        "created": "2025-03-04T18:56:05.424+00:00",
        "modified": "2025-03-04T18:56:05.424+00:00",
        "recipes": [
            {
                "id": "r214846",
                "title": "Waffles",
                "totalTime": "1500.0",
                "locale": "gb",
                "assets": {
                    "images": {
                        "square": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c6ea15c4-52ab-4119-b886-a7fb1d052f45/Derivates/b18fcddc-3b31-4ae9-9cd1-5a81751d91b3",
                        "portrait": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c6ea15c4-52ab-4119-b886-a7fb1d052f45/Derivates/b18fcddc-3b31-4ae9-9cd1-5a81751d91b3",
                        "landscape": "https://assets.tmecosys.com/image/upload/{transformation}/img/recipe/ras/Assets/c6ea15c4-52ab-4119-b886-a7fb1d052f45/Derivates/b18fcddc-3b31-4ae9-9cd1-5a81751d91b3",
                    }
                },
            }
        ],
        "customerRecipeIds": [],
        "author": "4a74c102-3ee6-4bcd-9227-2c403900b8de",
    },
    "code": None,
}

COOKIDOO_TEST_RESPONSE_ADD_CUSTOM_RECIPES_TO_CALENDAR = {
    "message": "Recipe planned for Aug 11, 2025!",
    "content": {
        "id": "2025-08-11",
        "title": "11.08.2025",
        "dayKey": "2025-08-11",
        "created": "2025-08-11T15:08:14.768+00:00",
        "modified": "2025-08-11T15:08:14.768+00:00",
        "recipes": [],
        "customerRecipeIds": ["01K2CTJ9Y1BABRG5MXK44CFZS4"],
        "author": "2d336b56-6c23-49bb-9543-5bdf0344eedf",
    },
    "code": None,
}

COOKIDOO_TEST_RESPONSE_REMOVE_CUSTOM_RECIPE_FROM_CALENDAR = {
    "message": "Recipe was removed",
    "content": {
        "id": "2025-08-11",
        "title": "11.08.2025",
        "dayKey": "2025-08-11",
        "created": "2025-08-11T15:08:14.768+00:00",
        "modified": "2025-08-11T15:08:14.768+00:00",
        "recipes": [],
        "customerRecipeIds": ["01K2CTJ9Y1BABRG5MXK44CFZS4"],
        "author": "2d336b56-6c23-49bb-9543-5bdf0344eedf",
    },
    "code": None,
}
