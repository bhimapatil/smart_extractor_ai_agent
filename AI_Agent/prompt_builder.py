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


def static_feild_extrctor():
    prompt= """
    ### Extract key information from the document image. Identify document type, key details, and any significant data.
        The output format should be in JSON.
        Extract the following fields from the document image:
        - invoice_number: The unique identifier for the invoice.
        - invoice_date: The date of the invoice.
        - company_name: The name of the company issuing the invoice.
        - invoice_total: The total amount mentioned on the invoice.
        - company_address: The address of the company.
        - company_phone: The phone number of the company.
        - company_email: The email address of the company.
        - company_website: The website of the company.
        - item: The item name.
        - quantity: The quantity of the item.
        - price: The price of the item.
        - total: The total price for the item.
        - tax: The tax amount.
        - discount: The discount amount.
        - grand_total: The grand total amount.
        - due_date: The due date for payment.
        - payment_terms: The payment terms mentioned on the invoice.
        - notes: Any additional notes or comments.   
        - If any of the fields are not present or unclear, mark them as `null`.
        
       ### Ensure the extracted information is structured as a JSON object like this:
        ```json
        {
          "invoice_number": "12345",
          "invoice_date": "2024-07-01",
          "invoice_total": "1000.00",
          "company_name": "XYZ Corporation",
          "company_address": "123 Business Rd, City, Country",
          "company_phone": "+1234567890",
          "company_email": "contact@xyzcorporation.com",
          "company_website": "https://www.xyzcorporation.com"
        }"""
    return prompt
