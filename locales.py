from functools import partial, wraps
from pathlib import Path

import yaml

from db import Config

default_language = "en-US"


def load_locales() -> dict[str, dict[str, str]]:
    ldict = {}
    for lang_file in Path("locales").glob("*.yml"):
        with lang_file.open(encoding="utf-8") as f:
            ldict[lang_file.stem] = yaml.safe_load(f)

    return ldict


langdict = load_locales()


def use_lang():
    def decorator(func):
        @wraps(func)
        async def wrapper(client, message):
            lang = await Config.get_or_none(id="lang")
            if not lang:
                lang = default_language
                await Config.create(id="lang", value=default_language)
            else:
                lang = lang.value

            lfunc = partial(get_locale_string, lang)
            return await func(client, message, lfunc)

        return wrapper

    return decorator


def get_locale_string(language: str, key: str) -> str:
    res: str = langdict[language].get(key) or langdict[default_language].get(key) or key
    return res
