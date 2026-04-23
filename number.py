def validate_number(phone_number):
    """
    Basic phone number validation logic.
    """
    # Remove any non-digit characters
    clean_number = ''.join(filter(str.isdigit, str(phone_number)))
    
    if len(clean_number) >= 10:
        return True, clean_number
    return False, None

def format_currency(amount):
    """
    Formats a number as currency.
    """
    return f"${amount:,.2f}"

if __name__ == "__main__":
    num = "123-456-7890"
    is_valid, cleaned = validate_number(num)
    print(f"Number: {num} | Valid: {is_valid} | Cleaned: {cleaned}")
