// Function to dynamically add column fields
const addColumn = () => {
  const columnList = document.getElementById('columns-list');
  const columnDiv = document.createElement('div');
  columnDiv.className = 'column';

  // Create input for column name
  const columnInput = document.createElement('input');
  columnInput.type = 'text';
  columnInput.placeholder = 'Column Name';
  columnInput.className = 'column-name-input';

  // Create select for column data type
  const columnSelect = document.createElement('select');
  const types = ['String', 'Integer', 'Float', 'Date', 'Boolean', 'Relation'];
  types.forEach((type) => {
    const option = document.createElement('option');
    option.value = type;
    option.textContent = type;
    columnSelect.appendChild(option);
  });
  columnSelect.className = 'column-type-select';

  // Add container for relation input if Relation is selected
  const relationInputsContainer = document.createElement('div');
  relationInputsContainer.className = 'relation-inputs';
  relationInputsContainer.style.display = 'none'; // Hide initially

  const referenceTableInput = document.createElement('input');
  referenceTableInput.type = 'text';
  referenceTableInput.placeholder = 'Reference Table Name';
  referenceTableInput.className = 'reference-table-input';

  const onColumnNameInput = document.createElement('input');
  onColumnNameInput.type = 'text';
  onColumnNameInput.placeholder = 'On Column Name';
  onColumnNameInput.className = 'on-column-name-input';

  relationInputsContainer.appendChild(referenceTableInput);
  relationInputsContainer.appendChild(onColumnNameInput);

  // Event listener to show/hide relation inputs based on selection
  columnSelect.addEventListener('change', () => {
    if (columnSelect.value === 'Relation') {
      relationInputsContainer.style.display = 'block';
    } else {
      relationInputsContainer.style.display = 'none';
    }
  });

  // Append inputs and relation inputs to the column div
  columnDiv.appendChild(columnInput);
  columnDiv.appendChild(columnSelect);
  columnDiv.appendChild(relationInputsContainer);

  // Append the column div to the columns list
  columnList.appendChild(columnDiv);
};

// Show the loader
const showLoader = () => {
  const loader = document.getElementById('loader');
  loader.style.display = 'flex';
};

// Hide the loader
const hideLoader = () => {
  const loader = document.getElementById('loader');
  loader.style.display = 'none';
};

// Render JSON response as two tables
const renderResponseAsTables = (jsonResponse) => {
  const tableContainer = document.getElementById('response-output');
  tableContainer.innerHTML = ''; // Clear previous content

  try {
    const response = JSON.parse(jsonResponse.response); // Parse the nested JSON string

    if (!response.data || response.data.length === 0) {
      tableContainer.textContent = 'No data available.';
      return;
    }

    // Create and append relation table if available
    if (response.relation_data && response.relation_data.length > 0) {
      const relationHeader = document.createElement('h3');
      relationHeader.textContent = 'Relation Data';
      tableContainer.appendChild(relationHeader);

      const relationTable = document.createElement('table');
      relationTable.className = 'response-table';

      const relationThead = document.createElement('thead');
      const relationHeaderRow = document.createElement('tr');
      const relationColumns = Object.keys(response.relation_data[0]);
      relationColumns.forEach((col) => {
        const th = document.createElement('th');
        th.textContent = col;
        relationHeaderRow.appendChild(th);
      });
      relationThead.appendChild(relationHeaderRow);
      relationTable.appendChild(relationThead);

      const relationTbody = document.createElement('tbody');
      response.relation_data.forEach((row) => {
        const tableRow = document.createElement('tr');
        relationColumns.forEach((col) => {
          const td = document.createElement('td');
          td.textContent = row[col] !== undefined ? row[col] : '';
          tableRow.appendChild(td);
        });
        relationTbody.appendChild(tableRow);
      });
      relationTable.appendChild(relationTbody);

      tableContainer.appendChild(relationTable);
    }

    // Create and append AI agent response table
    const aiHeader = document.createElement('h3');
    aiHeader.textContent = 'AI Agent Response';
    tableContainer.appendChild(aiHeader);

    const aiTable = document.createElement('table');
    aiTable.className = 'response-table';

    const aiThead = document.createElement('thead');
    const aiHeaderRow = document.createElement('tr');
    const aiColumns = Object.keys(response.data[0]);
    aiColumns.forEach((col) => {
      const th = document.createElement('th');
      th.textContent = col;
      aiHeaderRow.appendChild(th);
    });
    aiThead.appendChild(aiHeaderRow);
    aiTable.appendChild(aiThead);

    const aiTbody = document.createElement('tbody');
    response.data.forEach((row) => {
      const tableRow = document.createElement('tr');
      aiColumns.forEach((col) => {
        const td = document.createElement('td');
        td.textContent = row[col] !== undefined ? row[col] : '';
        tableRow.appendChild(td);
      });
      aiTbody.appendChild(tableRow);
    });
    aiTable.appendChild(aiTbody);

    tableContainer.appendChild(aiTable);
  } catch (error) {
    console.error('Error parsing or rendering response:', error);
    tableContainer.textContent = 'Failed to render the response.';
  }
};

