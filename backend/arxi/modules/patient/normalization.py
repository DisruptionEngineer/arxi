"""Name normalization for patient matching."""

NICKNAMES = {
    "bob": "robert", "bill": "william", "jim": "james",
    "jimmy": "james", "mike": "michael", "dick": "richard",
    "rick": "richard", "tom": "thomas", "joe": "joseph",
    "dan": "daniel", "dave": "david", "steve": "steven",
    "pat": "patrick", "liz": "elizabeth", "beth": "elizabeth",
    "kate": "katherine", "kathy": "katherine", "jen": "jennifer",
    "chris": "christopher", "matt": "matthew", "tony": "anthony",
    "ed": "edward", "ted": "edward", "sam": "samuel",
    "alex": "alexander", "nick": "nicholas", "ben": "benjamin",
    "will": "william", "rob": "robert", "charlie": "charles",
}

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v", "jr.", "sr."}


def normalize_name(name: str) -> str:
    """Normalize a name: lowercase, strip whitespace, remove suffixes, map nicknames."""
    parts = name.lower().strip().split()
    parts = [p for p in parts if p not in SUFFIXES]
    # Apply nickname mapping: if single word, map the whole thing;
    # if multi-word, map the first part (first name) only.
    if len(parts) == 1:
        return NICKNAMES.get(parts[0], parts[0])
    elif len(parts) > 1:
        parts[0] = NICKNAMES.get(parts[0], parts[0])
    return " ".join(parts)
