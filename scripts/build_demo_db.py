#!/usr/bin/env python3
"""
Build a compact demo database for GitHub distribution.

Creates a database with:
- All vital level 1-3 entities (~1,000)
- Extended showcase entities for impressive demos
- Full SPATIAL positions and rich relations for demos
"""

import sqlite3
import json
from pathlib import Path

SOURCE_DB = Path("/Users/rohanvinaik/relational-ai/data/sparse_wiki.db")
OUTPUT_DB = Path(__file__).parent.parent / "data" / "entities_demo.db"

# ============================================================================
# SHOWCASE ENTITIES - Extended for impressive demos
# ============================================================================

SHOWCASE_ENTITIES = {
    # === SCIENTISTS & INVENTORS ===
    "Q_Albert_Einstein", "Q_Marie_Curie", "Q_Isaac_Newton", "Q_Charles_Darwin",
    "Q_Galileo_Galilei", "Q_Nikola_Tesla", "Q_Thomas_Edison", "Q_Leonardo_da_Vinci",
    "Q_Pierre_Curie", "Q_Stephen_Hawking", "Q_Richard_Feynman", "Q_Niels_Bohr",
    "Q_Max_Planck", "Q_Werner_Heisenberg", "Q_Erwin_Schrodinger", "Q_Michael_Faraday",
    "Q_James_Clerk_Maxwell", "Q_Louis_Pasteur", "Q_Alexander_Fleming", "Q_Gregor_Mendel",
    "Q_Johannes_Kepler", "Q_Nicolaus_Copernicus", "Q_Archimedes", "Q_Pythagoras",
    "Q_Aristotle", "Q_Plato", "Q_Socrates", "Q_Euclid",
    "Q_Alexander_Graham_Bell", "Q_Wright_brothers", "Q_Henry_Ford", "Q_James_Watt",
    "Q_Benjamin_Franklin", "Q_Guglielmo_Marconi", "Q_Johannes_Gutenberg",

    # === ARTISTS & WRITERS ===
    "Q_William_Shakespeare", "Q_Wolfgang_Amadeus_Mozart", "Q_Ludwig_van_Beethoven",
    "Q_Vincent_van_Gogh", "Q_Pablo_Picasso", "Q_Johann_Sebastian_Bach",
    "Q_Michelangelo", "Q_Rembrandt", "Q_Claude_Monet", "Q_Salvador_Dali",
    "Q_Frida_Kahlo", "Q_Leonardo_da_Vinci", "Q_Raphael", "Q_Caravaggio",
    "Q_Charles_Dickens", "Q_Mark_Twain", "Q_Jane_Austen", "Q_Leo_Tolstoy",
    "Q_Fyodor_Dostoevsky", "Q_Ernest_Hemingway", "Q_Franz_Kafka", "Q_Oscar_Wilde",
    "Q_Edgar_Allan_Poe", "Q_Homer", "Q_Dante_Alighieri", "Q_Miguel_de_Cervantes",
    "Q_Frederic_Chopin", "Q_Franz_Schubert", "Q_Giuseppe_Verdi", "Q_Richard_Wagner",

    # === CITIES ===
    "Q_Paris", "Q_London", "Q_New_York_City", "Q_Tokyo", "Q_Rome", "Q_Berlin",
    "Q_Los_Angeles", "Q_Beijing", "Q_Moscow", "Q_Sydney", "Q_Hong_Kong",
    "Q_Singapore", "Q_Dubai", "Q_Mumbai", "Q_Shanghai", "Q_Sao_Paulo",
    "Q_Mexico_City", "Q_Cairo", "Q_Istanbul", "Q_Vienna", "Q_Amsterdam",
    "Q_Barcelona", "Q_Madrid", "Q_Athens", "Q_Jerusalem", "Q_Venice",
    "Q_Florence", "Q_Prague", "Q_Stockholm", "Q_Copenhagen",

    # === COUNTRIES ===
    "Q_France", "Q_United_Kingdom", "Q_United_States", "Q_Germany", "Q_Italy",
    "Q_Japan", "Q_China", "Q_India", "Q_Russia", "Q_Brazil", "Q_Australia",
    "Q_Canada", "Q_Spain", "Q_Mexico", "Q_Egypt", "Q_Greece", "Q_Turkey",
    "Q_South_Korea", "Q_Netherlands", "Q_Switzerland", "Q_Sweden", "Q_Norway",
    "Q_Poland", "Q_Argentina", "Q_South_Africa", "Q_Israel", "Q_Iran",
    "Q_Saudi_Arabia", "Q_Indonesia", "Q_Thailand", "Q_Vietnam", "Q_Pakistan",

    # === CONTINENTS ===
    "Q_Europe", "Q_Asia", "Q_North_America", "Q_South_America", "Q_Africa",
    "Q_Oceania", "Q_Antarctica",

    # === CELESTIAL BODIES ===
    "Q_Earth", "Q_Moon", "Q_Sun", "Q_Mars", "Q_Jupiter", "Q_Venus", "Q_Saturn",
    "Q_Mercury", "Q_Neptune", "Q_Uranus", "Q_Pluto", "Q_Milky_Way",

    # === LANDMARKS ===
    "Q_Eiffel_Tower", "Q_Statue_of_Liberty", "Q_Great_Wall_of_China", "Q_Colosseum",
    "Q_Taj_Mahal", "Q_Big_Ben", "Q_Pyramids_of_Giza", "Q_Machu_Picchu",
    "Q_Petra", "Q_Christ_the_Redeemer", "Q_Acropolis_of_Athens", "Q_Stonehenge",
    "Q_Sydney_Opera_House", "Q_Empire_State_Building", "Q_Burj_Khalifa",
    "Q_Golden_Gate_Bridge", "Q_Tower_of_London", "Q_Notre-Dame_de_Paris",
    "Q_Louvre", "Q_Vatican_City", "Q_Sistine_Chapel", "Q_Leaning_Tower_of_Pisa",

    # === CONCEPTS & DISCOVERIES ===
    "Q_Theory_of_relativity", "Q_Evolution", "Q_Gravity", "Q_Quantum_mechanics",
    "Q_Radioactivity", "Q_DNA", "Q_Atom", "Q_Light", "Q_Electricity",
    "Q_Polonium", "Q_Radium", "Q_Penicillin", "Q_Vaccine", "Q_X-ray",
    "Q_Black_hole", "Q_Big_Bang", "Q_Electromagnetism", "Q_Thermodynamics",
    "Q_Cell", "Q_Gene", "Q_Photosynthesis", "Q_Plate_tectonics",
    "Q_General_relativity", "Q_Special_relativity", "Q_Wave-particle_duality",

    # === INVENTIONS ===
    "Q_Telephone", "Q_Light_bulb", "Q_Printing_press", "Q_Steam_engine",
    "Q_Internet", "Q_Computer", "Q_Television", "Q_Radio", "Q_Airplane",
    "Q_Automobile", "Q_Wheel", "Q_Compass", "Q_Telescope", "Q_Microscope",
    "Q_Vaccine", "Q_Antibiotic", "Q_Camera", "Q_Refrigerator",
    "Q_Electric_motor", "Q_Internal_combustion_engine", "Q_Battery",
    "Q_Transistor", "Q_Laser", "Q_Satellite", "Q_Nuclear_reactor",

    # === WORKS OF ART & LITERATURE ===
    "Q_Hamlet", "Q_Mona_Lisa", "Q_Symphony_No._9_(Beethoven)", "Q_Romeo_and_Juliet",
    "Q_The_Starry_Night", "Q_Don_Quixote", "Q_The_Last_Supper", "Q_David_(Michelangelo)",
    "Q_The_Birth_of_Venus", "Q_Guernica", "Q_The_Scream", "Q_Girl_with_a_Pearl_Earring",
    "Q_Les_Miserables", "Q_War_and_Peace", "Q_Crime_and_Punishment", "Q_Pride_and_Prejudice",
    "Q_The_Divine_Comedy", "Q_The_Odyssey", "Q_The_Iliad", "Q_Macbeth",
    "Q_A_Midsummer_Nights_Dream", "Q_The_Tempest", "Q_King_Lear", "Q_Othello",

    # === AWARDS & INSTITUTIONS ===
    "Q_Nobel_Prize", "Q_Nobel_Prize_in_Physics", "Q_Nobel_Prize_in_Chemistry",
    "Q_Nobel_Prize_in_Literature", "Q_Nobel_Peace_Prize", "Q_Fields_Medal",
    "Q_Turing_Award", "Q_Academy_Award", "Q_Grammy_Award", "Q_Pulitzer_Prize",
    "Q_Harvard_University", "Q_University_of_Cambridge", "Q_University_of_Oxford",
    "Q_MIT", "Q_Stanford_University", "Q_Yale_University", "Q_Princeton_University",
    "Q_Caltech", "Q_ETH_Zurich", "Q_Sorbonne", "Q_University_of_Tokyo",

    # === HISTORICAL FIGURES ===
    "Q_Napoleon", "Q_Julius_Caesar", "Q_Alexander_the_Great", "Q_Cleopatra",
    "Q_Abraham_Lincoln", "Q_George_Washington", "Q_Winston_Churchill",
    "Q_Mahatma_Gandhi", "Q_Nelson_Mandela", "Q_Martin_Luther_King_Jr.",
    "Q_Queen_Victoria", "Q_Queen_Elizabeth_II", "Q_Genghis_Khan",
    "Q_Charlemagne", "Q_Peter_the_Great", "Q_Catherine_the_Great",
    "Q_Louis_XIV", "Q_Henry_VIII", "Q_Elizabeth_I", "Q_Joan_of_Arc",
    "Q_Confucius", "Q_Buddha", "Q_Jesus", "Q_Muhammad", "Q_Moses",

    # === HISTORICAL EVENTS ===
    "Q_World_War_I", "Q_World_War_II", "Q_French_Revolution", "Q_Renaissance",
    "Q_Industrial_Revolution", "Q_American_Revolution", "Q_Russian_Revolution",
    "Q_Cold_War", "Q_Fall_of_the_Berlin_Wall", "Q_Moon_landing",
    "Q_Black_Death", "Q_Age_of_Enlightenment", "Q_Protestant_Reformation",
    "Q_Ancient_Rome", "Q_Ancient_Greece", "Q_Ancient_Egypt",
    "Q_Roman_Empire", "Q_Byzantine_Empire", "Q_Ottoman_Empire", "Q_British_Empire",

    # === MODERN TECH FIGURES ===
    "Q_Steve_Jobs", "Q_Bill_Gates", "Q_Elon_Musk", "Q_Mark_Zuckerberg",
    "Q_Jeff_Bezos", "Q_Tim_Berners-Lee", "Q_Alan_Turing", "Q_Ada_Lovelace",
    "Q_Grace_Hopper", "Q_Linus_Torvalds",

    # === COMPANIES & ORGANIZATIONS ===
    "Q_Apple_Inc.", "Q_Google", "Q_Microsoft", "Q_Amazon", "Q_Facebook",
    "Q_NASA", "Q_United_Nations", "Q_European_Union", "Q_NATO",
    "Q_World_Health_Organization", "Q_International_Space_Station",
}

