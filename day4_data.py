
books = ["Python for Beginners", "Strategic Management", "Tax Law in Tanzania"]


print("My book collection:", books)

print("The first book is:", books[0])
print("The second book is:", books[1])

books.append("Entrepreneurship 101")
print("Updated collection:", books)



taxpayer = {
    "name": "Gotorah",
    "district": "Kinondoni",
    "tax_amount": 750000
}

print(taxpayer["name"], "is from", taxpayer["district"])

taxpayer["tax_amount"] = 1200000
print("Updated tax amount:", taxpayer["tax_amount"])


taxpayers = [
    {"name": "Ally", "tax": 2000000},
    {"name": "Fatma", "tax": 450000},
    {"name": "John", "tax": 900000},
    {"name": "Amina", "tax": 1500000}  
]

print("\n--- TRA Batch Processing ---")

for person in taxpayers:
    if person["tax"] > 1000000:
        status = "High value - Audit"
    elif person["tax"] > 500000:
        status = "Medium value - Standard"
    else:
        status = "Standard - Fast track"
        
    print(person["name"], ":", status)
