import pdfplumber
import pandas as pd
from fastapi import UploadFile

def extract_text_from_pdf(file: UploadFile):
    text = ""
    with pdfplumber.open(file.file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text.strip()

def extract_text_from_excel(file: UploadFile):
    df = pd.read_excel(file.file)
    return df.to_string()

