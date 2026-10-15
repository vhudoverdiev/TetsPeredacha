from pathlib import Path
p=Path('app/services/task_service.py');s=p.read_text();s=s.replace('PREMISE_SEARCH_MODES = {','PREMISE_SEARCH_MODES = {\n    "premise_range",')
s=s.replace('        \\d+-\\d+-\\d+\n        |','        \\d+-\\d+-\\d+\n        |\n        \\d+\\s*[-–—]\\s*\\d+(?![\\d/-])\n        |',1)
s=s.replace('    normalized = normalize_text(text).replace("ё", "е")','''    range_match = re.fullmatch(r"(\\d{1,9})\\s*[-–—]\\s*(\\d{1,9})", text)
    if range_match:
        low, high = sorted(map(int, range_match.groups()))
        return "premise_range", f"{low}|{high}"
    normalized = normalize_text(text).replace("ё", "е")''',1)
s=s.replace('    if mode == "commercial_pair":\n        number, _, building = str(value).partition("|")','    if mode == "premise_range":\n        return str(value).replace("|", "-")\n    if mode == "commercial_pair":\n        number, _, building = str(value).partition("|")',1)
needle='def premise_selector_clause(selector: tuple[str, str]):\n    mode, value = selector'
s=s.replace(needle,needle+'''
    if mode == "premise_range":
        low, high = map(int, value.split("|"))
        number = func.trim(Apartment.apartment_number)
        number = case(
            (Apartment.premise_type == "storeroom", func.replace(func.replace(number, "КЛ", ""), "кл", "")),
            (Apartment.premise_type == "parking", func.replace(func.replace(number, "П", ""), "п", "")),
            else_=number,
        )
        number = func.trim(number)
        remainder = number
        for digit in "0123456789":
            remainder = func.replace(remainder, digit, "")
        return and_(number != "", remainder == "", cast(number, Integer).between(low, high))
''')
needle='    value = str(value).strip()\n    if mode == "commercial_pair":'
s=s.replace(needle,'''    value = str(value).strip()
    if mode == "premise_range":
        low, high = map(int, value.split("|"))
        number = str(apartment.apartment_number or "").strip()
        if apartment.premise_type == "storeroom":
            number = re.sub(r"^кл", "", number, flags=re.I).strip()
        elif apartment.premise_type == "parking":
            number = re.sub(r"^п", "", number, flags=re.I).strip()
        return bool(re.fullmatch(r"[0-9]+", number)) and low <= int(number) <= high
    if mode == "commercial_pair":''',1)
p.write_text(s)
