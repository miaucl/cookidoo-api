# Breaking changes

This document tracks the breaking changes observed in the Cookidoo API.

## 20250811

- `serving_size` is now a _int_ instead of a _str_ and lacks therefore the unit information which was backed in prior.

## 20250624

- Collections (custom and managed) now require the correct `ACCEPT` header field.
