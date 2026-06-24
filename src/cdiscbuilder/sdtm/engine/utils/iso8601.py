import pandas as pd

def parse_iso8601(date_str):
    if pd.isna(date_str) or not str(date_str).strip():
        return None
        
    s = str(date_str).strip().upper()
    
    # Split into Date and Time
    time_part = ""
    if "T" in s:
        parts = s.split("T", 1)
        s = parts[0]
        time_part = parts[1]
    elif " " in s:
        parts = s.split(" ", 1)
        s = parts[0]
        time_part = parts[1]
        
    # Standardize separators to dashes
    s = s.replace("/", "-").replace(".", "-")
    parts = s.split("-")
    
    # Clean parts: map unknowns to None
    unknowns = {"UN", "UNK", "U", "ND", "NA", "UKN", "UNKNOWN"}
    clean_parts = [None if p in unknowns else p for p in parts]
    
    # Identify Year, Month, Day based on 4-digit presence
    year, month, day = None, None, None
    
    if len(clean_parts) >= 1:
        # Check if first part is year
        if clean_parts[0] and len(clean_parts[0]) == 4 and clean_parts[0].isdigit():
            year = clean_parts[0]
            month = clean_parts[1] if len(clean_parts) > 1 else None
            day = clean_parts[2] if len(clean_parts) > 2 else None
        # Check if last part is year
        elif len(clean_parts) >= 3 and clean_parts[2] and len(clean_parts[2]) == 4 and clean_parts[2].isdigit():
            year = clean_parts[2]
            part1, part2 = clean_parts[0], clean_parts[1]
            if part1 and part1.isalpha(): # MMM-DD-YYYY
                month = part1
                day = part2
            elif part2 and part2.isalpha(): # DD-MMM-YYYY
                month = part2
                day = part1
            else:
                # Both numeric or None
                if part1 and part1.isdigit() and int(part1) > 12:
                    # part1 is definitely day -> DD-MM-YYYY
                    day = part1
                    month = part2
                elif part2 and part2.isdigit() and int(part2) > 12:
                    # part2 is definitely day -> MM-DD-YYYY
                    month = part1
                    day = part2
                else:
                    # Ambiguous, or one/both are None. 
                    # Let's assume DD-MM-YYYY as it's more common in clinical outside US,
                    # but if part1 is missing, it's UN/MM/YYYY.
                    # Actually, if part1 is missing, we still assume part2 is month.
                    day = part1
                    month = part2
                
    if not year:
        return None
        
    # Format Month
    month_map = {"JAN": "01", "FEB": "02", "MAR": "03", "APR": "04", "MAY": "05", "JUN": "06", 
                 "JUL": "07", "AUG": "08", "SEP": "09", "OCT": "10", "NOV": "11", "DEC": "12"}
    
    if month:
        if month.isalpha():
            month = month_map.get(month[:3], None)
        elif month.isdigit():
            month = month.zfill(2)
        else:
            month = None
            
    if day and day.isdigit():
        day = day.zfill(2)
    else:
        day = None
        
    # SDTM ISO8601 Truncation Rule
    if year and month and day:
        res = f"{year}-{month}-{day}"
        if time_part and not any(u in time_part for u in unknowns):
            # Clean up time separators if they are wonky, or just append
            res += f"T{time_part}"
        return res
    elif year and month:
        return f"{year}-{month}"
    elif year:
        return year
    else:
        return None
