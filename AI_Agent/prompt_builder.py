from API.utility import ColumnRelation


def build_prompt(table_name: str, columns: dict, input_text: str, related_columns: dict = None) -> str:
    # Dynamically construct the column details from the `columns` dictionary
    column_info = ",\n".join([
        # Check if the column is of type ColumnRelation
        f'"{col}": "<{col}_value>", "reference_table": "{col_info.reference_table}", "on_column_name": "{col_info.on_column_name}"'
        if isinstance(col_info, ColumnRelation)
        else f'"{col}": "<{col}_value>"'  # Otherwise, treat as a simple string type
        for col, col_info in columns.items()
    ])

    # Include related columns in the prompt if they exist
    related_info = ""
    if related_columns:
        related_info = "\n### Related Columns (for linked data):\n" + "\n".join(
            [f'Column "{col}" is related to the table "{related}"' for col, related in related_columns.items()]
        )

    # Format the entire prompt with inclusion of related data
    prompt = f"""
        ## Instructions:
        You are an intelligent data extractor. Your task is to extract the following details 
        from the given input text and format them as structured data. Ensure that:
        - All values match the specified data types.
        - Handle ambiguities by making the best possible assumption and noting it.
        - If a value is missing, return 'NULL' or 'N/A' for that field.
        - If there is any irrelevant information, ignore it.
        - If exact matches are not found, make logical assumptions based on the input context.
        - If the input contains multiple entries (e.g., multiple items), split them into separate 
          entries in the `data` array, each containing the relevant details.
        - If the input text contains numbers mentioned with abbreviations like 'k,' 'm,' or 'b' (e.g., 50k), convert them to their full numerical values (e.g., 50,000). 
        - If numbers like invoice number, item numner etc conatains special characters like #, $ etc, remove them before extracting the number.

        ### Details to extract (column name and data type):
        {table_name}
        {column_info}

        {related_info}

        ### Input Text:
        {input_text}

        ### Output Requirements:
        - Return the output as a JSON object.
        - If the input includes multiple entities (e.g., multiple items), the `data` array should 
          include one object per entity, each with its own extracted values.
        - Ensure the format is consistent and adheres to the schema provided.
        - Provide a brief explanation for any assumptions made during extraction.
        - Do not include anything extra outside the JSON output. No need to explain anything, just JSON is enough.

        ### Output Format:
        {{
          "table_name": "{table_name}", 
          "data": [
            {{
              {column_info}
            }}
          ]
        }}

        ### Example for multiple entities:
        For input like "Item1: 2 units at $10, Item2: 3 units at $15", the output should look like:
        {{

          "table_name": "{table_name}",
          "data": [
            {{
              "item_name": "Item1",
              "quantity": 2,
              "price": 10,
              "related_data": {{
                "category": "Beverages",
                "manufacturer": "BrandX"
              }}
            }},
            {{
              "item_name": "Item2",
              "quantity": 3,
              "price": 15,
              "related_data": {{
                "category": "Beverages",
                "manufacturer": "BrandY"
              }}
            }}
          ]
        }}
    """
    return prompt



def text_extractor_prompt_builder():
    prompt = '''
    ## Instructions:
    You are a highly accurate text extractor for images. Your task:
    - Extract text exactly as it appears, removing special characters (e.g., #, $) from numbers like invoice or item numbers.
    - Avoid including extra text or explanations—output only the extracted text.
    - Handle noisy or scanned documents carefully, extracting relevant text only.
    '''

    return prompt


def static_field_extractor():
    prompt = """
You are a precise document parser. Extract information from the provided document image and return ONLY a JSON object with no additional text, explanations, or markdown formatting.

REQUIRED FORMAT:
{
    "metadata": {
        "document_type": string,  // e.g., "invoice", "receipt", "quote", null
        "confidence_score": float // 0.0 to 1.0, indicating extraction confidence
    },
    "invoice_details": {
        "invoice_number": string | null,
        "invoice_date": string | null,  // ISO 8601 format (YYYY-MM-DD)
        "due_date": string | null,      // ISO 8601 format (YYYY-MM-DD)
        "payment_terms": string | null,
        "po_number": string | null
    },
    "amounts": {
        "subtotal": number | null,
        "tax": number | null,
        "discount": number | null,
        "shipping": number | null,
        "total": number | null         // Always use decimal format (e.g., 1234.56)
    },
    "company": {
        "name": string | null,
        "address": {
            "street": string | null,
            "city": string | null,
            "state": string | null,
            "postal_code": string | null,
            "country": string | null
        },
        "contact": {
            "phone": string | null,
            "email": string | null,
            "website": string | null
        },
        "tax_id": string | null
    },
    "line_items": [
        {
            "item": string | null,
            "description": string | null,
            "quantity": number | null,
            "unit_price": number | null,
            "total": number | null
        }
    ],
    "notes": string | null,
    "payment_info": {
        "payment_method": string | null,
        "bank_account": string | null,
        "routing_number": string | null
    }
}

RULES:
1. Return ONLY valid JSON - no explanations or additional text
2. Use null for missing or unclear fields, never empty strings or 0
3. Normalize all currency values to numbers without symbols (e.g., 1234.56 not $1,234.56)
4. Use ISO 8601 (YYYY-MM-DD) for all dates
5. Include confidence_score to indicate overall extraction quality
6. Array fields (like line_items) should be empty array [] if no items found
7. Standardize phone numbers to E.164 format when possible (+[country][number])
8. Convert all websites to lowercase and include http(s)://
9. Remove any trailing/leading whitespace from string values
10. Sanitize all extracted text to remove special characters

IMPORTANT: Provide ONLY the JSON output. Any explanatory text or non-JSON content will break the parsing."""

    return prompt
