import pytest
from pipeline.normalizers.address import normalize_address
from pipeline.normalizers.phone import normalize_phone
from pipeline.normalizers.name import normalize_name


# --- address ---
def test_normalize_address_basic():
    result = normalize_address("250 health park dr, fort myers, fl 33908")
    assert "250" in result
    assert "FORT MYERS" in result
    assert "FL" in result
    assert "33908" in result

def test_normalize_address_already_upper():
    result = normalize_address("250 HEALTH PARK DR, FORT MYERS, FL 33908")
    assert "250 HEALTH PARK DR" in result

def test_normalize_address_empty():
    assert normalize_address("") == ""

def test_normalize_address_extra_whitespace():
    result = normalize_address("  100  Main  St ,  Naples , FL  34102  ")
    assert "100" in result
    assert "NAPLES" in result


# --- phone ---
def test_normalize_phone_dashes():
    assert normalize_phone("239-555-1234") == "+12395551234"

def test_normalize_phone_dots():
    assert normalize_phone("239.555.1234") == "+12395551234"

def test_normalize_phone_parens():
    assert normalize_phone("(239) 555-1234") == "+12395551234"

def test_normalize_phone_already_e164():
    assert normalize_phone("+12395551234") == "+12395551234"

def test_normalize_phone_invalid():
    assert normalize_phone("not-a-phone") == ""

def test_normalize_phone_empty():
    assert normalize_phone("") == ""


# --- name ---
def test_normalize_name_basic():
    assert normalize_name("JOHN SMITH MD") == "John Smith MD"

def test_normalize_name_with_comma_credential():
    assert normalize_name("Smith, John, MD") == "John Smith MD"

def test_normalize_name_do():
    assert normalize_name("MARIA GARCIA DO") == "Maria Garcia DO"

def test_normalize_name_empty():
    assert normalize_name("") == ""
