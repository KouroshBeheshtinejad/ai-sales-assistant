from __future__ import annotations

BUSINESS_TYPES = [
    {
        "slug": "clothing",
        "label": "Clothing & Fashion",
        "fields": [
            {"name": "size", "label": "Size", "type": "text", "placeholder": "S, M, L, XL"},
            {"name": "color", "label": "Color", "type": "text", "placeholder": "Black, White, Navy"},
            {"name": "material", "label": "Material", "type": "text", "placeholder": "Cotton, Denim, Silk"},
            {"name": "gender", "label": "Gender", "type": "select", "options": ["Unisex", "Men", "Women", "Kids"]},
        ],
    },
    {
        "slug": "fast_food",
        "label": "Fast Food",
        "fields": [
            {"name": "ingredients", "label": "Ingredients", "type": "textarea", "placeholder": "Chicken, cheese, lettuce"},
            {"name": "spice_level", "label": "Spice Level", "type": "select", "options": ["Low", "Medium", "High"]},
            {"name": "calories", "label": "Calories", "type": "number", "placeholder": "450"},
            {"name": "contains_nuts", "label": "Contains Nuts", "type": "checkbox"},
        ],
    },
    {
        "slug": "restaurant",
        "label": "Restaurant",
        "fields": [
            {"name": "cuisine", "label": "Cuisine", "type": "text", "placeholder": "Persian, Italian"},
            {"name": "serving_size", "label": "Serving Size", "type": "text", "placeholder": "Single / Family"},
            {"name": "dietary", "label": "Dietary Tags", "type": "text", "placeholder": "Vegan, Halal, Gluten-free"},
            {"name": "prep_time", "label": "Prep Time (minutes)", "type": "number", "placeholder": "15"},
        ],
    },
    {
        "slug": "bakery",
        "label": "Bakery",
        "fields": [
            {"name": "flavor", "label": "Flavor", "type": "text", "placeholder": "Vanilla, Chocolate"},
            {"name": "weight", "label": "Weight", "type": "text", "placeholder": "250g, 500g"},
            {"name": "contains_egg", "label": "Contains Egg", "type": "checkbox"},
            {"name": "freshness", "label": "Freshness", "type": "select", "options": ["Same Day", "48h", "72h"]},
        ],
    },
    {
        "slug": "cafe",
        "label": "Cafe",
        "fields": [
            {"name": "coffee_origin", "label": "Coffee Origin", "type": "text", "placeholder": "Ethiopia, Brazil"},
            {"name": "roast_level", "label": "Roast Level", "type": "select", "options": ["Light", "Medium", "Dark"]},
            {"name": "milk_type", "label": "Milk Type", "type": "select", "options": ["Regular", "Oat", "Almond", "Soy"]},
            {"name": "temperature", "label": "Temperature", "type": "select", "options": ["Hot", "Ice", "Warm"]},
        ],
    },
    {
        "slug": "pharmacy",
        "label": "Pharmacy",
        "fields": [
            {"name": "dosage", "label": "Dosage", "type": "text", "placeholder": "500 mg"},
            {"name": "usage", "label": "Usage", "type": "textarea", "placeholder": "Take one tablet after meal"},
            {"name": "prescription_required", "label": "Prescription Required", "type": "checkbox"},
            {"name": "expiry_date", "label": "Expiry Date", "type": "date"},
        ],
    },
    {
        "slug": "electronics",
        "label": "Electronics",
        "fields": [
            {"name": "brand", "label": "Brand", "type": "text", "placeholder": "Samsung, Sony"},
            {"name": "model", "label": "Model", "type": "text", "placeholder": "X10 Pro"},
            {"name": "warranty", "label": "Warranty (months)", "type": "number", "placeholder": "12"},
            {"name": "power", "label": "Power Specs", "type": "text", "placeholder": "220V, 65W"},
        ],
    },
    {
        "slug": "furniture",
        "label": "Furniture",
        "fields": [
            {"name": "material", "label": "Material", "type": "text", "placeholder": "Wood, Metal"},
            {"name": "dimensions", "label": "Dimensions", "type": "text", "placeholder": "120x80x75 cm"},
            {"name": "color", "label": "Color", "type": "text", "placeholder": "Oak, Walnut"},
            {"name": "assembly_required", "label": "Assembly Required", "type": "checkbox"},
        ],
    },
    {
        "slug": "grocery",
        "label": "Grocery Store",
        "fields": [
            {"name": "origin", "label": "Origin", "type": "text", "placeholder": "Local, Imported"},
            {"name": "packaging", "label": "Packaging", "type": "text", "placeholder": "500g, Bottle 1L"},
            {"name": "shelf_life", "label": "Shelf Life", "type": "text", "placeholder": "12 months"},
            {"name": "organic", "label": "Organic", "type": "checkbox"},
        ],
    },
    {
        "slug": "cosmetics",
        "label": "Cosmetics",
        "fields": [
            {"name": "skin_type", "label": "Skin Type", "type": "select", "options": ["Dry", "Oily", "Sensitive", "Normal"]},
            {"name": "fragrance", "label": "Fragrance", "type": "text", "placeholder": "Rose, Citrus"},
            {"name": "volume", "label": "Volume", "type": "text", "placeholder": "50 ml"},
            {"name": "cruelty_free", "label": "Cruelty Free", "type": "checkbox"},
        ],
    },
    {
        "slug": "jewelry",
        "label": "Jewelry",
        "fields": [
            {"name": "metal", "label": "Metal", "type": "text", "placeholder": "Gold, Silver"},
            {"name": "stone", "label": "Stone", "type": "text", "placeholder": "Diamond, Ruby"},
            {"name": "size", "label": "Ring Size", "type": "text", "placeholder": "6, 7, 8"},
            {"name": "certified", "label": "Certified", "type": "checkbox"},
        ],
    },
    {
        "slug": "beauty_salon",
        "label": "Beauty Salon",
        "fields": [
            {"name": "service_type", "label": "Service Type", "type": "text", "placeholder": "Haircut, Facial"},
            {"name": "duration", "label": "Duration (minutes)", "type": "number", "placeholder": "45"},
            {"name": "hair_type", "label": "Hair Type", "type": "select", "options": ["Straight", "Curly", "Wavy", "Coily"]},
            {"name": "product_brand", "label": "Product Brand", "type": "text", "placeholder": "Brand name"},
        ],
    },
    {
        "slug": "home_decor",
        "label": "Home Decor",
        "fields": [
            {"name": "style", "label": "Style", "type": "text", "placeholder": "Modern, Classic"},
            {"name": "material", "label": "Material", "type": "text", "placeholder": "Ceramic, Wood"},
            {"name": "room", "label": "Room", "type": "select", "options": ["Living Room", "Bed Room", "Kitchen", "Office"]},
            {"name": "dimensions", "label": "Dimensions", "type": "text", "placeholder": "40x50 cm"},
        ],
    },
    {
        "slug": "stationery",
        "label": "Stationery",
        "fields": [
            {"name": "paper_type", "label": "Paper Type", "type": "text", "placeholder": "A4, Notebook"},
            {"name": "ink_color", "label": "Ink Color", "type": "text", "placeholder": "Blue, Black"},
            {"name": "page_count", "label": "Page Count", "type": "number", "placeholder": "120"},
            {"name": "binding", "label": "Binding", "type": "select", "options": ["Spiral", "Hardcover", "Softcover"]},
        ],
    },
    {
        "slug": "pet_store",
        "label": "Pet Store",
        "fields": [
            {"name": "pet_type", "label": "Pet Type", "type": "select", "options": ["Dog", "Cat", "Bird", "Fish"]},
            {"name": "age_group", "label": "Age Group", "type": "select", "options": ["Puppy", "Adult", "Senior"]},
            {"name": "breed", "label": "Breed", "type": "text", "placeholder": "Labrador"},
            {"name": "nutrition", "label": "Nutrition Info", "type": "textarea", "placeholder": "Chicken, rice, vitamins"},
        ],
    },
    {
        "slug": "sports",
        "label": "Sports & Outdoor",
        "fields": [
            {"name": "sport_type", "label": "Sport Type", "type": "text", "placeholder": "Running, Football"},
            {"name": "size", "label": "Size", "type": "text", "placeholder": "S, M, L"},
            {"name": "material", "label": "Material", "type": "text", "placeholder": "Nylon, Cotton"},
            {"name": "waterproof", "label": "Waterproof", "type": "checkbox"},
        ],
    },
    {
        "slug": "fitness",
        "label": "Fitness & Gym",
        "fields": [
            {"name": "equipment_type", "label": "Equipment Type", "type": "text", "placeholder": "Dumbbell, Treadmill"},
            {"name": "weight_kg", "label": "Weight (kg)", "type": "number", "placeholder": "10"},
            {"name": "resistance", "label": "Resistance", "type": "text", "placeholder": "Low, Medium, High"},
            {"name": "assembly", "label": "Assembly", "type": "select", "options": ["Easy", "Moderate", "Hard"]},
        ],
    },
    {
        "slug": "automotive",
        "label": "Automotive",
        "fields": [
            {"name": "vehicle_type", "label": "Vehicle Type", "type": "text", "placeholder": "Car, Motorcycle"},
            {"name": "compatibility", "label": "Compatibility", "type": "text", "placeholder": "Toyota Corolla 2019"},
            {"name": "part_number", "label": "Part Number", "type": "text", "placeholder": "AB-245"},
            {"name": "warranty", "label": "Warranty", "type": "text", "placeholder": "12 months"},
        ],
    },
    {
        "slug": "books_music",
        "label": "Books & Music",
        "fields": [
            {"name": "author", "label": "Author / Artist", "type": "text", "placeholder": "Author or Artist"},
            {"name": "genre", "label": "Genre", "type": "text", "placeholder": "Fiction, Jazz"},
            {"name": "format", "label": "Format", "type": "select", "options": ["Hardcover", "Paperback", "CD", "Vinyl"]},
            {"name": "language", "label": "Language", "type": "text", "placeholder": "English, Persian"},
        ],
    },
    {
        "slug": "toys",
        "label": "Toys & Games",
        "fields": [
            {"name": "age_range", "label": "Age Range", "type": "text", "placeholder": "3-5 years"},
            {"name": "material", "label": "Material", "type": "text", "placeholder": "Plastic, Wood"},
            {"name": "category", "label": "Category", "type": "select", "options": ["Puzzle", "Board Game", "Action Toy", "Educational"]},
            {"name": "battery_required", "label": "Battery Required", "type": "checkbox"},
        ],
    },
    {
        "slug": "hardware",
        "label": "Hardware & Tools",
        "fields": [
            {"name": "tool_type", "label": "Tool Type", "type": "text", "placeholder": "Drill, Screwdriver"},
            {"name": "material", "label": "Material", "type": "text", "placeholder": "Steel, Aluminum"},
            {"name": "power_source", "label": "Power Source", "type": "select", "options": ["Manual", "Battery", "Electric"]},
            {"name": "size", "label": "Size", "type": "text", "placeholder": "1/2 inch"},
        ],
    },
    {
        "slug": "flowers",
        "label": "Flowers & Gifts",
        "fields": [
            {"name": "flower_type", "label": "Flower Type", "type": "text", "placeholder": "Rose, Tulip"},
            {"name": "arrangement", "label": "Arrangement", "type": "select", "options": ["Bouquet", "Basket", "Box"]},
            {"name": "occasion", "label": "Occasion", "type": "text", "placeholder": "Birthday, Anniversary"},
            {"name": "delivery_date", "label": "Delivery Date", "type": "date"},
        ],
    },
    {
        "slug": "real_estate",
        "label": "Real Estate",
        "fields": [
            {"name": "property_type", "label": "Property Type", "type": "select", "options": ["Apartment", "Villa", "Office", "Land"]},
            {"name": "location", "label": "Location", "type": "text", "placeholder": "District name"},
            {"name": "area", "label": "Area (sqm)", "type": "number", "placeholder": "120"},
            {"name": "bedrooms", "label": "Bedrooms", "type": "number", "placeholder": "3"},
        ],
    },
    {
        "slug": "travel",
        "label": "Travel & Tourism",
        "fields": [
            {"name": "destination", "label": "Destination", "type": "text", "placeholder": "Paris, Dubai"},
            {"name": "travel_days", "label": "Travel Days", "type": "number", "placeholder": "5"},
            {"name": "inclusion", "label": "Inclusions", "type": "textarea", "placeholder": "Hotel, transfer, tour"},
            {"name": "season", "label": "Season", "type": "select", "options": ["Spring", "Summer", "Autumn", "Winter"]},
        ],
    },
    {
        "slug": "medical_clinic",
        "label": "Medical Clinic",
        "fields": [
            {"name": "service", "label": "Service", "type": "text", "placeholder": "General checkup"},
            {"name": "doctor_name", "label": "Doctor Name", "type": "text", "placeholder": "Dr. Rahimi"},
            {"name": "duration", "label": "Duration (minutes)", "type": "number", "placeholder": "30"},
            {"name": "insurance_covered", "label": "Insurance Covered", "type": "checkbox"},
        ],
    },
    {
        "slug": "dental",
        "label": "Dental Clinic",
        "fields": [
            {"name": "procedure", "label": "Procedure", "type": "text", "placeholder": "Teeth whitening"},
            {"name": "session_count", "label": "Session Count", "type": "number", "placeholder": "2"},
            {"name": "anesthesia", "label": "Anesthesia", "type": "checkbox"},
            {"name": "specialist", "label": "Specialist", "type": "text", "placeholder": "Orthodontist"},
        ],
    },
    {
        "slug": "yoga",
        "label": "Yoga & Wellness",
        "fields": [
            {"name": "session_type", "label": "Session Type", "type": "text", "placeholder": "Vinyasa, Hatha"},
            {"name": "duration", "label": "Duration (minutes)", "type": "number", "placeholder": "60"},
            {"name": "level", "label": "Level", "type": "select", "options": ["Beginner", "Intermediate", "Advanced"]},
            {"name": "equipment", "label": "Equipment", "type": "text", "placeholder": "Mat, Block"},
        ],
    },
    {
        "slug": "educational",
        "label": "Educational Services",
        "fields": [
            {"name": "course_level", "label": "Course Level", "type": "text", "placeholder": "Beginner, Advanced"},
            {"name": "duration_hours", "label": "Duration (hours)", "type": "number", "placeholder": "12"},
            {"name": "teacher_name", "label": "Teacher Name", "type": "text", "placeholder": "Alex"},
            {"name": "certificate", "label": "Certificate", "type": "checkbox"},
        ],
    },
    {
        "slug": "digital_products",
        "label": "Digital Products",
        "fields": [
            {"name": "file_type", "label": "File Type", "type": "select", "options": ["PDF", "ZIP", "MP4", "PSD"]},
            {"name": "license", "label": "License", "type": "text", "placeholder": "Personal, Commercial"},
            {"name": "download_count", "label": "Download Count", "type": "number", "placeholder": "1000"},
            {"name": "product_version", "label": "Version", "type": "text", "placeholder": "1.0.0"},
        ],
    },
    {
        "slug": "software",
        "label": "Software & SaaS",
        "fields": [
            {"name": "platform", "label": "Platform", "type": "select", "options": ["Web", "Mobile", "Desktop"]},
            {"name": "plan_type", "label": "Plan Type", "type": "select", "options": ["Free", "Starter", "Pro", "Enterprise"]},
            {"name": "integration", "label": "Integrations", "type": "text", "placeholder": "Slack, Zapier"},
            {"name": "trial_days", "label": "Trial Days", "type": "number", "placeholder": "14"},
        ],
    },
    {
        "slug": "agency",
        "label": "Marketing Agency",
        "fields": [
            {"name": "package", "label": "Package", "type": "text", "placeholder": "SEO Growth"},
            {"name": "deliverable", "label": "Deliverable", "type": "textarea", "placeholder": "Ads creative, landing page"},
            {"name": "timeline", "label": "Timeline (weeks)", "type": "number", "placeholder": "8"},
            {"name": "reporting", "label": "Reporting", "type": "select", "options": ["Weekly", "Monthly", "Quarterly"]},
        ],
    },
    {
        "slug": "construction",
        "label": "Construction",
        "fields": [
            {"name": "project_type", "label": "Project Type", "type": "text", "placeholder": "Renovation, New Build"},
            {"name": "area", "label": "Area (sqm)", "type": "number", "placeholder": "500"},
            {"name": "deadline", "label": "Deadline", "type": "date"},
            {"name": "materials", "label": "Materials", "type": "textarea", "placeholder": "Concrete, Wood, Glass"},
        ],
    },
    {
        "slug": "landscaping",
        "label": "Landscaping",
        "fields": [
            {"name": "service_area", "label": "Service Area", "type": "text", "placeholder": "Garden, Backyard"},
            {"name": "plant_type", "label": "Plant Type", "type": "text", "placeholder": "Trees, Flowers"},
            {"name": "maintenance", "label": "Maintenance", "type": "select", "options": ["Weekly", "Monthly", "Seasonal"]},
            {"name": "irrigation", "label": "Irrigation", "type": "checkbox"},
        ],
    },
    {
        "slug": "cleaning",
        "label": "Cleaning Services",
        "fields": [
            {"name": "service_type", "label": "Service Type", "type": "text", "placeholder": "Home, Office"},
            {"name": "frequency", "label": "Frequency", "type": "select", "options": ["One Time", "Weekly", "Monthly"]},
            {"name": "room_count", "label": "Room Count", "type": "number", "placeholder": "4"},
            {"name": "supplies_included", "label": "Supplies Included", "type": "checkbox"},
        ],
    },
    {
        "slug": "laundry",
        "label": "Laundry Service",
        "fields": [
            {"name": "fabric_type", "label": "Fabric Type", "type": "text", "placeholder": "Cotton, Wool"},
            {"name": "service_type", "label": "Service Type", "type": "select", "options": ["Wash", "Dry Clean", "Iron"]},
            {"name": "pickup_time", "label": "Pickup Time", "type": "text", "placeholder": "9:00 AM"},
            {"name": "stain_removal", "label": "Stain Removal", "type": "checkbox"},
        ],
    },
    {
        "slug": "printing",
        "label": "Printing & Design",
        "fields": [
            {"name": "print_type", "label": "Print Type", "type": "select", "options": ["Business Cards", "Brochure", "Poster", "Packaging"]},
            {"name": "material", "label": "Material", "type": "text", "placeholder": "Glossy, Matte"},
            {"name": "quantity", "label": "Quantity", "type": "number", "placeholder": "500"},
            {"name": "finishing", "label": "Finishing", "type": "text", "placeholder": "Laminate, UV"},
        ],
    },
    {
        "slug": "event_planning",
        "label": "Event Planning",
        "fields": [
            {"name": "event_type", "label": "Event Type", "type": "text", "placeholder": "Wedding, Conference"},
            {"name": "guests", "label": "Guest Count", "type": "number", "placeholder": "150"},
            {"name": "venue", "label": "Venue", "type": "text", "placeholder": "Hotel, Garden"},
            {"name": "catering", "label": "Catering", "type": "checkbox"},
        ],
    },
    {
        "slug": "wedding",
        "label": "Wedding Services",
        "fields": [
            {"name": "service_type", "label": "Service Type", "type": "text", "placeholder": "Photography, Dress"},
            {"name": "guest_count", "label": "Guest Count", "type": "number", "placeholder": "200"},
            {"name": "venue_style", "label": "Venue Style", "type": "text", "placeholder": "Garden, Ballroom"},
            {"name": "theme", "label": "Theme", "type": "text", "placeholder": "Classic, Royal"},
        ],
    },
    {
        "slug": "artist_shop",
        "label": "Artist Shop",
        "fields": [
            {"name": "art_medium", "label": "Art Medium", "type": "text", "placeholder": "Oil, Watercolor"},
            {"name": "canvas_size", "label": "Canvas Size", "type": "text", "placeholder": "50x70 cm"},
            {"name": "framed", "label": "Framed", "type": "checkbox"},
            {"name": "series", "label": "Series", "type": "text", "placeholder": "Nature collection"},
        ],
    },
    {
        "slug": "handmade",
        "label": "Handmade Products",
        "fields": [
            {"name": "craft_type", "label": "Craft Type", "type": "text", "placeholder": "Ceramic, Knit"},
            {"name": "material", "label": "Material", "type": "text", "placeholder": "Clay, Wool"},
            {"name": "handcrafted", "label": "Handcrafted", "type": "checkbox"},
            {"name": "finish", "label": "Finish", "type": "text", "placeholder": "Matte, Glossy"},
        ],
    },
    {
        "slug": "agricultural",
        "label": "Agricultural Products",
        "fields": [
            {"name": "crop_type", "label": "Crop Type", "type": "text", "placeholder": "Tomato, Rice"},
            {"name": "organic", "label": "Organic", "type": "checkbox"},
            {"name": "harvest_season", "label": "Harvest Season", "type": "text", "placeholder": "Spring"},
            {"name": "quality_grade", "label": "Quality Grade", "type": "select", "options": ["A", "B", "C"]},
        ],
    },
    {
        "slug": "veterinary",
        "label": "Veterinary Clinic",
        "fields": [
            {"name": "animal_type", "label": "Animal Type", "type": "select", "options": ["Dog", "Cat", "Bird", "Horse"]},
            {"name": "service", "label": "Service", "type": "text", "placeholder": "Vaccination, Surgery"},
            {"name": "pet_age", "label": "Pet Age", "type": "text", "placeholder": "2 years"},
            {"name": "follow_up", "label": "Follow Up", "type": "checkbox"},
        ],
    },
    {
        "slug": "aquarium",
        "label": "Aquarium & Fish",
        "fields": [
            {"name": "fish_type", "label": "Fish Type", "type": "text", "placeholder": "Goldfish, Betta"},
            {"name": "tank_size", "label": "Tank Size (L)", "type": "number", "placeholder": "80"},
            {"name": "water_type", "label": "Water Type", "type": "select", "options": ["Freshwater", "Saltwater"]},
            {"name": "feeding", "label": "Feeding Info", "type": "textarea", "placeholder": "Pellets, frozen food"},
        ],
    },
    {
        "slug": "garden",
        "label": "Garden Center",
        "fields": [
            {"name": "plant_type", "label": "Plant Type", "type": "text", "placeholder": "Flower, Tree"},
            {"name": "pot_size", "label": "Pot Size", "type": "text", "placeholder": "10 cm"},
            {"name": "sun_requirement", "label": "Sun Requirement", "type": "select", "options": ["Full Sun", "Partial Shade", "Shade"]},
            {"name": "watering", "label": "Watering Need", "type": "text", "placeholder": "Twice a week"},
        ],
    },
    {
        "slug": "grocery_delivery",
        "label": "Grocery Delivery",
        "fields": [
            {"name": "delivery_window", "label": "Delivery Window", "type": "text", "placeholder": "Today, 2 hours"},
            {"name": "temperature_need", "label": "Temperature Need", "type": "select", "options": ["Ambient", "Cold", "Frozen"]},
            {"name": "packaging", "label": "Packaging", "type": "text", "placeholder": "Recyclable box"},
            {"name": "freshness", "label": "Freshness Guarantee", "type": "checkbox"},
        ],
    },
    {
        "slug": "productivity",
        "label": "Productivity Tools",
        "fields": [
            {"name": "use_case", "label": "Use Case", "type": "text", "placeholder": "Project management"},
            {"name": "team_size", "label": "Team Size", "type": "number", "placeholder": "15"},
            {"name": "integration", "label": "Integration", "type": "text", "placeholder": "Google Drive"},
            {"name": "deployment", "label": "Deployment", "type": "select", "options": ["Cloud", "Self-hosted", "Hybrid"]},
        ],
    },
    {
        "slug": "car_rental",
        "label": "Car Rental",
        "fields": [
            {"name": "car_model", "label": "Car Model", "type": "text", "placeholder": "Toyota Corolla"},
            {"name": "transmission", "label": "Transmission", "type": "select", "options": ["Auto", "Manual"]},
            {"name": "fuel_type", "label": "Fuel Type", "type": "select", "options": ["Petrol", "Diesel", "Hybrid"]},
            {"name": "rental_days", "label": "Rental Days", "type": "number", "placeholder": "3"},
        ],
    },
    {
        "slug": "boat",
        "label": "Boats & Marine",
        "fields": [
            {"name": "boat_type", "label": "Boat Type", "type": "text", "placeholder": "Yacht, Fishing boat"},
            {"name": "length_m", "label": "Length (m)", "type": "number", "placeholder": "8"},
            {"name": "engine", "label": "Engine", "type": "text", "placeholder": "150 HP"},
            {"name": "capacity", "label": "Capacity", "type": "number", "placeholder": "5"},
        ],
    },
    {
        "slug": "camping",
        "label": "Camping & Outdoor",
        "fields": [
            {"name": "camp_type", "label": "Camp Type", "type": "text", "placeholder": "Tent, Caravan"},
            {"name": "capacity", "label": "Capacity", "type": "number", "placeholder": "4"},
            {"name": "season", "label": "Season", "type": "select", "options": ["Spring", "Summer", "Autumn", "Winter"]},
            {"name": "weight_kg", "label": "Weight (kg)", "type": "number", "placeholder": "12"},
        ],
    },
]


def get_business_types():
    return BUSINESS_TYPES


def get_business_type(slug: str | None):
    if not slug:
        return BUSINESS_TYPES[0]

    normalized_slug = slug.strip().lower()
    for business_type in BUSINESS_TYPES:
        if business_type["slug"] == normalized_slug:
            return business_type

    return BUSINESS_TYPES[0]


def get_business_type_label(slug: str | None):
    return get_business_type(slug)["label"]


def get_business_fields_for_store(store_business_type: str | None):
    return get_business_type(store_business_type)["fields"]


def normalize_business_type(value: str | None):
    if not value:
        return "clothing"
    normalized = value.strip().lower().replace(" ", "_")
    return normalized if normalized in {item["slug"] for item in BUSINESS_TYPES} else "clothing"
