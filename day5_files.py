
total_tax = 0

file = open(r"C:\Users\gphilemon\Desktop\taxpayers_data1.csv", "r")
lines = file.readlines()
file.close()

print("--- TRA Data Processing ---")

for line in lines:
    # Skip the header row
    if line.startswith("Name"):
        continue
        
    parts = line.split(",")
    
    if len(parts) < 3:
        continue
        
    name = parts[0]
    district = parts[1]
    tax = float(parts[2])
    
    total_tax = total_tax + tax
    print("Processed:", name, "from", district)


print("\nTotal Tax Collected:", total_tax)
