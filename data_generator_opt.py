import csv
import random
import string
import calendar
from datetime import datetime, timedelta
from collections import defaultdict
from pathlib import Path
from random import randint, sample

# ==========================================
# GLOBALS
# ==========================================

NAME = "raw_data.csv"
BASE_DIR = Path(__file__).resolve().parent
OUT_CSV_PATH = BASE_DIR / NAME

STARTING_NUMBER = 101
STATES = ["GA", "CA", "TX", "FL", "IL", "NJ", "AZ", "OH", "NC", "MI", "UT", "TN", "MO", "WI"]

NAMES = [
    "juan", "maria", "carlos", "luis", "ana", "diego", "laura", "pedro", 
    "sofia", "jose", "elena", "miguel", "lucia", "jorge", "claudia", "andres",
    "alejandro", "valentina", "mateo", "camila", "santiago", "isabella", "lucas", "mariana",
    "nicolas", "gabriela", "sebastian", "daniela", "david", "victoria", "daniel", "martina",
    "javier", "paula", "manuel", "sara", "fernando", "andrea", "ricardo", "natalia"
]

LAST_NAMES = [
    "perez", "gomez", "ruiz", "fernandez", "martinez", "tovar", "nunez", "infante", 
    "lopez", "diaz", "rodriguez", "sanchez", "alvarez", "torres", "garcia", "castro",
    "romero", "herrera", "medina", "silva", "vargas", "mendoza", "rios", "morales",
    "gutierrez", "suarez", "ortiz", "ramos", "chavez", "flores", "gonzalez", "benitez",
    "jimenez", "marin", "aguilar", "acosta", "rojas", "ledesma", "miranda", "valenzuela"
]

AGENT_NAMES = ["Mario Gomez", "Anselmo Urrutia", "Iris Solorzano", "Azul Perez", "Nancy Ramirez", "Arturo Rios", "Miguel Ledezma", "Marisol Parra"]

CARRIERS_LIST= ['Molino', 'Azure', 'Belgrano', 'Wellhub', 'Rosebud', 'Americano Health', 'Gecko', 'Panorama', 'First Aid']

PREMIUM_RANGES = {
    ("Bronze", 1): (0, 25), ("Bronze", 2): (25, 75), ("Bronze", 3): (75, 125), ("Bronze", 4): (125, 175),
    ("Silver", 1): (50, 100), ("Silver", 2): (100, 200), ("Silver", 3): (200, 300), ("Silver", 4): (300, 400),
    ("Gold", 1): (150, 200), ("Gold", 2): (200, 350), ("Gold", 3): (350, 500), ("Gold", 4): (500, 650)
}

counter = defaultdict(lambda: STARTING_NUMBER) 

# ==========================================
# GENERATION AND CORRUPTION
# ==========================================
def corrupt_id(clean_id: str) -> str:
    error_type = random.choice(["missing_separator", "low_caps", "extra_space", "duplicate_digit"])
    code, number = clean_id.split("-")

    if error_type == 'missing_separator': 
        return f'{code}{number}'
    elif error_type == 'low_caps': 
        return f'{code.lower()}-{number}'
    elif error_type == 'extra_space': 
        return f'{code}- {number}' if random.random() < 0.5 else f'{code} -{number}'
    elif error_type == 'duplicate_digit':
        return f'{code}-{number}{number}'

def generate_id(state: str, number: int) -> str:
    clean_id = f'{state}-{number}'
    return corrupt_id(clean_id) if random.random() < 0.10 else clean_id

def corrupt_name(full_name):
    name, l_name = full_name.split(" ")
    error_type = random.choice(['upper', 'blank', 'comma', 'dash'])
    if error_type == 'upper': 
        return f'{name} {l_name}'.upper()
    elif error_type == 'blank':
        blank = " " * randint(1,5)
        if random.random() < 0.50:
            return f'{blank}{name} {l_name}'
        else:
            return f'{name} {l_name}{blank}'
    elif error_type == 'comma':
        return f'{l_name}, {name}'
    elif error_type == 'dash':
        return f'{name}-{l_name}'

def generate_name() -> str:
    full_name = f'{random.choice(NAMES)} {random.choice(LAST_NAMES)}'
    return corrupt_name(full_name) if random.random() < 0.20 else full_name

def generate_agent_name() -> str:
    clean_name = random.choice(AGENT_NAMES)
    if random.random() < 0.40:
        name, l_name = clean_name.split(' ')
        return f'{l_name}, {name}'
    return clean_name

def corrupt_status(status: str) -> str:
    error_type = random.choices(['Upper', 'Lower', 'Sliced','Spaced'], weights=[30,30,20,20])[0]

    if error_type == 'Upper':
        return status.upper()
    elif error_type == 'Lower':
        return status.lower()
    elif error_type == 'Sliced':
        return status[:randint(3,5)]
    elif error_type == 'Spaced':
        spaces = " " * randint(1,5)
        return f'{spaces}{status}' if random.random() < 0.50 else f'{status}{spaces}'
    return status

def generate_status() -> str:
    weights = [random.randint(50, 80),random.randint(10, 30), random.randint(5, 25)]
    status = random.choices(["Active", "Pipeline", "Terminated"], weights=weights, k=1)[0]
    return corrupt_status(status) if random.random() < 0.50 else status

