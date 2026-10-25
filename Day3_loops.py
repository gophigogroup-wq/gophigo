# Task 1: For loop
for number in range(1, 6):
    print("Processing receipt number:", number)
print("done! all 5 receipts processed.")

# Task 2: While loop
countdown = 3
while countdown > 0:
    print("Seconds left:", countdown)
    countdown = countdown - 1

print("Blastoff! 🚀")

# Task 3: TRA Batch Processor
tax_amounts = [2000000, 750000, 150000, 5000000, 20000]

for amount in tax_amounts:
    if amount > 1000000:
        print(amount, "- High value taxpayer. Flag for audit.")
    elif amount > 500000:
        print(amount, "- Medium value taxpayer. Standard processing.")
    else:
        print(amount, "- Standard taxpayer. Fast track.")
