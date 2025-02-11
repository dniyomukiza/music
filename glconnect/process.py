import json
import re
from docx import Document

def process_line(line):
    """Process a single line and extract the necessary values."""
    words = re.split(r'[\s,;:\-]+', line.strip())
    
    if len(words) < 2:
        return None  # Skip lines that don't have enough words.

    first_word = words[0].lower()
    second_word = words[1][:-2] if len(words[1]) > 2 else words[1]
    third_word = second_word + first_word
    third_word_no_duplicates = re.sub(r'(\w)\1+', r'\1', third_word)

    remaining_words = words[2:]
    fourth_word = " ".join(remaining_words)
    
    if "." in fourth_word:
        fifth_word = fourth_word.split('.', 1)[1].strip()
        fourth_word = fourth_word.split('.', 1)[0].strip()
    else:
        fifth_word = "NA"

    return {
        "first_word": first_word,
        "second_word": second_word,
        "third_word": third_word,
        "third_word_no_duplicates": third_word_no_duplicates,
        "fourth_word": fourth_word,
        "fifth_word": fifth_word
    }

def process_docx(file_path):
    """Process the .docx file and generate the JSON output."""
    doc = Document(file_path)
    output_data = {}

    for paragraph in doc.paragraphs:
        if paragraph.text.startswith("-"):
            result = process_line(paragraph.text[1:].strip())  # Remove leading dash
            if result:
                key = result["third_word"]
                output_data[key] = {
                    "umuzi/root": result["first_word"],
                    "basoma/phonetics": {
                        " ": "NA",
                        "mu buke/singular": "NA",
                        "mu bwinshi/plural": "NA"
                    },
                    "bandika/writing": result["third_word_no_duplicates"],
                    "icyiciro/pos": ["noun", "izina"],
                    "igisobanuro/meaning": [
                        [result["fourth_word"]],
                        [result["fifth_word"]]
                    ]
                }

    return output_data

# Specify the file path of the .docx document
input_file_path = "~/Desktop/clean.docx"
output_file_path = "~/Desktop/output.json"

# Process the document and save the output
output = process_docx(input_file_path)

with open(output_file_path, "w", encoding="utf-8") as json_file:
    json.dump(output, json_file, ensure_ascii=False, indent=4)

print(f"JSON data has been written to {output_file_path}")

