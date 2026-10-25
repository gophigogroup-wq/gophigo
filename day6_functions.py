def calculate_vat(price):
    vat= price*0.18
    total= price + vat
    return total
book_price = 20000
final_price = calculate_vat(book_price)

print("original price:", book_price)
print("price with VAT:",final_price)

print("\n--- Bulk Processing ---")
print("A 50,000 book costs:", calculate_vat(50000))
print("A 100,000 book costs:", calculate_vat(100000))
print("A 5,000 book costs:", calculate_vat(5000))

def check_tax_status(amount):
    if amount > 1000000:
        return "High value - Audit"
    elif amount > 500000:
        return "Medium value - Standard"
    else:
        return "Standard - Fast track"

print("\n--- TRA Status Checker ---")
print("2,000,000:", check_tax_status(2000000))
print("750,000:", check_tax_status(750000))
print("100,000:", check_tax_status(100000))

def calculate_discount(price):
    if price > 20000:
        total_price= price * 0.9
        return total_price
    else:
        return price
book_price = 30000
final_price = calculate_discount(book_price)
print("Original price:", book_price)
print("Price with discount:", final_price)
