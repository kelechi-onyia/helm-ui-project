import React, { useEffect, useState } from "react";
import Form from "@rjsf/mui";
import validator from "@rjsf/validator-ajv8";
import axios from "axios";
import "./App.css";
import {
  AppBar,
  Toolbar,
  Typography,
  Container,
  Paper,
  Box,
  CircularProgress,
  Alert,
  Snackbar,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Divider,
  IconButton,
  Tooltip,
} from "@mui/material";
import {
  ExpandMore as ExpandMoreIcon,
  Settings as SettingsIcon,
  Save as SaveIcon,
  Image as ImageIcon,
  Public as PublicIcon,
  Cloud as CloudIcon,
  Refresh as RefreshIcon,
  Info as InfoIcon,
} from "@mui/icons-material";

const App = () => {
  const [formData, setFormData] = useState({});
  const [originalFormData, setOriginalFormData] = useState({}); // Track original data
  const [schema, setSchema] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitSuccess, setSubmitSuccess] = useState(false);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [pendingFormData, setPendingFormData] = useState(null);
  const [showConfigJson, setShowConfigJson] = useState(false);

  const API_BASE_URL = process.env.REACT_APP_API_URL || "http://127.0.0.1:8000";

  // Deep comparison function to check if two objects are equal
  const deepEqual = (obj1, obj2) => {
    return JSON.stringify(obj1) === JSON.stringify(obj2);
  };

  // Check if there are any changes from original data
  const hasChanges = !deepEqual(formData, originalFormData);

  // Function to find differences between two objects
  const findDifferences = (original, updated, path = "") => {
    const differences = [];

    const compare = (obj1, obj2, currentPath) => {
      // Handle arrays
      if (Array.isArray(obj1) && Array.isArray(obj2)) {
        if (JSON.stringify(obj1) !== JSON.stringify(obj2)) {
          differences.push({
            path: currentPath,
            oldValue: obj1,
            newValue: obj2,
            type: "array"
          });
        }
        return;
      }

      // Handle objects
      if (typeof obj1 === "object" && obj1 !== null && typeof obj2 === "object" && obj2 !== null) {
        const allKeys = new Set([...Object.keys(obj1), ...Object.keys(obj2)]);

        allKeys.forEach(key => {
          const newPath = currentPath ? `${currentPath}.${key}` : key;

          if (!(key in obj1)) {
            differences.push({
              path: newPath,
              oldValue: undefined,
              newValue: obj2[key],
              type: "added"
            });
          } else if (!(key in obj2)) {
            differences.push({
              path: newPath,
              oldValue: obj1[key],
              newValue: undefined,
              type: "removed"
            });
          } else if (typeof obj1[key] === "object" && typeof obj2[key] === "object") {
            compare(obj1[key], obj2[key], newPath);
          } else if (obj1[key] !== obj2[key]) {
            differences.push({
              path: newPath,
              oldValue: obj1[key],
              newValue: obj2[key],
              type: "modified"
            });
          }
        });
        return;
      }

      // Handle primitives
      if (obj1 !== obj2) {
        differences.push({
          path: currentPath,
          oldValue: obj1,
          newValue: obj2,
          type: "modified"
        });
      }
    };

    compare(original, updated, path);
    return differences;
  };

  const fetchConfiguration = () => {
    setLoading(true);
    setError(null);

    axios
      .get(`${API_BASE_URL}/schema`)
      .then((res) => {
        console.log("Received schema:", res.data);
        setSchema(res.data);
        return axios.get(`${API_BASE_URL}/values`);
      })
      .then((res) => {
        if (res && res.data) {
          console.log("Current values:", res.data);
          setFormData(res.data);
          setOriginalFormData(res.data); // Store original data for comparison
        }
        setLoading(false);
      })
      .catch((err) => {
        console.error("Error:", err);
        setError(err.response?.data?.detail || err.message || "Failed to load configuration");
        setLoading(false);
      });
  };

  useEffect(() => {
    fetchConfiguration();
  }, []);

  const createUiSchema = (schemaObj) => {
    const uiSchema = {
      "ui:submitButtonOptions": {
        submitText: "Save Configuration",
        norender: true, // We'll use our custom button
      },
    };

    const processSchemaForUI = (schemaObj, currentPath = "", parentUiSchema = uiSchema) => {
      if (!schemaObj || typeof schemaObj !== "object") return;

      if (schemaObj.properties) {
        for (const key in schemaObj.properties) {
          const property = schemaObj.properties[key];

          if (!parentUiSchema[key]) {
            parentUiSchema[key] = {};
          }

          if (property.readOnly) {
            parentUiSchema[key]["ui:disabled"] = true;
            parentUiSchema[key]["ui:readonly"] = true;
            parentUiSchema[key]["ui:help"] = "This field is read-only and cannot be modified";
          }

          if (property.type === "object" && property.properties) {
            processSchemaForUI(property, currentPath ? `${currentPath}.${key}` : key, parentUiSchema[key]);
          }
        }
      }
    };

    processSchemaForUI(schemaObj);
    return uiSchema;
  };

  const handleSubmit = ({ formData }) => {
    console.log("Form submitted, opening confirmation dialog");
    setPendingFormData(formData);
    setConfirmDialogOpen(true);
  };

  const handleConfirmSave = () => {
    console.log("Confirming save with data:", pendingFormData);
    setConfirmDialogOpen(false);
    setSubmitSuccess(false);
    setError(null);

    axios
      .post(`${API_BASE_URL}/update`, pendingFormData)
      .then(() => {
        console.log("Update successful");
        setFormData(pendingFormData);
        setOriginalFormData(pendingFormData); // Update original data after successful save
        setSubmitSuccess(true);
      })
      .catch((err) => {
        console.error("Error updating:", err);
        setError(err.response?.data?.detail || err.message || "Failed to update configuration");
      })
      .finally(() => {
        setPendingFormData(null);
      });
  };

  const handleCancelSave = () => {
    setConfirmDialogOpen(false);
    setPendingFormData(null);
  };

  const getIconComponent = (iconName) => {
    const iconMap = {
      image: <ImageIcon />,
      cloud: <CloudIcon />,
      public: <PublicIcon />,
      settings: <SettingsIcon />,
    };
    return iconMap[iconName] || <SettingsIcon />;
  };

  const renderFormInSections = () => {
    if (!schema || !schema.properties) {
      return null;
    }

    // Get sections from schema (coming from backend config.yaml)
    // If no sections defined, create a default structure
    const sections = schema.sections && schema.sections.length > 0
      ? schema.sections.map(section => ({
          ...section,
          icon: getIconComponent(section.icon)
        }))
      : [];

    // Identify which properties belong to sections and which are top-level
    const topLevelProps = Object.keys(schema.properties).filter(
      (key) => !sections.some((section) => section.key === key)
    );

    return (
      <Box>
        {/* Top-level properties */}
        {topLevelProps.length > 0 && (
          <Accordion defaultExpanded>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box display="flex" alignItems="center" gap={1}>
                <SettingsIcon color="primary" />
                <Typography variant="h6">General Settings</Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                Configure general application settings
              </Typography>
              {topLevelProps.map((propKey) => (
                <Box key={propKey} sx={{ mb: 2 }}>
                  <Form
                    schema={{
                      type: "object",
                      properties: { [propKey]: schema.properties[propKey] },
                    }}
                    formData={{ [propKey]: formData[propKey] }}
                    validator={validator}
                    onChange={({ formData: newFormData }) => {
                      setFormData((prev) => ({ ...prev, ...newFormData }));
                    }}
                    uiSchema={{
                      "ui:submitButtonOptions": { norender: true },
                      ...(createUiSchema(schema)[propKey] ? { [propKey]: createUiSchema(schema)[propKey] } : {}),
                    }}
                  />
                </Box>
              ))}
            </AccordionDetails>
          </Accordion>
        )}

        {/* Section-based properties */}
        {sections.map(
          (section) =>
            schema.properties[section.key] && (
              <Accordion key={section.key} defaultExpanded>
                <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                  <Box display="flex" alignItems="center" gap={1}>
                    {React.cloneElement(section.icon, { color: "primary" })}
                    <Typography variant="h6">{section.title}</Typography>
                    {schema.properties[section.key]?.readOnly && (
                      <Chip label="Read-Only" size="small" color="default" sx={{ ml: 1 }} />
                    )}
                  </Box>
                </AccordionSummary>
                <AccordionDetails>
                  <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                    {section.description}
                  </Typography>
                  <Form
                    schema={{
                      type: "object",
                      properties: { [section.key]: schema.properties[section.key] },
                    }}
                    formData={{ [section.key]: formData[section.key] }}
                    validator={validator}
                    onChange={({ formData: newFormData }) => {
                      setFormData((prev) => ({ ...prev, ...newFormData }));
                    }}
                    uiSchema={{
                      "ui:submitButtonOptions": { norender: true },
                      ...(createUiSchema(schema)[section.key] ? { [section.key]: createUiSchema(schema)[section.key] } : {}),
                    }}
                  />
                </AccordionDetails>
              </Accordion>
            )
        )}
      </Box>
    );
  };

  if (loading) {
    return (
      <Box
        display="flex"
        flexDirection="column"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        gap={2}
      >
        <CircularProgress size={60} />
        <Typography variant="h6" color="text.secondary">
          Loading configuration...
        </Typography>
      </Box>
    );
  }

  if (error && !schema) {
    return (
      <Container maxWidth="md" sx={{ mt: 8 }}>
        <Alert
          severity="error"
          action={
            <Button color="inherit" size="small" onClick={fetchConfiguration} startIcon={<RefreshIcon />}>
              Retry
            </Button>
          }
        >
          <Typography variant="h6">Error Loading Configuration</Typography>
          {error}
        </Alert>
      </Container>
    );
  }

  if (!schema) {
    return (
      <Container maxWidth="md" sx={{ mt: 8 }}>
        <Alert severity="warning">No configuration schema available.</Alert>
      </Container>
    );
  }

  const uiSchema = createUiSchema(schema);

  // Get UI configuration from schema
  const uiMetadata = schema.ui_metadata || {};
  const appTitle = uiMetadata.title || "ArgoCD Deployment Manager";
  const appDescription = uiMetadata.description || "Configure your Docker image tags and deployment settings for ArgoCD";
  const showJsonToggle = uiMetadata.show_json_toggle !== false;

  return (
    <Box sx={{ flexGrow: 1, minHeight: "100vh", backgroundColor: "#f5f5f5" }}>
      {/* App Bar */}
      <AppBar position="static" elevation={0}>
        <Toolbar>
          <SettingsIcon sx={{ mr: 2 }} />
          <Typography variant="h6" component="div" sx={{ flexGrow: 1 }}>
            {appTitle}
          </Typography>
          <Tooltip title="Refresh configuration">
            <IconButton color="inherit" onClick={fetchConfiguration}>
              <RefreshIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Container maxWidth="lg" sx={{ mt: 4, mb: 4 }}>
        {/* Page Header */}
        <Paper elevation={2} sx={{ p: 3, mb: 3, backgroundColor: "white" }}>
          <Box display="flex" alignItems="center" justifyContent="space-between">
            <Box>
              <Typography variant="h4" gutterBottom>
                Application Configuration
              </Typography>
              <Typography variant="body1" color="text.secondary">
                {appDescription}
              </Typography>
            </Box>
            {showJsonToggle && (
              <Tooltip title="Toggle JSON view">
                <IconButton onClick={() => setShowConfigJson(!showConfigJson)}>
                  <InfoIcon />
                </IconButton>
              </Tooltip>
            )}
          </Box>
        </Paper>

        {/* Error Display */}
        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {/* Main Form */}
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          {renderFormInSections()}

          <Divider sx={{ my: 3 }} />

          {/* Submit Button */}
          <Box display="flex" justifyContent="flex-end" gap={2}>
            <Button
              variant="outlined"
              onClick={fetchConfiguration}
              startIcon={<RefreshIcon />}
            >
              Reset
            </Button>
            <Button
              variant="contained"
              size="large"
              startIcon={<SaveIcon />}
              onClick={() => handleSubmit({ formData })}
              disabled={!hasChanges}
              sx={{ px: 4 }}
            >
              Save Configuration
            </Button>
          </Box>
        </Paper>

        {/* Current Configuration JSON View */}
        {showConfigJson && (
          <Paper elevation={2} sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Current Configuration (JSON)
            </Typography>
            <Box
              component="pre"
              sx={{
                p: 2,
                backgroundColor: "#f5f5f5",
                borderRadius: 1,
                overflow: "auto",
                fontSize: "0.875rem",
                fontFamily: "monospace",
              }}
            >
              {JSON.stringify(formData, null, 2)}
            </Box>
          </Paper>
        )}
      </Container>

      {/* Confirmation Dialog */}
      <Dialog open={confirmDialogOpen} onClose={handleCancelSave} maxWidth="sm" fullWidth>
        <DialogTitle>
          {pendingFormData && deepEqual(pendingFormData, originalFormData)
            ? "No Changes Detected"
            : "Confirm Configuration Update"}
        </DialogTitle>
        <DialogContent>
          {pendingFormData && deepEqual(pendingFormData, originalFormData) ? (
            <>
              <Alert severity="info" sx={{ mb: 2 }}>
                No changes have been made to the configuration.
              </Alert>
              <Typography variant="body2" color="text.secondary">
                The current configuration is identical to the saved configuration.
                Make changes to any field to enable saving.
              </Typography>
            </>
          ) : (
            <>
              <Typography variant="body1" gutterBottom>
                Are you sure you want to save these configuration changes?
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                This will update the deployment configuration and may trigger an ArgoCD sync.
              </Typography>
              {pendingFormData && originalFormData && (() => {
                const differences = findDifferences(originalFormData, pendingFormData);

                return (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
                      Changed Fields ({differences.length}):
                    </Typography>
                    <Box
                      sx={{
                        p: 2,
                        backgroundColor: "#f5f5f5",
                        borderRadius: 1,
                        overflow: "auto",
                        maxHeight: "300px",
                      }}
                    >
                      {differences.length > 0 ? (
                        differences.map((diff, index) => (
                          <Box
                            key={index}
                            sx={{
                              mb: 2,
                              pb: 2,
                              borderBottom: index < differences.length - 1 ? "1px solid #e0e0e0" : "none",
                            }}
                          >
                            <Typography
                              variant="body2"
                              sx={{
                                fontWeight: "bold",
                                fontFamily: "monospace",
                                color: "#1976d2",
                                mb: 0.5,
                              }}
                            >
                              {diff.path}
                            </Typography>
                            <Box sx={{ display: "flex", gap: 2, alignItems: "center", flexWrap: "wrap" }}>
                              <Box sx={{ flex: "1 1 45%" }}>
                                <Typography variant="caption" color="text.secondary">
                                  Old:
                                </Typography>
                                <Typography
                                  variant="body2"
                                  sx={{
                                    fontFamily: "monospace",
                                    fontSize: "0.75rem",
                                    color: "#d32f2f",
                                    textDecoration: "line-through",
                                  }}
                                >
                                  {diff.type === "array"
                                    ? JSON.stringify(diff.oldValue, null, 2)
                                    : String(diff.oldValue ?? "undefined")}
                                </Typography>
                              </Box>
                              <Typography variant="body2" sx={{ fontWeight: "bold" }}>
                                →
                              </Typography>
                              <Box sx={{ flex: "1 1 45%" }}>
                                <Typography variant="caption" color="text.secondary">
                                  New:
                                </Typography>
                                <Typography
                                  variant="body2"
                                  sx={{
                                    fontFamily: "monospace",
                                    fontSize: "0.75rem",
                                    color: "#2e7d32",
                                    fontWeight: "bold",
                                  }}
                                >
                                  {diff.type === "array"
                                    ? JSON.stringify(diff.newValue, null, 2)
                                    : String(diff.newValue ?? "undefined")}
                                </Typography>
                              </Box>
                            </Box>
                          </Box>
                        ))
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          No changes detected
                        </Typography>
                      )}
                    </Box>
                  </Box>
                );
              })()}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancelSave}>
            {pendingFormData && deepEqual(pendingFormData, originalFormData) ? "Close" : "Cancel"}
          </Button>
          <Button
            onClick={handleConfirmSave}
            variant="contained"
            startIcon={<SaveIcon />}
            disabled={pendingFormData && deepEqual(pendingFormData, originalFormData)}
          >
            Confirm Save
          </Button>
        </DialogActions>
      </Dialog>

      {/* Success Notification */}
      <Snackbar
        open={submitSuccess}
        autoHideDuration={6000}
        onClose={() => setSubmitSuccess(false)}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
      >
        <Alert onClose={() => setSubmitSuccess(false)} severity="success" sx={{ width: "100%" }}>
          Configuration updated successfully!
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default App;