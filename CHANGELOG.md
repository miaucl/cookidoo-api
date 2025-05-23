# CHANGELOG

## DEPRECATED

 This changelog is no longer maintained and will not be updated in future releases. Please refer to the [release notes](https://github.com/miaucl/cookidoo-api/releases/latest) on GitHub for the latest changes.

## 0.12.2

- Fix .co.uk countries which do share a common domain

## 0.12.1

- Add support for recipes which feature ranges for quantity in addition to fixed values

## 0.12.0

- Use sub from jwt as username no longer available at login stage

## 0.11.2

- Fix exotic countries which do share a common domain

## 0.11.1

- Extend smoke tests to multiple accounts with different countries

## 0.11.0

- Align token endpoint with new way of auth for cookidoo app

## 0.10.0

- Use async lib aiofiles to read files from file system

## 0.9.1

- Remove unnecessary python-dotenv from prod requirements

## 0.9.0

- Migrate from TypedDict to dataclass

## 0.8.0

- add collections for managed and custom lists
- add and remove recipes to custom lists
- add calendar/my week with planned recipes

## 0.7.0

- add a method to get the recipe details
- rename the ingredients to ingredient_items to have a logical group of items for the shopping list
- pure ingredients are only a part of the recipe now

## 0.6.0

- add a method to get the recipes on a shopping list

## 0.5.0

- add localization getter for the Cookidoo instance

## 0.4.0

- switch from web automation to proper API (based on Android App)

## 0.3.0

- add check method to quickly verify browser functionality

## 0.2.0

- add method to add items when in free account
- auto-close feedback modal when in free account

## 0.1.1

- fix build

## 0.1.0

Initial commit.