// Collect column information and input data
let extractedText ;
const collectFormData = () => {
  const columns = {};
  const columnElements = document.querySelectorAll('.column');
  columnElements.forEach((column) => {
    const columnName = column.querySelector('.column-name-input').value.trim();
    const columnType = column.querySelector('.column-type-select').value;
    const relationInputsContainer = column.querySelector('.relation-inputs');

    let columnData = columnType;
    if (columnType === 'Relation') {
      const referenceTable = relationInputsContainer.querySelector('.reference-table-input').value.trim();
      const onColumnName = relationInputsContainer.querySelector('.on-column-name-input').value.trim();
      if (referenceTable && onColumnName) {
        columnData = {
          data_type: 'relation',
          reference_table: referenceTable,
          on_column_name: onColumnName
        };
      }
    }

    if (columnName && columnData) {
      columns[columnName] = columnData;
    }
  });


//  const inputText = inputTextElement ? inputTextElement.value.trim() : '';
  const inputText = extractedText;
  const tableName = document.getElementById('table-name').value.trim();

  return { table_name: tableName, columns, input_text: inputText };
};


// Attach click event to "Add Column" button
document.getElementById('add-column-btn').addEventListener('click', () => {
  addColumn();
});

// Attach click event to "Submit" button
document.getElementById('submit-btn').addEventListener('click', async () => {
  const data = collectFormData();
  console.log('data:', data);

  if (!data.table_name || !data.input_text || Object.keys(data.columns).length === 0) {
    document.getElementById('response-output').textContent = 'Please fill in all required fields.';
    return;
  }

  try {
    showLoader();

    // Send POST request to API
    const response = await fetch('http://127.0.0.1:8089/generate-response', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });

    if (!response.ok) {
      throw new Error(`API request failed with status: ${response.status}`);
    }

    jsonResponse = await response.json();
    console.log('jsonResponse:', jsonResponse);
    renderResponseAsTables(jsonResponse); // Render the tables
  } catch (error) {
    console.error('Error:', error);
    document.getElementById('response-output').textContent = `Error: ${error.message}`;
  } finally {
    hideLoader();
  }
});
addColumn();



