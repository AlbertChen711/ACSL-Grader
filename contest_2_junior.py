def analyze_license_plate(plate, day):
    # 1. Base format validation
    if len(plate) < 4 or not plate[0].isalpha() or not plate[0].isupper() or plate[1] != '.':
        return "invalid"
    
    after_dot = plate[2:]
    
    # Determine plate type by length of characters after the dot
    if len(after_dot) == 6:
        plate_color = "green"
    elif len(after_dot) == 5:
        plate_color = "blue"
    else:
        return "invalid"
        
    # Ensure all characters after the dot are uppercase alphanumeric
    if not after_dot.isalnum() or not after_dot.isupper():
        # Note: .isalnum() is True for alphanumeric, but we must ensure no lowercase letters
        # Since we already checked .isupper(), any alphabetic char is uppercase. Digits pass .isupper() as False, 
        # so we check if it's equal to its uppercase version.
        if after_dot != after_dot.upper():
            return "invalid"

    # 2. Check for "Fortunate"
    is_fortunate = False
    
    # Check for 2 consecutive adjacent letters after the dot
    for i in range(len(after_dot) - 1):
        if after_dot[i].isalpha() and after_dot[i+1].isalpha():
            is_fortunate = True
            break
            
    # Check for 3 consecutive adjacent digits in strictly ascending/descending order
    if not is_fortunate:
        for i in range(len(after_dot) - 2):
            ch1, ch2, ch3 = after_dot[i], after_dot[i+1], after_dot[i+2]
            if ch1.isdigit() and ch2.isdigit() and ch3.isdigit():
                d1, d2, d3 = int(ch1), int(ch2), int(ch3)
                # Strictly ascending (e.g., 1, 2, 3) or strictly descending (e.g., 5, 4, 3)
                if (d2 == d1 + 1 and d3 == d2 + 1) or (d2 == d1 - 1 and d3 == d2 - 1):
                    is_fortunate = True
                    break

    # 3. Check for "Lucky" (adjacent repeated 6s, 8s, or 9s anywhere in the plate)
    is_lucky = "66" in plate or "88" in plate or "99" in plate

    # 4. Check for "Restricted" (Only applies to blue plates)
    is_restricted = False
    if plate_color == "blue":
        last_char = after_dot[-1]
        if last_char.isdigit():
            last_digit = int(last_char)
            if last_digit % 2 != 0:  # Odd digit
                restricted_days = {"Sunday", "Tuesday", "Thursday", "Saturday"}
                if day in restricted_days:
                    is_restricted = True
        else:
            # Blue plate rules state the last character must be a digit
            return "invalid"

    # 5. Output based on priority order
    if is_fortunate:
        return "fortunate"
    elif is_lucky:
        return "lucky"
    elif is_restricted:
        return "restricted"
    else:
        return plate_color

# --- Test Cases ---
first_input = input().strip()
second_input = input().strip()
print(analyze_license_plate(first_input, second_input)) 