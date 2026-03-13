from arxi.modules.patient.normalization import normalize_name


async def test_lowercase_and_strip():
    assert normalize_name("  John  ") == "john"


async def test_suffix_removal_jr():
    assert normalize_name("John Smith Jr") == "john smith"


async def test_suffix_removal_sr():
    assert normalize_name("John Smith Sr.") == "john smith"


async def test_suffix_removal_roman_numerals():
    assert normalize_name("John Smith III") == "john smith"
    assert normalize_name("John Smith II") == "john smith"
    assert normalize_name("John Smith IV") == "john smith"


async def test_nickname_bob_to_robert():
    assert normalize_name("Bob") == "robert"


async def test_nickname_bill_to_william():
    assert normalize_name("Bill") == "william"


async def test_nickname_jim_to_james():
    assert normalize_name("Jim") == "james"


async def test_nickname_liz_to_elizabeth():
    assert normalize_name("Liz") == "elizabeth"


async def test_nickname_kate_to_katherine():
    assert normalize_name("Kate") == "katherine"


async def test_no_nickname_match():
    assert normalize_name("Derek") == "derek"


async def test_combined_suffix_and_nickname():
    assert normalize_name("Bob Smith Jr.") == "robert smith"


async def test_multi_word_name_no_suffix():
    assert normalize_name("Mary Jane Watson") == "mary jane watson"
