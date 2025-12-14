import re
from typing import Pattern, List
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

def validate_text(text: str) -> bool:
    if len(text) > 0:
        return True
    else:
        return False
    
def validate_frescures(pattern: Pattern[str], text: str) -> bool:
    valid_chars = {"A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"}
    list_text = text.split()
    valid = not valid_chars.isdisjoint(list_text)
    valid_format = re.fullmatch(pattern, text)

    if valid or len(text) != 4 or valid_format is None or not text.isalnum():
        return False
    else:    
        return True
           
def validate_sku(text: str) -> bool:
    text = text.strip()
    if len(text) != 7 or not text.isdecimal():
        return False
    else:
        return True

def frescure_to_date(frescure: str) -> str:
    """
    Convierte un STR validado A000 en fecha:
        - letra A-L -> mes 1-12
        - posiciones [1:3] -> día (01-31)
        - último dígito -> año dentro de la década (por ejemplo '5' -> 2025)
    Devuelve la fecha en formato 'DD/MM/YYYY'.
    """
    frescure_list: List[str] = []
    for char in frescure:
        if char.isalpha():
            frescure_list.append(char)
        if char.isdigit():
            frescure_list.append(char)
        else:
            continue

    dia1 = frescure_list[1]
    dia2 = frescure_list[2]
    dia = int(dia1 + dia2)
    mes = ord(frescure_list[0]) - ord("A") + 1
    last_digit = int(frescure_list[3])
    ref =  datetime.now().year
    decade_start = (ref // 10) * 10
    year = decade_start + last_digit

    if dia >= 32:
        print("Mal dia")
        return ""
    elif mes >= 13:
        print("Mal mes")
        return ""
    elif 2024 >= ref:
        print("Mal año")
        return ""
    else:    
        dt = datetime(year, mes, dia)
    
    return dt.strftime("%d/%m/%Y")
    