# ============================================================================
# SPATIAL DIMENSION DATA
# ============================================================================

SPATIAL_DATA = {
    # Cities - Extended
    "Q_Paris": ["Earth", "Europe", "France", "Paris"],
    "Q_London": ["Earth", "Europe", "United Kingdom", "England", "London"],
    "Q_New_York_City": ["Earth", "North America", "United States", "New York", "New York City"],
    "Q_Tokyo": ["Earth", "Asia", "Japan", "Tokyo"],
    "Q_Rome": ["Earth", "Europe", "Italy", "Rome"],
    "Q_Berlin": ["Earth", "Europe", "Germany", "Berlin"],
    "Q_Los_Angeles": ["Earth", "North America", "United States", "California", "Los Angeles"],
    "Q_Beijing": ["Earth", "Asia", "China", "Beijing"],
    "Q_Moscow": ["Earth", "Europe", "Russia", "Moscow"],
    "Q_Sydney": ["Earth", "Oceania", "Australia", "New South Wales", "Sydney"],
    "Q_Hong_Kong": ["Earth", "Asia", "China", "Hong Kong"],
    "Q_Singapore": ["Earth", "Asia", "Singapore"],
    "Q_Dubai": ["Earth", "Asia", "United Arab Emirates", "Dubai"],
    "Q_Mumbai": ["Earth", "Asia", "India", "Maharashtra", "Mumbai"],
    "Q_Shanghai": ["Earth", "Asia", "China", "Shanghai"],
    "Q_Sao_Paulo": ["Earth", "South America", "Brazil", "Sao Paulo"],
    "Q_Mexico_City": ["Earth", "North America", "Mexico", "Mexico City"],
    "Q_Cairo": ["Earth", "Africa", "Egypt", "Cairo"],
    "Q_Istanbul": ["Earth", "Europe", "Turkey", "Istanbul"],
    "Q_Vienna": ["Earth", "Europe", "Austria", "Vienna"],
    "Q_Amsterdam": ["Earth", "Europe", "Netherlands", "Amsterdam"],
    "Q_Barcelona": ["Earth", "Europe", "Spain", "Catalonia", "Barcelona"],
    "Q_Madrid": ["Earth", "Europe", "Spain", "Madrid"],
    "Q_Athens": ["Earth", "Europe", "Greece", "Athens"],
    "Q_Jerusalem": ["Earth", "Asia", "Israel", "Jerusalem"],
    "Q_Venice": ["Earth", "Europe", "Italy", "Veneto", "Venice"],
    "Q_Florence": ["Earth", "Europe", "Italy", "Tuscany", "Florence"],
    "Q_Prague": ["Earth", "Europe", "Czech Republic", "Prague"],
    "Q_Stockholm": ["Earth", "Europe", "Sweden", "Stockholm"],
    "Q_Copenhagen": ["Earth", "Europe", "Denmark", "Copenhagen"],

    # Countries
    "Q_France": ["Earth", "Europe", "France"],
    "Q_United_Kingdom": ["Earth", "Europe", "United Kingdom"],
    "Q_United_States": ["Earth", "North America", "United States"],
    "Q_Germany": ["Earth", "Europe", "Germany"],
    "Q_Italy": ["Earth", "Europe", "Italy"],
    "Q_Japan": ["Earth", "Asia", "Japan"],
    "Q_China": ["Earth", "Asia", "China"],
    "Q_India": ["Earth", "Asia", "India"],
    "Q_Russia": ["Earth", "Europe", "Russia"],
    "Q_Brazil": ["Earth", "South America", "Brazil"],
    "Q_Australia": ["Earth", "Oceania", "Australia"],
    "Q_Canada": ["Earth", "North America", "Canada"],
    "Q_Spain": ["Earth", "Europe", "Spain"],
    "Q_Mexico": ["Earth", "North America", "Mexico"],
    "Q_Egypt": ["Earth", "Africa", "Egypt"],
    "Q_Greece": ["Earth", "Europe", "Greece"],
    "Q_Turkey": ["Earth", "Europe", "Turkey"],
    "Q_South_Korea": ["Earth", "Asia", "South Korea"],
    "Q_Netherlands": ["Earth", "Europe", "Netherlands"],
    "Q_Switzerland": ["Earth", "Europe", "Switzerland"],
    "Q_Sweden": ["Earth", "Europe", "Sweden"],
    "Q_Norway": ["Earth", "Europe", "Norway"],
    "Q_Poland": ["Earth", "Europe", "Poland"],
    "Q_Argentina": ["Earth", "South America", "Argentina"],
    "Q_South_Africa": ["Earth", "Africa", "South Africa"],
    "Q_Israel": ["Earth", "Asia", "Israel"],

    # Continents
    "Q_Europe": ["Earth", "Europe"],
    "Q_Asia": ["Earth", "Asia"],
    "Q_North_America": ["Earth", "North America"],
    "Q_South_America": ["Earth", "South America"],
    "Q_Africa": ["Earth", "Africa"],
    "Q_Oceania": ["Earth", "Oceania"],
    "Q_Antarctica": ["Earth", "Antarctica"],

    # Landmarks - Extended
    "Q_Eiffel_Tower": ["Earth", "Europe", "France", "Paris", "Eiffel Tower"],
    "Q_Statue_of_Liberty": ["Earth", "North America", "United States", "New York", "Statue of Liberty"],
    "Q_Great_Wall_of_China": ["Earth", "Asia", "China", "Great Wall of China"],
    "Q_Colosseum": ["Earth", "Europe", "Italy", "Rome", "Colosseum"],
    "Q_Taj_Mahal": ["Earth", "Asia", "India", "Agra", "Taj Mahal"],
    "Q_Big_Ben": ["Earth", "Europe", "United Kingdom", "England", "London", "Big Ben"],
    "Q_Pyramids_of_Giza": ["Earth", "Africa", "Egypt", "Giza", "Pyramids of Giza"],
    "Q_Machu_Picchu": ["Earth", "South America", "Peru", "Machu Picchu"],
    "Q_Petra": ["Earth", "Asia", "Jordan", "Petra"],
    "Q_Christ_the_Redeemer": ["Earth", "South America", "Brazil", "Rio de Janeiro", "Christ the Redeemer"],
    "Q_Acropolis_of_Athens": ["Earth", "Europe", "Greece", "Athens", "Acropolis"],
    "Q_Stonehenge": ["Earth", "Europe", "United Kingdom", "England", "Stonehenge"],
    "Q_Sydney_Opera_House": ["Earth", "Oceania", "Australia", "Sydney", "Sydney Opera House"],
    "Q_Empire_State_Building": ["Earth", "North America", "United States", "New York", "Empire State Building"],
    "Q_Burj_Khalifa": ["Earth", "Asia", "United Arab Emirates", "Dubai", "Burj Khalifa"],
    "Q_Golden_Gate_Bridge": ["Earth", "North America", "United States", "California", "San Francisco", "Golden Gate Bridge"],
    "Q_Tower_of_London": ["Earth", "Europe", "United Kingdom", "England", "London", "Tower of London"],
    "Q_Notre-Dame_de_Paris": ["Earth", "Europe", "France", "Paris", "Notre-Dame"],
    "Q_Louvre": ["Earth", "Europe", "France", "Paris", "Louvre"],
    "Q_Vatican_City": ["Earth", "Europe", "Vatican City"],
    "Q_Sistine_Chapel": ["Earth", "Europe", "Vatican City", "Sistine Chapel"],
    "Q_Leaning_Tower_of_Pisa": ["Earth", "Europe", "Italy", "Tuscany", "Pisa", "Leaning Tower"],

    # Universities
    "Q_Harvard_University": ["Earth", "North America", "United States", "Massachusetts", "Cambridge", "Harvard"],
    "Q_University_of_Cambridge": ["Earth", "Europe", "United Kingdom", "England", "Cambridge", "Cambridge University"],
    "Q_University_of_Oxford": ["Earth", "Europe", "United Kingdom", "England", "Oxford", "Oxford University"],
    "Q_MIT": ["Earth", "North America", "United States", "Massachusetts", "Cambridge", "MIT"],
    "Q_Stanford_University": ["Earth", "North America", "United States", "California", "Stanford"],
    "Q_Yale_University": ["Earth", "North America", "United States", "Connecticut", "New Haven", "Yale"],
    "Q_Princeton_University": ["Earth", "North America", "United States", "New Jersey", "Princeton"],
    "Q_Caltech": ["Earth", "North America", "United States", "California", "Pasadena", "Caltech"],
    "Q_Sorbonne": ["Earth", "Europe", "France", "Paris", "Sorbonne"],
    "Q_University_of_Tokyo": ["Earth", "Asia", "Japan", "Tokyo", "University of Tokyo"],
}

