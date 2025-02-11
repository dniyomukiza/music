import json
import re
from docx import Document

def process_docx(file_path):
    # Load the document
    doc = Document(file_path)
    
    # Initialize result dictionary
    result = {}

    for para in doc.paragraphs:
        line = para.text.strip()
        
        if line.startswith('-'):
            # Remove the dash and split the line
            words = re.split(r'[,\s]\s*', line[1:].strip(), maxsplit=2)

            if len(words) < 3:
                continue  # Skip invalid lines

            root_word = words[0].lower()
            second_word = words[1].lower()
            full_word = second_word + root_word
            description = words[2]

            # Check for the second sentence in the description
            meanings = description.split('. ')
            first_meaning = meanings[0].strip()
            second_meaning = meanings[1].strip() if len(meanings) > 1 else ""

            # Structure the extracted data
            result[full_word] = {
                "umuzi/root": root_word,
                "basoma/phonetics": {
                    "default": "NA",
                    "mu buke/singular": full_word,
                    "mu bwinshi/plural": "NA"
                },
                "bandika/writing": full_word,
                "icyiciro/pos": [
                    "noun",
                    "izina"
                ],
                "igisobanuro/meaning": [
                    first_meaning,
                    second_meaning
                ]
            }

    # Convert the dictionary to JSON and return
    return json.dumps(result, indent=4, ensure_ascii=False)

# Example usage
file_path = "/Users/nididier/Desktop/music/api/kinya/clean.docx"  
json_output = process_docx(file_path)

# Save to a JSON file
with open("output.json", "w", encoding="utf-8") as f:
    f.write(json_output)

print("JSON output saved to output.json")