document.getElementById("file-input").addEventListener("change", async (event) => {
    const fileInput = event.target;
    const uploadContainer = document.getElementById("upload-container");
    const responseContainer = document.getElementById("response-container");
    const responseText = document.getElementById("response-text");
    const status = document.getElementById("status");
    console.log('fileInput:', fileInput.files[0]);
    // Check if a file is selected
    if (!fileInput.files[0]) {
        status.textContent = "Please select a file to upload.";
        return;
    }
    // Prepare the file for upload
    const formData = new FormData();
    formData.append("file", fileInput.files[0]);
  console.log('formData:', formData);
    // Replace with your API endpoint
    const apiEndpoint = "http://127.0.0.1:8089/upload-and-extract-text/";

    try {
        // Show progress or status message before uploading
        status.textContent = "Uploading...";

        // Make the API call
        const response = await fetch(apiEndpoint, {
            method: "POST",
            body: formData,
        });

        // Handle the response
        if (response.ok) {
            // If the response is plain text, handle it this way
            extractedText = await response.text();

            // Hide the upload input and show the response text
            uploadContainer.style.display = "none";
            responseContainer.style.display = "block";
            responseText.textContent = extractedText;  // Display plain text
            console.log("extractedText", extractedText);
//            console.log('responseText:', responseText);

            // Set the extracted text as the value of the input field (input-text)
            document.getElementById('input-text').value = extractedText;
        } else {
            const error = await response.text();
            status.textContent = `Upload failed: ${error}`;
        }
    } catch (error) {
        // Handle network errors
        status.textContent = `An error occurred: ${error.message}`;
    }
});


let jsonResponse;

//document.getElementById('insertDataBtn').addEventListener('click', async () => {
//    try {
//        if (!jsonResponse) {
//            alert('No data to insert. Please ensure jsonResponse is populated.');
//            return;
//        }
//
//        // Send the jsonResponse to the API using fetch
//        const response = await fetch('http://127.0.0.1:8089/push-data/', {
//            method: 'POST', // HTTP method
//            headers: {
//                'Content-Type': 'application/json',
//            },
//            body: JSON.stringify(jsonResponse), // Pass jsonResponse as the payload
//        });
//
//        // Check if the request was successful
//        if (response.ok) {
//            const result = await response.json(); // Parse the response JSON
//            alert('Data inserted successfully: ' + JSON.stringify(result));
//        } else {
//            const error = await response.json();
//            console.error('Error response:', error);
//            alert('Failed to insert data. Status: ' + response.status + ', Message: ' + JSON.stringify(error));
//        }
//    } catch (error) {
//        console.error('Error:', error);
//        alert('An error occurred while inserting data.');
//    }
//});
//

document.getElementById('insertDataBtn').addEventListener('click', async () => {
    try {
        if (!jsonResponse || !jsonResponse.response) {
            alert('No data to insert. Please ensure jsonResponse is populated.');
            return;
        }

        // Parse the dynamic response
        const parsedPayload = JSON.parse(jsonResponse.response);

        // Dynamically derive column_definitions from the first row of data
        if (!parsedPayload.data || !parsedPayload.data.length) {
            alert('No data available in the payload to determine columns.');
            return;
        }

        const firstRow = parsedPayload.data[0];
     const columnDefinitions = Object.keys(firstRow).reduce((definitions, key) => {
    const value = firstRow[key];
    let type;

    // Infer data type dynamically
    if (typeof value === 'string') {
        type = 'String(255)'; // Add a default length for String
    } else if (typeof value === 'number') {
        type = Number.isInteger(value) ? 'Integer' : 'Float';
    } else if (typeof value === 'boolean') {
        type = 'Boolean';
    } else {
        type = 'String(255)'; // Default to String with a length
    }

    definitions[key] = type;
    return definitions;
}, {});


        // Add column_definitions to the payload
        parsedPayload.column_definitions = columnDefinitions;

        // Send the parsed payload to the API
        const response = await fetch('http://127.0.0.1:8089/push-data/', {
            method: 'POST', // HTTP method
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(parsedPayload), // Pass the dynamically processed payload
        });

        // Check if the request was successful
        if (response.ok) {
            const result = await response.json(); // Parse the response JSON
            alert('Data inserted successfully: ' + JSON.stringify(result));
        } else {
            const error = await response.json();
            console.error('Error response:', error);
            alert('Failed to insert data. Status: ' + response.status + ', Message: ' + JSON.stringify(error));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred while inserting data.');
    }
});