def corrupt_premium(premium: float) -> str:
    error_type = random.choice(['$$', 'extra_decimal', 'usd', 'empty', 'negative', 'spacing', 'comma', 'surreal_value',])
    premium_str = f'{premium:.2f}'

    if error_type == '$$':
        return f'$$ {premium_str}'
    elif error_type == 'extra_decimal':
        return f'{premium_str}{randint(0,9)}'
    elif error_type == 'usd':
        return f'{premium_str} USD'
    elif error_type == 'empty':
        return ''
    elif error_type == 'negative':
        return f'-{premium_str}'
    elif error_type == 'spacing':
        spaces = ' ' * randint(1, 5)
        return f'{premium_str}{spaces}' if random.random() < 0.50 else f'{spaces}{premium_str}'
    elif error_type == 'comma':
        return premium_str.replace('.', ',')
    elif error_type == 'surreal_value':
        return f'{randint(15000, 99000)}.{randint(0, 99):02d}'
    return premium_str

def generate_premium(metal: str, members: str | int) -> str | float:
    text_to_number = {'one': 1, 'two': 2, 'three': 3, 'four': 4}
    members_num = text_to_number.get(members, members)

    if (metal, members_num) not in PREMIUM_RANGES:
        premium = round(random.uniform(0,500), 2)
    else:
        low, high = PREMIUM_RANGES[(metal, members_num)]
        premium = round(random.uniform(low, high), 2)
    return premium

def generate_members() -> str | int:
    members = randint(1,4)
    if random.random() < 0.40:
        error_type = random.choice(['empty', 'out_of_range', 'text'])
        if error_type == 'empty':
            return ''
        if error_type == 'out_of_range':
            return randint(10,25)
        if error_type == 'text':
            return {1: 'one', 2: 'two', 3: 'three', 4: 'four'}[members]
    return members

def corrupt_date(date_obj: datetime) -> str:
    error_type =  random.choice(['invalid','empty','year_first','wrong_separator','extra_character', 'space'])
    month, day, year = date_obj.strftime("%m-%d-%Y").split('-')

    if error_type == 'empty':
        return f''
    elif error_type == 'year_first':
        return f'{year}-{month}-{day}'
    elif error_type == 'wrong_separator':
        return f'{month}/{day}/{year}' if random.random() < 0.50 else f'{month}.{day}.{year}'
    elif error_type == 'extra_character':
        extra_letter = random.choice(string.ascii_letters + "!@#$%^&*()-_=+")
        return f'{month}-{day}-{year}{extra_letter}'
    elif error_type == 'invalid':
        return f'{month}-{day}-{randint(1900,2000)}'
    elif error_type == 'space':
        space = ' ' * randint(2,5)
        return f'{month}-{day}-{year}{space}' if random.random() < 0.50 else f'{space}{month}-{day}-{year}'
    return date_obj.strftime("%m-%d-%Y")

def generate_cancellation_date(start_date: datetime) -> datetime:
    finish = datetime(2026, 6, 30)
    last_days = [datetime(start_date.year, month, calendar.monthrange(start_date.year, month)[1]) for month in range(start_date.month, finish.month + 1)]
    valid_term_dates = [d for d in last_days if d > start_date]
    final_date = random.choice(valid_term_dates)
    return final_date

def generate_record():
    state = random.choice(STATES)
    number = counter[state]
    counter[state] += 1

    policy_id = generate_id(state, number)
    full_name = generate_name()
    agent_name = generate_agent_name()
    status = generate_status()
    members_covered = generate_members()
    metal_tier = random.choice(["Gold", "Silver", "Bronze"])
    pre_premium = generate_premium(metal_tier, members_covered)
    premium = corrupt_premium(pre_premium) if random.random() < 0.20 else pre_premium
    carrier = random.choice(CARRIERS_LIST)
    purch_date =  datetime(2026, randint(1,6), 1)
    purch_date_str = purch_date.strftime("%m-%d-%Y")

    if "term" in status.lower():
        cancel_date = generate_cancellation_date(purch_date)
        cancel_date_str = corrupt_date(cancel_date) if random.random() < 0.20 else cancel_date.strftime("%m-%d-%Y")
    else:
        cancel_date_str = ""

    if "pipe" in status.lower():
        deadline = purch_date + timedelta(days=random.choice([75, 95]))
        deadline_str = corrupt_date(deadline) if random.random() < 0.15 else deadline.strftime("%m-%d-%Y")
        pipeline_reason = random.choice(["Missing Documents", "Missing Payment"])
    else:
        deadline_str = ""
        pipeline_reason = ""

    return [policy_id, full_name, state, agent_name, status, members_covered, metal_tier, premium, carrier, purch_date_str, cancel_date_str, deadline_str, pipeline_reason]

def corrupt_duplicate(record:list) -> list:
    duplicate = record.copy()
    error_type = random.choice(["exact", "missing fields"])

    if error_type == "exact":
        return duplicate
    elif error_type == "missing_fields":
        numbers = ['1, 4, 5, 6, 8']
        indexes = random.sample(numbers, 2)
        duplicate[indexes[0]] = ""
        duplicate[indexes[1]] = ""

    return duplicate

# ==========================================
# MAIN
# ==========================================

POLICIES_TO_BE_GEN = 1000

def main():
    headers = ["policy_id", "client_name", "state", "agent", "status", "members_covered", "metal_tier", "premium", "carrier", "purchase_date", "cancel_date", "pipeline_deadline", "pipeline_reason"]
    records = []

    for _ in range(POLICIES_TO_BE_GEN):
        record = generate_record()
        records.append(record)
        if random.random() < 0.07:
            records.append(corrupt_duplicate(record))

    random.shuffle(records)
    OUT_CSV_PATH.parent.mkdir(parents=True, exist_ok=True)

    with open(OUT_CSV_PATH, mode="w", newline ="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(records)

    print(f'✅✅✅\nRaw data generated\n{"*" * 25}')

if __name__ == "__main__":
    main()