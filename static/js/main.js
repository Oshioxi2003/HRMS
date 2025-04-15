function updateValueHelpText(valueType) {
    const valueField = document.getElementById('id_value');
    
    // Clear previous attributes
    valueField.placeholder = '';
    
    // Set appropriate help text based on type
    if (valueType === 'string') {
        valueField.placeholder = 'Simple text value';
    } else if (valueType === 'integer') {
        valueField.placeholder = 'Numeric value (e.g., 42)';
    } else if (valueType === 'boolean') {
        valueField.placeholder = 'true or false';
    } else if (valueType === 'json') {
        valueField.placeholder = '{"key": "value", "another_key": 123}';
    } else if (valueType === 'text') {
        valueField.placeholder = 'Enter longer text content here...';
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const valueType = document.getElementById('id_value_type').value;
    updateValueHelpText(valueType);
});
