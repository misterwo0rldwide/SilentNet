import re

# Path to the input-event-codes.h file
file_path = "input-event-codes.h"

# Regular expression to match #define macros
define_pattern = re.compile(r"#define\s+(\w+)\s+(\w+)")

# Dictionaries to store the mappings
code_to_name = {}
name_to_code = {}

# Read the file and extract the macros
with open(file_path, "r") as file:
    for line in file:
        match = define_pattern.match(line.strip())
        if match:
            name, code = match.groups()
            # Convert code to integer if it's a hexadecimal or decimal value
            if code.startswith("0x"):
                code = int(code, 16)
            else:
                try:
                    code = int(code)
                except ValueError:
                    continue  # Skip non-integer codes (e.g., KEY_MAX)
            # Add to dictionaries
            code_to_name[code] = name
            name_to_code[name] = code

# Example usage
print("Code to Name:", code_to_name)
print("Name to Code:", name_to_code)

# Example translations
print("KEY_ESC (Name to Code):", name_to_code.get("KEY_ESC", "Not found"))
print("1 (Code to Name):", code_to_name.get(1, "Not found"))
print("KEY_SPACE (Name to Code):", name_to_code.get("KEY_SPACE", "Not found"))
print("57 (Code to Name):", code_to_name.get(57, "Not found"))