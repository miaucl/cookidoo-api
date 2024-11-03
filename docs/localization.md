# Available localizations

To extract the available localizations, we use the web application and extract the data from the html.

Open [<https://cookidoo.ch/foundation/en>](https://cookidoo.ch/foundation/en) and entry following command `navigator.clipboard.writeText(document.querySelector(".core-footer__language-select ul.core-dropdown-list").outerHTML)` into the console to extract the desired html, which will be copied to the clipboard. Should you run into permission issues, just use `console.log(document.querySelector(".core-footer__language-select ul.core-dropdown-list").outerHTML)` and copy it from the console output manually.

Paste it into the [`./raw/localization-extract.html`](https://github.com/miaucl/cookidoo/blob/master/raw/localization-extract.html) file.

Run following snippet [`../scripts/process-localization-extract.py`](https://github.com/miaucl/cookidoo/blob/master/scripts/process-localization-extract.py) or use the VSCode task, to extract the data and update the [`../cookidoo_api/localization.json`](https://github.com/miaucl/cookidoo/blob/master/cookidoo_api/localization.json).
