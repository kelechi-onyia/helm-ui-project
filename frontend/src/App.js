import React, { useEffect, useState } from "react";
import Form from "@rjsf/core";
import validator from "@rjsf/validator-ajv8";
import axios from "axios";
// import '../node_modules/bootstrap/dist/css/bootstrap.min.css';

const App = () => {
  const [formData, setFormData] = useState({});
  const [schema, setSchema] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitSuccess, setSubmitSuccess] = useState(false);

  // Create a UI schema with specific styling for read-only fields
  const createUiSchema = (schemaObj) => {
    const uiSchema = {
      "ui:submitButtonOptions": {
        submitText: "Save Configuration",
        props: {
          className: "bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
        }
      }
    };

    // Helper function to traverse the schema and apply UI properties
    const processSchemaForUI = (schemaObj, currentPath = "", parentUiSchema = uiSchema) => {
      if (!schemaObj || typeof schemaObj !== 'object') return;

      // Process the properties of the schema
      if (schemaObj.properties) {
        for (const key in schemaObj.properties) {
          const property = schemaObj.properties[key];
          const propertyPath = currentPath ? `${currentPath}.${key}` : key;

          // Ensure the parent UI schema has an entry for this property
          if (!parentUiSchema[key]) {
            parentUiSchema[key] = {};
          }

          // Apply read-only styling if the property is marked as readOnly
          if (property.readOnly) {
            parentUiSchema[key]["ui:disabled"] = true;
            parentUiSchema[key]["ui:readonly"] = true;
            // parentUiSchema[key]["ui:widget"] = "ReadOnlyWidget";
            parentUiSchema[key]["ui:options"] = {
              ...parentUiSchema[key]["ui:options"],
              classNames: "bg-gray-100"
            };
          }

          // Recursively process nested objects
          if (property.type === "object" && property.properties) {
            processSchemaForUI(property, propertyPath, parentUiSchema[key]);
          }
        }
      }
    };

    // Process the schema to build UI schema
    processSchemaForUI(schemaObj);
    return uiSchema;
  };

  useEffect(() => {
    setLoading(true);
    setError(null);

    axios.get("http://127.0.0.1:8000/schema")
      .then((res) => {
        console.log("Received schema:", res.data);
        setSchema(res.data);

        // Also fetch current values
        return axios.get("http://127.0.0.1:8000/values");
      })
      .then((res) => {
        if (res && res.data) {
          console.log("Current values:", res.data);
          setFormData(res.data);
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error:", err);
        setError(err.message || "Failed to load data");
        setLoading(false);
      });
  }, []);

  // Custom read-only widget
  const ReadOnlyWidget = ({ value }) => {
    return (
      <div className="p-2 bg-gray-100 border border-gray-200 rounded text-gray-700">
        {value === undefined ? <em>Not set</em> : String(value)}
      </div>
    );
  };

  const handleSubmit = ({ formData }) => {
    console.log("Submitting form data:", formData);
    setSubmitSuccess(false);

    axios.post("http://127.0.0.1:8000/update", formData)
      .then(() => {
        console.log("Update successful");
        setSubmitSuccess(true);
        setTimeout(() => setSubmitSuccess(false), 3000);
      })
      .catch((err) => {
        console.error("Error updating:", err);
        setError(err.message || "Failed to update configuration");
      });
  };

  if (loading) {
    return <div>Loading configuration...</div>;
  }

  if (error) {
    return <div className="error">{error}</div>;
  }

  if (!schema) {
    return <div>No configuration schema available.</div>;
  }

  // Create the UI schema from the JSON schema
  const uiSchema = createUiSchema(schema);

  return (
    <div className="max-w-4xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Application Configuration</h1>

      {submitSuccess && (
        <div className="mb-4 p-3 bg-green-100 text-green-700 rounded-md">
          Configuration updated successfully!
        </div>
      )}

      <Form
        schema={schema}
        uiSchema={uiSchema}
        formData={formData}
        validator={validator}
        onSubmit={handleSubmit}
        widgets={{
          ReadOnlyWidget: ReadOnlyWidget
        }}
        liveValidate={false}
      />

      <div className="mt-8 p-4 bg-gray-50 rounded-md">
        <h3 className="text-lg font-medium mb-2">Current Configuration</h3>
        <pre className="bg-gray-100 p-3 rounded whitespace-pre-wrap">
          {JSON.stringify(formData, null, 2)}
        </pre>
      </div>
    </div>
  );
};

export default App;