# ============================================================================
# SHOWCASE RELATIONS - Rich set for demos
# ============================================================================

SHOWCASE_RELATIONS = [
    # === SCIENTISTS & DISCOVERIES ===
    # Einstein
    ("Q_Albert_Einstein", "Q_Theory_of_relativity", "created", 1.0),
    ("Q_Albert_Einstein", "Q_General_relativity", "developed", 1.0),
    ("Q_Albert_Einstein", "Q_Special_relativity", "developed", 1.0),
    ("Q_Albert_Einstein", "Q_Nobel_Prize_in_Physics", "awarded", 1.0),
    ("Q_Albert_Einstein", "Q_Germany", "born_in", 1.0),
    ("Q_Albert_Einstein", "Q_United_States", "citizen_of", 1.0),
    ("Q_Albert_Einstein", "Q_Princeton_University", "worked_at", 1.0),

    # Marie Curie
    ("Q_Marie_Curie", "Q_Radioactivity", "discovered", 1.0),
    ("Q_Marie_Curie", "Q_Polonium", "discovered", 1.0),
    ("Q_Marie_Curie", "Q_Radium", "discovered", 1.0),
    ("Q_Marie_Curie", "Q_Nobel_Prize_in_Physics", "awarded", 1.0),
    ("Q_Marie_Curie", "Q_Nobel_Prize_in_Chemistry", "awarded", 1.0),
    ("Q_Marie_Curie", "Q_Pierre_Curie", "spouse_of", 1.0),
    ("Q_Pierre_Curie", "Q_Marie_Curie", "spouse_of", 1.0),
    ("Q_Marie_Curie", "Q_France", "citizen_of", 1.0),
    ("Q_Marie_Curie", "Q_Sorbonne", "worked_at", 1.0),

    # Newton
    ("Q_Isaac_Newton", "Q_Gravity", "discovered", 1.0),
    ("Q_Isaac_Newton", "Q_University_of_Cambridge", "worked_at", 1.0),
    ("Q_Isaac_Newton", "Q_United_Kingdom", "born_in", 1.0),

    # Darwin
    ("Q_Charles_Darwin", "Q_Evolution", "developed", 1.0),
    ("Q_Charles_Darwin", "Q_United_Kingdom", "born_in", 1.0),

    # Other scientists
    ("Q_Galileo_Galilei", "Q_Telescope", "improved", 1.0),
    ("Q_Galileo_Galilei", "Q_Italy", "born_in", 1.0),
    ("Q_Nikola_Tesla", "Q_Electric_motor", "invented", 1.0),
    ("Q_Nikola_Tesla", "Q_United_States", "citizen_of", 1.0),
    ("Q_Alexander_Fleming", "Q_Penicillin", "discovered", 1.0),
    ("Q_Alexander_Fleming", "Q_Nobel_Prize_in_Chemistry", "awarded", 1.0),
    ("Q_Louis_Pasteur", "Q_Vaccine", "developed", 1.0),
    ("Q_Louis_Pasteur", "Q_France", "born_in", 1.0),
    ("Q_Max_Planck", "Q_Quantum_mechanics", "founded", 1.0),
    ("Q_Max_Planck", "Q_Nobel_Prize_in_Physics", "awarded", 1.0),
    ("Q_Niels_Bohr", "Q_Atom", "model_of", 1.0),
    ("Q_Niels_Bohr", "Q_Nobel_Prize_in_Physics", "awarded", 1.0),
    ("Q_Stephen_Hawking", "Q_Black_hole", "studied", 1.0),
    ("Q_Stephen_Hawking", "Q_University_of_Cambridge", "worked_at", 1.0),
    ("Q_Richard_Feynman", "Q_Quantum_mechanics", "contributed_to", 1.0),
    ("Q_Richard_Feynman", "Q_Nobel_Prize_in_Physics", "awarded", 1.0),
    ("Q_Richard_Feynman", "Q_Caltech", "worked_at", 1.0),
    ("Q_Alan_Turing", "Q_Computer", "pioneer_of", 1.0),
    ("Q_Alan_Turing", "Q_Turing_Award", "namesake_of", 1.0),
    ("Q_Alan_Turing", "Q_University_of_Cambridge", "worked_at", 1.0),

    # === INVENTORS ===
    ("Q_Thomas_Edison", "Q_Light_bulb", "invented", 1.0),
    ("Q_Thomas_Edison", "Q_United_States", "born_in", 1.0),
    ("Q_Alexander_Graham_Bell", "Q_Telephone", "invented", 1.0),
    ("Q_Alexander_Graham_Bell", "Q_United_States", "citizen_of", 1.0),
    ("Q_Wright_brothers", "Q_Airplane", "invented", 1.0),
    ("Q_Wright_brothers", "Q_United_States", "born_in", 1.0),
    ("Q_Henry_Ford", "Q_Automobile", "mass_produced", 1.0),
    ("Q_Henry_Ford", "Q_United_States", "born_in", 1.0),
    ("Q_Johannes_Gutenberg", "Q_Printing_press", "invented", 1.0),
    ("Q_Johannes_Gutenberg", "Q_Germany", "born_in", 1.0),
    ("Q_James_Watt", "Q_Steam_engine", "improved", 1.0),
    ("Q_James_Watt", "Q_United_Kingdom", "born_in", 1.0),
    ("Q_Guglielmo_Marconi", "Q_Radio", "invented", 1.0),
    ("Q_Tim_Berners-Lee", "Q_Internet", "invented", 1.0),

    # === ARTISTS ===
    ("Q_Leonardo_da_Vinci", "Q_Mona_Lisa", "created", 1.0),
    ("Q_Leonardo_da_Vinci", "Q_The_Last_Supper", "created", 1.0),
    ("Q_Leonardo_da_Vinci", "Q_Italy", "born_in", 1.0),
    ("Q_Michelangelo", "Q_David_(Michelangelo)", "created", 1.0),
    ("Q_Michelangelo", "Q_Sistine_Chapel", "painted", 1.0),
    ("Q_Michelangelo", "Q_Italy", "born_in", 1.0),
    ("Q_Vincent_van_Gogh", "Q_The_Starry_Night", "created", 1.0),
    ("Q_Vincent_van_Gogh", "Q_Netherlands", "born_in", 1.0),
    ("Q_Pablo_Picasso", "Q_Guernica", "created", 1.0),
    ("Q_Pablo_Picasso", "Q_Spain", "born_in", 1.0),
    ("Q_Claude_Monet", "Q_France", "born_in", 1.0),
    ("Q_Salvador_Dali", "Q_Spain", "born_in", 1.0),
    ("Q_Frida_Kahlo", "Q_Mexico", "born_in", 1.0),
    ("Q_Rembrandt", "Q_Netherlands", "born_in", 1.0),

    # === COMPOSERS ===
    ("Q_Ludwig_van_Beethoven", "Q_Symphony_No._9_(Beethoven)", "composed", 1.0),
    ("Q_Ludwig_van_Beethoven", "Q_Germany", "born_in", 1.0),
    ("Q_Wolfgang_Amadeus_Mozart", "Q_Austria", "born_in", 1.0),
    ("Q_Johann_Sebastian_Bach", "Q_Germany", "born_in", 1.0),
    ("Q_Frederic_Chopin", "Q_Poland", "born_in", 1.0),
    ("Q_Giuseppe_Verdi", "Q_Italy", "born_in", 1.0),
    ("Q_Richard_Wagner", "Q_Germany", "born_in", 1.0),

    # === WRITERS ===
    ("Q_William_Shakespeare", "Q_Hamlet", "wrote", 1.0),
    ("Q_William_Shakespeare", "Q_Romeo_and_Juliet", "wrote", 1.0),
    ("Q_William_Shakespeare", "Q_Macbeth", "wrote", 1.0),
    ("Q_William_Shakespeare", "Q_Othello", "wrote", 1.0),
    ("Q_William_Shakespeare", "Q_King_Lear", "wrote", 1.0),
    ("Q_William_Shakespeare", "Q_A_Midsummer_Nights_Dream", "wrote", 1.0),
    ("Q_William_Shakespeare", "Q_The_Tempest", "wrote", 1.0),
    ("Q_William_Shakespeare", "Q_United_Kingdom", "born_in", 1.0),
    ("Q_Miguel_de_Cervantes", "Q_Don_Quixote", "wrote", 1.0),
    ("Q_Miguel_de_Cervantes", "Q_Spain", "born_in", 1.0),
    ("Q_Leo_Tolstoy", "Q_War_and_Peace", "wrote", 1.0),
    ("Q_Leo_Tolstoy", "Q_Russia", "born_in", 1.0),
    ("Q_Fyodor_Dostoevsky", "Q_Crime_and_Punishment", "wrote", 1.0),
    ("Q_Fyodor_Dostoevsky", "Q_Russia", "born_in", 1.0),
    ("Q_Jane_Austen", "Q_Pride_and_Prejudice", "wrote", 1.0),
    ("Q_Jane_Austen", "Q_United_Kingdom", "born_in", 1.0),
    ("Q_Charles_Dickens", "Q_United_Kingdom", "born_in", 1.0),
    ("Q_Mark_Twain", "Q_United_States", "born_in", 1.0),
    ("Q_Ernest_Hemingway", "Q_United_States", "born_in", 1.0),
    ("Q_Ernest_Hemingway", "Q_Nobel_Prize_in_Literature", "awarded", 1.0),
    ("Q_Homer", "Q_The_Odyssey", "wrote", 1.0),
    ("Q_Homer", "Q_The_Iliad", "wrote", 1.0),
    ("Q_Dante_Alighieri", "Q_The_Divine_Comedy", "wrote", 1.0),
    ("Q_Dante_Alighieri", "Q_Italy", "born_in", 1.0),

    # === HISTORICAL FIGURES ===
    ("Q_Napoleon", "Q_France", "leader_of", 1.0),
    ("Q_Napoleon", "Q_France", "born_in", 1.0),
    ("Q_Julius_Caesar", "Q_Rome", "leader_of", 1.0),
    ("Q_Julius_Caesar", "Q_Roman_Empire", "leader_of", 1.0),
    ("Q_Alexander_the_Great", "Q_Greece", "born_in", 1.0),
    ("Q_Cleopatra", "Q_Egypt", "leader_of", 1.0),
    ("Q_Abraham_Lincoln", "Q_United_States", "leader_of", 1.0),
    ("Q_George_Washington", "Q_United_States", "leader_of", 1.0),
    ("Q_George_Washington", "Q_American_Revolution", "led", 1.0),
    ("Q_Winston_Churchill", "Q_United_Kingdom", "leader_of", 1.0),
    ("Q_Winston_Churchill", "Q_World_War_II", "led_during", 1.0),
    ("Q_Winston_Churchill", "Q_Nobel_Prize_in_Literature", "awarded", 1.0),
    ("Q_Mahatma_Gandhi", "Q_India", "leader_of", 1.0),
    ("Q_Nelson_Mandela", "Q_South_Africa", "leader_of", 1.0),
    ("Q_Nelson_Mandela", "Q_Nobel_Peace_Prize", "awarded", 1.0),
    ("Q_Martin_Luther_King_Jr.", "Q_United_States", "born_in", 1.0),
    ("Q_Martin_Luther_King_Jr.", "Q_Nobel_Peace_Prize", "awarded", 1.0),
    ("Q_Queen_Victoria", "Q_United_Kingdom", "leader_of", 1.0),
    ("Q_Queen_Elizabeth_II", "Q_United_Kingdom", "leader_of", 1.0),
    ("Q_Genghis_Khan", "Q_Asia", "conquered", 1.0),
    ("Q_Charlemagne", "Q_Europe", "leader_of", 1.0),
    ("Q_Joan_of_Arc", "Q_France", "fought_for", 1.0),

    # === TECH FIGURES ===
    ("Q_Steve_Jobs", "Q_Apple_Inc.", "founded", 1.0),
    ("Q_Steve_Jobs", "Q_United_States", "born_in", 1.0),
    ("Q_Bill_Gates", "Q_Microsoft", "founded", 1.0),
    ("Q_Bill_Gates", "Q_United_States", "born_in", 1.0),
    ("Q_Elon_Musk", "Q_United_States", "citizen_of", 1.0),
    ("Q_Mark_Zuckerberg", "Q_Facebook", "founded", 1.0),
    ("Q_Jeff_Bezos", "Q_Amazon", "founded", 1.0),
    ("Q_Linus_Torvalds", "Q_Computer", "contributed_to", 1.0),

    # === LANDMARKS -> LOCATIONS ===
    ("Q_Eiffel_Tower", "Q_Paris", "located_in", 1.0),
    ("Q_Eiffel_Tower", "Q_France", "located_in", 1.0),
    ("Q_Statue_of_Liberty", "Q_New_York_City", "located_in", 1.0),
    ("Q_Statue_of_Liberty", "Q_United_States", "located_in", 1.0),
    ("Q_Colosseum", "Q_Rome", "located_in", 1.0),
    ("Q_Colosseum", "Q_Italy", "located_in", 1.0),
    ("Q_Great_Wall_of_China", "Q_China", "located_in", 1.0),
    ("Q_Taj_Mahal", "Q_India", "located_in", 1.0),
    ("Q_Big_Ben", "Q_London", "located_in", 1.0),
    ("Q_Big_Ben", "Q_United_Kingdom", "located_in", 1.0),
    ("Q_Pyramids_of_Giza", "Q_Egypt", "located_in", 1.0),
    ("Q_Machu_Picchu", "Q_Peru", "located_in", 1.0),
    ("Q_Petra", "Q_Jordan", "located_in", 1.0),
    ("Q_Christ_the_Redeemer", "Q_Brazil", "located_in", 1.0),
    ("Q_Acropolis_of_Athens", "Q_Greece", "located_in", 1.0),
    ("Q_Stonehenge", "Q_United_Kingdom", "located_in", 1.0),
    ("Q_Sydney_Opera_House", "Q_Australia", "located_in", 1.0),
    ("Q_Empire_State_Building", "Q_New_York_City", "located_in", 1.0),
    ("Q_Burj_Khalifa", "Q_Dubai", "located_in", 1.0),
    ("Q_Golden_Gate_Bridge", "Q_United_States", "located_in", 1.0),
    ("Q_Tower_of_London", "Q_London", "located_in", 1.0),
    ("Q_Notre-Dame_de_Paris", "Q_Paris", "located_in", 1.0),
    ("Q_Louvre", "Q_Paris", "located_in", 1.0),
    ("Q_Sistine_Chapel", "Q_Vatican_City", "located_in", 1.0),
    ("Q_Leaning_Tower_of_Pisa", "Q_Italy", "located_in", 1.0),

    # === ARTWORKS -> LOCATIONS ===
    ("Q_Mona_Lisa", "Q_Louvre", "displayed_in", 1.0),
    ("Q_Mona_Lisa", "Q_Paris", "located_in", 1.0),

    # === CAPITALS ===
    ("Q_Paris", "Q_France", "capital_of", 1.0),
    ("Q_London", "Q_United_Kingdom", "capital_of", 1.0),
    ("Q_Berlin", "Q_Germany", "capital_of", 1.0),
    ("Q_Rome", "Q_Italy", "capital_of", 1.0),
    ("Q_Tokyo", "Q_Japan", "capital_of", 1.0),
    ("Q_Beijing", "Q_China", "capital_of", 1.0),
    ("Q_Moscow", "Q_Russia", "capital_of", 1.0),
    ("Q_Madrid", "Q_Spain", "capital_of", 1.0),
    ("Q_Athens", "Q_Greece", "capital_of", 1.0),
    ("Q_Cairo", "Q_Egypt", "capital_of", 1.0),
    ("Q_Vienna", "Q_Austria", "capital_of", 1.0),
    ("Q_Amsterdam", "Q_Netherlands", "capital_of", 1.0),
    ("Q_Stockholm", "Q_Sweden", "capital_of", 1.0),
    ("Q_Copenhagen", "Q_Denmark", "capital_of", 1.0),

    # === CITIES IN COUNTRIES ===
    ("Q_Paris", "Q_France", "located_in", 1.0),
    ("Q_London", "Q_United_Kingdom", "located_in", 1.0),
    ("Q_New_York_City", "Q_United_States", "located_in", 1.0),
    ("Q_Los_Angeles", "Q_United_States", "located_in", 1.0),
    ("Q_Tokyo", "Q_Japan", "located_in", 1.0),
    ("Q_Rome", "Q_Italy", "located_in", 1.0),
    ("Q_Berlin", "Q_Germany", "located_in", 1.0),
    ("Q_Beijing", "Q_China", "located_in", 1.0),
    ("Q_Moscow", "Q_Russia", "located_in", 1.0),
    ("Q_Sydney", "Q_Australia", "located_in", 1.0),
    ("Q_Hong_Kong", "Q_China", "located_in", 1.0),
    ("Q_Shanghai", "Q_China", "located_in", 1.0),
    ("Q_Mumbai", "Q_India", "located_in", 1.0),
    ("Q_Sao_Paulo", "Q_Brazil", "located_in", 1.0),
    ("Q_Mexico_City", "Q_Mexico", "located_in", 1.0),
    ("Q_Cairo", "Q_Egypt", "located_in", 1.0),
    ("Q_Istanbul", "Q_Turkey", "located_in", 1.0),
    ("Q_Barcelona", "Q_Spain", "located_in", 1.0),
    ("Q_Madrid", "Q_Spain", "located_in", 1.0),
    ("Q_Venice", "Q_Italy", "located_in", 1.0),
    ("Q_Florence", "Q_Italy", "located_in", 1.0),

    # === COUNTRIES IN CONTINENTS ===
    ("Q_France", "Q_Europe", "located_in", 1.0),
    ("Q_Germany", "Q_Europe", "located_in", 1.0),
    ("Q_Italy", "Q_Europe", "located_in", 1.0),
    ("Q_Spain", "Q_Europe", "located_in", 1.0),
    ("Q_United_Kingdom", "Q_Europe", "located_in", 1.0),
    ("Q_Japan", "Q_Asia", "located_in", 1.0),
    ("Q_China", "Q_Asia", "located_in", 1.0),
    ("Q_India", "Q_Asia", "located_in", 1.0),
    ("Q_United_States", "Q_North_America", "located_in", 1.0),
    ("Q_Canada", "Q_North_America", "located_in", 1.0),
    ("Q_Mexico", "Q_North_America", "located_in", 1.0),
    ("Q_Brazil", "Q_South_America", "located_in", 1.0),
    ("Q_Argentina", "Q_South_America", "located_in", 1.0),
    ("Q_Egypt", "Q_Africa", "located_in", 1.0),
    ("Q_South_Africa", "Q_Africa", "located_in", 1.0),
    ("Q_Australia", "Q_Oceania", "located_in", 1.0),

    # === UNIVERSITIES ===
    ("Q_Harvard_University", "Q_United_States", "located_in", 1.0),
    ("Q_University_of_Cambridge", "Q_United_Kingdom", "located_in", 1.0),
    ("Q_University_of_Oxford", "Q_United_Kingdom", "located_in", 1.0),
    ("Q_MIT", "Q_United_States", "located_in", 1.0),
    ("Q_Stanford_University", "Q_United_States", "located_in", 1.0),
    ("Q_Yale_University", "Q_United_States", "located_in", 1.0),
    ("Q_Princeton_University", "Q_United_States", "located_in", 1.0),
    ("Q_Caltech", "Q_United_States", "located_in", 1.0),
    ("Q_Sorbonne", "Q_France", "located_in", 1.0),
    ("Q_University_of_Tokyo", "Q_Japan", "located_in", 1.0),

    # === COMPANIES ===
    ("Q_Apple_Inc.", "Q_United_States", "headquartered_in", 1.0),
    ("Q_Google", "Q_United_States", "headquartered_in", 1.0),
    ("Q_Microsoft", "Q_United_States", "headquartered_in", 1.0),
    ("Q_Amazon", "Q_United_States", "headquartered_in", 1.0),
    ("Q_Facebook", "Q_United_States", "headquartered_in", 1.0),

    # === ORGANIZATIONS ===
    ("Q_NASA", "Q_United_States", "located_in", 1.0),
    ("Q_NASA", "Q_Moon_landing", "achieved", 1.0),
    ("Q_International_Space_Station", "Q_Earth", "orbits", 1.0),

    # === EVENTS ===
    ("Q_World_War_I", "Q_Europe", "occurred_in", 1.0),
    ("Q_World_War_II", "Q_Europe", "occurred_in", 1.0),
    ("Q_French_Revolution", "Q_France", "occurred_in", 1.0),
    ("Q_American_Revolution", "Q_United_States", "occurred_in", 1.0),
    ("Q_Russian_Revolution", "Q_Russia", "occurred_in", 1.0),
    ("Q_Industrial_Revolution", "Q_United_Kingdom", "started_in", 1.0),
    ("Q_Renaissance", "Q_Italy", "started_in", 1.0),
    ("Q_Moon_landing", "Q_Moon", "occurred_on", 1.0),
    ("Q_Moon_landing", "Q_United_States", "achieved_by", 1.0),

    # === PHILOSOPHERS ===
    ("Q_Aristotle", "Q_Greece", "born_in", 1.0),
    ("Q_Plato", "Q_Greece", "born_in", 1.0),
    ("Q_Socrates", "Q_Greece", "born_in", 1.0),
    ("Q_Confucius", "Q_China", "born_in", 1.0),
]

