import secrets
import string
import random

def generate_password(need_number: bool = True, 
                      need_lowercase: bool = True, 
                      need_uppercase: bool = True, 
                      need_special_char: bool = True, 
                      custom_char: str = "", 
                      length: int = 12) -> str:
    pool_map = []
    if need_number:       pool_map.append(string.digits)
    if need_lowercase:    pool_map.append(string.ascii_lowercase)
    if need_uppercase:    pool_map.append(string.ascii_uppercase)
    if need_special_char: pool_map.append(string.punctuation)
    if not pool_map and not custom_char:
        raise ValueError("At least one character type must be selected")
    if length < len(pool_map):
        raise ValueError(f"Length {length} is too short for {len(pool_map)} required character types")
    password_chars = []
    for chars in pool_map:
        password_chars.append(secrets.choice(chars))
    full_alphabet = "".join(pool_map) + custom_char
    full_alphabet_set = sorted(list(set(full_alphabet))) 
    remaining_length = length - len(password_chars)
    for _ in range(remaining_length):
        password_chars.append(secrets.choice(full_alphabet_set))
    random.SystemRandom().shuffle(password_chars)
    return "".join(password_chars)

if __name__ == "__main__":
    print(f"常规: {generate_password()}")
    print(f"短密码: {generate_password(length=4)}") 
    print(f"自定义: {generate_password(need_number=False, need_lowercase=False, need_uppercase=False, need_special_char=False, custom_char='abc', length=5)}")
