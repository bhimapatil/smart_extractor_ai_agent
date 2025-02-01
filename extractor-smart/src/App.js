import './App.css';
import Header from './components/header';
import { useState } from 'react';
import loader from "./assets/loader.jpg"
import { LineByLineDisplay } from './components/lineByLineDisplay';

const columnTypes = ['String', 'Integer', 'Float', 'Date', 'Boolean', 'Relation'];
function App() {
  const [tableConfig, setTableConfig] = useState("");
  const [columnConfig, setColumnConfig] = useState([{ id: 1, value: "", type: "" }]);
  const [fileResp, setFileResp] = useState(null);
  const [loading, setLoading] = useState(false);
  const [errors, setErrors] = useState({}); // Store validation errors

  const handleTableChange = (event) => {
    setTableConfig(event.target.value);
    if (event.target.value) setErrors((prev) => ({ ...prev, tableConfig: "" }));
  };

  const handleAddField = () => {
    const newField = { id: columnConfig.length + 1, value: "", type: "" };
    setColumnConfig([...columnConfig, newField]);
  };

  const handleColumnValue = (id, value) => {
    setColumnConfig(
      columnConfig.map((field) => (field.id === id ? { ...field, value } : field))
    );
    setErrors((prev) => ({
      ...prev,
      columnConfig: columnConfig.some((field) => field.value === "") ? "All column fields must have a value" : "",
    }));
  };

  const handleTypeChange = (id, type) => {
    setColumnConfig(
      columnConfig.map((field) => (field.id === id ? { ...field, type } : field))
    );
    setErrors((prev) => ({
      ...prev,
      columnConfig: columnConfig.some((field) => field.type === "") ? "All column fields must have a type" : "",
    }));
  };

  const handleFileChange = (event) => {
    if (!event.target.files[0]) {
      setErrors((prev) => ({ ...prev, fileResp: "Please select a file to upload" }));
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append("file", event.target.files[0]);

    fetch("http://127.0.0.1:8089/upload-and-extract-text/", {
      method: "POST",
      body: formData,
    })
      .then((response) =>
        response.text().then((res) => {
          setFileResp(res);
          setLoading(false);
          setErrors((prev) => ({ ...prev, fileResp: "" }));
        })
      )
      .catch((error) => {
        console.error("Error uploading file:", error);
        setLoading(false);
        alert("Failed to upload the file");
      });
  };

  const validateForm = () => {
    const newErrors = {};

    if (!tableConfig.trim()) newErrors.tableConfig = "Table configuration is required";
    if (columnConfig.some((field) => !field.value.trim() || !field.type.trim())) {
      newErrors.columnConfig = "All column fields must have both value and type";
    }
    if (!fileResp) newErrors.fileResp = "File upload is required";

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = () => {
    if (!validateForm()) return; // Prevent submission if validation fails

    const data = { tableConfig, columnConfig, fileResp };
    console.log("Submit clicked", data);
  };

  return (
    <div className='container'>
      <Header></Header>
      <div className="card mt-5 mb-5">
        <div className="card-body">

          <div className='row'>
            <div className="col-md-3">
              <label htmlFor="tableConfig" className="form-label">Table Configuration</label>
              <input type="text" className="form-control" id="tableConfig" value={tableConfig}
                onChange={handleTableChange} />
            </div>
            <div className="col-md-5 row">
              <label className="form-label">
                Column Configuration
              </label>
              {columnConfig.map((field, index) => (
                <div key={field.id} className="col-md-12 mb-3">

                  <div className="d-flex">
                    <input
                      type="text"
                      className="form-control w-75"
                      id={`columnConfig-${field.id}`}
                      value={field.value}
                      onChange={(e) => handleColumnValue(field.id, e.target.value)}
                      placeholder="Enter column value"
                    />
                    <select
                      id={`columnSelect-${field.id}`}
                      className="form-select w-25"

                      onChange={(e) => handleTypeChange(field.id, e.target.value)}
                    >
                      <option value="" >
                        Type
                      </option>
                      {columnTypes.map((type, index) => (
                        <option key={index} value={type}>
                          {type}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
              ))}
              <div className='row'>
                <div className='col-md-4'>
                  <button
                    type="button"
                    className="btn btn-outline-success"
                    onClick={handleAddField}
                  >
                    Add
                  </button>
                </div>
              </div>

            </div>
          </div>
          <div className='row mt-3'>
            <div className="col-md-8 mx-auto">
              <label htmlFor="formFile" className="form-label">Upload File</label>
              <div className='row'>
                <div className='col-md-12'>
                  <input className="form-control" type="file" id="formFile"
                    onChange={handleFileChange} />
                </div>

              </div>
            </div>
          </div>
          {fileResp && 
            <div class=" d-flex justify-content-center mt-4">
                <div className='card p-4 col-md-8 fileData'>
                <LineByLineDisplay data={fileResp} />
                </div>
            </div>}
              
              {loading &&   <div class="d-flex justify-content-center mt-4">
                  <div class="spinner-border" role="status">
                    <span class="visually-hidden">Loading...</span>
                  </div>
                </div>}
          <button type="button" className="btn btn-outline-success mt-4"
          onClick={handleSubmit}>Submit</button>
        </div>
      </div>
    </div>
  );
}

export default App;
