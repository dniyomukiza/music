import re
import json
from docx import Document

# Function to process the text
def process_text(data):
    # Split data into lines
    lines = data.split('\n')
    
    result = {}

    # Process each line
    for line in lines:
        # Match an uppercase word at the beginning of the line followed by a space, hyphen, or comma
        match = re.match(r'^-([A-ZÁ-Ú]+)[\s,|-]*(\S+)', line.strip())
        
        if match:
            first_word = match.group(1)  # The uppercase word at the beginning
            second_word = match.group(2)  # The next word after the uppercase word
            
            # Clean the second word by removing hyphens and commas
            second_word = re.sub(r'[-,]', '', second_word)
            
            # Default values for "meaning"
            meaning_1 = "None"
            meaning_2 = "None"
            
            # Check if the line contains a dot and process accordingly
            if '.' in line:
                # After the second word, find text up to the first dot
                parts = line.split(second_word, 1)[1] if second_word in line else ""  # Everything after the second word
                if parts:
                    first_meaning = parts.split('.', 1)[0].strip() if '.' in parts else ""  # Text up to the first dot
                    meaning_1 = first_meaning
                    
                    # If there are two dots, get text between the dots
                    if parts.count('.') > 1:
                        try:
                            second_meaning = parts.split('.', 2)[1].split('.', 1)[0].strip()
                            meaning_2 = second_meaning
                        except IndexError:
                            meaning_2 = "None"  # Handle case where the second dot is not followed by text
                else:
                    meaning_1 = "None"
                    meaning_2 = "None"
            
            # Concatenate the second word to the first word, and convert the entire result to lowercase
            concatenated_word = (second_word[:-2] + first_word).lower()

            # Store the result in the dictionary
            result[concatenated_word] = {
                "umuzi/root": first_word,
                "basoma/phonetics": {
                    " ": concatenated_word,
                },
                "bandika/writing": concatenated_word,
                "icyiciro/pos": ["noun", "izina"],
                "igisobanuro/meaning": [
                    meaning_1,
                    meaning_2,
                    "None"
                ]
            }
    
    # Use ensure_ascii=False to keep accented characters in their original form
    return json.dumps(result, indent=4, ensure_ascii=False)

# Function to extract text from a .docx file
def extract_text_from_docx(docx_path):
    document = Document(docx_path)
    full_text = []
    for para in document.paragraphs:
        full_text.append(para.text)
    return '\n'.join(full_text)

# Function to write the result into a new .docx file
def write_to_docx(json_data, output_path):
    document = Document()
    document.add_paragraph(json_data)
    document.save(output_path)

# Path to the .docx file
docx_path = '/Users/nididier/Downloads/cleanv2.docx'

# Extract text from the .docx file
data = extract_text_from_docx(docx_path)

# Process the text and get the result as JSON
result_json = process_text(data)

# Path to save the output .docx file
output_docx_path = './out.docx'

# Write the result to a new .docx file
write_to_docx(result_json, output_docx_path)

print(f"Output saved to {output_docx_path}")