# Relation normalization
RELATION_NORMALIZATION = {
    "AtLocation": "located_in",
    "PartOf": "part_of",
    "IsA": "instance_of",
    "CapableOf": "can",
    "UsedFor": "used_for",
    "HasProperty": "has_property",
    "DerivedFrom": "derived_from",
    "RelatedTo": "related_to",
    "SimilarTo": "similar_to",
    "FieldOf": "field_of",
}


def main():
    if not SOURCE_DB.exists():
        print(f"Source DB not found: {SOURCE_DB}")
        return

    OUTPUT_DB.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_DB.exists():
        OUTPUT_DB.unlink()

    # Create new database
    conn = sqlite3.connect(OUTPUT_DB)
    conn.row_factory = sqlite3.Row

    # Create schema
    conn.executescript("""
        CREATE TABLE entities (
            id TEXT PRIMARY KEY,
            wikipedia_title TEXT,
            label TEXT NOT NULL,
            description TEXT,
            vital_level INTEGER,
            pagerank REAL
        );

        CREATE TABLE dimension_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            entity_id TEXT NOT NULL,
            dimension TEXT NOT NULL,
            path_sign INTEGER NOT NULL,
            path_depth INTEGER NOT NULL,
            path_nodes TEXT NOT NULL,
            zero_state TEXT NOT NULL
        );

        CREATE TABLE epa_values (
            entity_id TEXT PRIMARY KEY,
            evaluation INTEGER NOT NULL DEFAULT 0,
            potency INTEGER NOT NULL DEFAULT 0,
            activity INTEGER NOT NULL DEFAULT 0,
            confidence REAL DEFAULT 1.0
        );

        CREATE TABLE properties (
            entity_id TEXT NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            PRIMARY KEY (entity_id, key)
        );

        CREATE TABLE entity_links (
            source_id TEXT NOT NULL,
            target_id TEXT NOT NULL,
            relation TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            UNIQUE(source_id, target_id, relation)
        );

        CREATE INDEX idx_entities_label ON entities(label);
        CREATE INDEX idx_entities_label_lower ON entities(LOWER(label));
        CREATE INDEX idx_dim_pos_entity ON dimension_positions(entity_id);
        CREATE INDEX idx_links_source ON entity_links(source_id);
        CREATE INDEX idx_links_target ON entity_links(target_id);
    """)

    # Connect to source
    src = sqlite3.connect(SOURCE_DB)
    src.row_factory = sqlite3.Row

    # Get entities: vital 1-3 + showcase entities
    showcase_sql = ", ".join(f"'{e}'" for e in SHOWCASE_ENTITIES)
    entities = src.execute(f"""
        SELECT * FROM entities
        WHERE (vital_level IS NOT NULL AND vital_level <= 3)
        OR id IN ({showcase_sql})
    """).fetchall()

    # Filter out wiki markup junk
    valid_entities = []
    for e in entities:
        label = e["label"] or ""
        if "[[" in label or "{{" in label or "==" in label or "|" in label:
            continue
        valid_entities.append(e)

    entity_ids = {e["id"] for e in valid_entities}

    print(f"Copying {len(valid_entities)} entities...")

    # Copy entities
    for e in valid_entities:
        conn.execute("""
            INSERT INTO entities (id, wikipedia_title, label, description, vital_level, pagerank)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (e["id"], e["wikipedia_title"], e["label"], e["description"], e["vital_level"], e["pagerank"]))

    # Copy dimension positions
    print("Copying dimension positions...")
    for e_id in entity_ids:
        positions = src.execute("SELECT * FROM dimension_positions WHERE entity_id = ?", (e_id,)).fetchall()
        for p in positions:
            conn.execute("""
                INSERT INTO dimension_positions (entity_id, dimension, path_sign, path_depth, path_nodes, zero_state)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (p["entity_id"], p["dimension"], p["path_sign"], p["path_depth"], p["path_nodes"], p["zero_state"]))

    # Copy EPA values
    print("Copying EPA values...")
    for e_id in entity_ids:
        epa = src.execute("SELECT * FROM epa_values WHERE entity_id = ?", (e_id,)).fetchone()
        if epa:
            conn.execute("""
                INSERT INTO epa_values (entity_id, evaluation, potency, activity, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (epa["entity_id"], epa["evaluation"], epa["potency"], epa["activity"], epa["confidence"]))

    # Copy properties
    print("Copying properties...")
    for e_id in entity_ids:
        props = src.execute("SELECT * FROM properties WHERE entity_id = ?", (e_id,)).fetchall()
        for p in props:
            conn.execute("""
                INSERT OR IGNORE INTO properties (entity_id, key, value)
                VALUES (?, ?, ?)
            """, (p["entity_id"], p["key"], p["value"]))

    # Copy and normalize entity links
    print("Copying entity links...")
    links = src.execute("SELECT source_id, target_id, relation, weight FROM entity_links").fetchall()

    for link in links:
        if link["source_id"] in entity_ids and link["target_id"] in entity_ids:
            relation = RELATION_NORMALIZATION.get(link["relation"], link["relation"])
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO entity_links (source_id, target_id, relation, weight)
                    VALUES (?, ?, ?, ?)
                """, (link["source_id"], link["target_id"], relation, link["weight"]))
            except:
                pass

    src.close()

    # Add SPATIAL positions
    print("Adding SPATIAL dimension positions...")
    for entity_id, path in SPATIAL_DATA.items():
        if entity_id not in entity_ids:
            continue

        # Check if already has SPATIAL
        has_spatial = conn.execute(
            "SELECT 1 FROM dimension_positions WHERE entity_id = ? AND dimension = 'SPATIAL'",
            (entity_id,)
        ).fetchone()

        if not has_spatial:
            conn.execute("""
                INSERT INTO dimension_positions (entity_id, dimension, path_sign, path_depth, path_nodes, zero_state)
                VALUES (?, 'SPATIAL', 1, ?, ?, 'Earth')
            """, (entity_id, len(path) - 1, json.dumps(path)))

    # Add showcase relations
    print("Adding showcase relations...")
    for source, target, relation, weight in SHOWCASE_RELATIONS:
        if source in entity_ids and target in entity_ids:
            try:
                conn.execute("""
                    INSERT OR IGNORE INTO entity_links (source_id, target_id, relation, weight)
                    VALUES (?, ?, ?, ?)
                """, (source, target, relation, weight))
            except:
                pass

    conn.commit()

    # Vacuum to optimize
    print("Optimizing database...")
    conn.execute("VACUUM")
    conn.commit()

    # Stats
    stats = {
        'entities': conn.execute("SELECT COUNT(*) FROM entities").fetchone()[0],
        'positions': conn.execute("SELECT COUNT(*) FROM dimension_positions").fetchone()[0],
        'spatial': conn.execute("SELECT COUNT(*) FROM dimension_positions WHERE dimension = 'SPATIAL'").fetchone()[0],
        'epa': conn.execute("SELECT COUNT(*) FROM epa_values").fetchone()[0],
        'links': conn.execute("SELECT COUNT(*) FROM entity_links").fetchone()[0],
        'unique_relations': conn.execute("SELECT COUNT(DISTINCT relation) FROM entity_links").fetchone()[0],
    }

    conn.close()
    size_mb = OUTPUT_DB.stat().st_size / 1024 / 1024

    print()
    print("=" * 50)
    print(f"Created {OUTPUT_DB}")
    print("=" * 50)
    print(f"  Entities:         {stats['entities']:,}")
    print(f"  Dim Positions:    {stats['positions']:,}")
    print(f"  SPATIAL:          {stats['spatial']:,}")
    print(f"  EPA values:       {stats['epa']:,}")
    print(f"  Entity links:     {stats['links']:,}")
    print(f"  Relation types:   {stats['unique_relations']}")
    print(f"  Size:             {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
