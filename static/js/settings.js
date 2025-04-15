// static/js/settings.js
document.addEventListener('DOMContentLoaded', function() {
    // Initialize form elements
    initializeForm();
    
    // Add event listeners for dynamic behavior
    addEventListeners();
});

/**
 * Initialize form elements
 */
function initializeForm() {
    // Set up color pickers for appearance settings
    const colorInputs = document.querySelectorAll('input[name^="setting_"][name$="_color"]');
    colorInputs.forEach(input => {
        if (input.type !== 'color') {
            input.type = 'color';
        }
    });
    
    // Set up JSON formatting for JSON type settings
    const jsonInputs = document.querySelectorAll('textarea[id^="setting_"][data-type="json"]');
    jsonInputs.forEach(textarea => {
        try {
            const jsonValue = JSON.parse(textarea.value);
            textarea.value = JSON.stringify(jsonValue, null, 2);
        } catch (e) {
            // Invalid JSON, leave as is
            console.warn('Invalid JSON in textarea:', textarea.id);
        }
    });
}

/**
 * Add event listeners for dynamic behavior
 */
function addEventListeners() {
    // Setup boolean switches
    document.querySelectorAll('.form-check-input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            const hiddenInput = this.nextElementSibling;
            hiddenInput.value = this.checked ? 'true' : 'false';
        });
    });
    
    // Setup visibility toggles for dependent settings
    document.querySelectorAll('[data-toggle-control]').forEach(control => {
        control.addEventListener('change', function() {
            const targetSelector = this.getAttribute('data-toggle-target');
            const targets = document.querySelectorAll(targetSelector);
            
            if ((this.type === 'checkbox' && this.checked) || 
                (this.type !== 'checkbox' && this.value === '1')) {
                targets.forEach(target => {
                    target.style.display = 'block';
                });
            } else {
                targets.forEach(target => {
                    target.style.display = 'none';
                });
            }
        });
        
        // Trigger change event to initialize state
        const event = new Event('change');
        control.dispatchEvent(event);
    });
    
    // Setup password toggles
    document.querySelectorAll('.toggle-password').forEach(button => {
        button.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const passwordInput = document.getElementById(targetId);
            const icon = this.querySelector('i');
            
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                passwordInput.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
    
    // Setup JSON validation
    document.querySelectorAll('textarea[data-type="json"]').forEach(textarea => {
        textarea.addEventListener('blur', function() {
            try {
                const jsonValue = JSON.parse(this.value);
                this.value = JSON.stringify(jsonValue, null, 2);
                this.classList.remove('is-invalid');
                
                // Hide error message if exists
                const errorElement = document.getElementById(`${this.id}-error`);
                if (errorElement) {
                    errorElement.style.display = 'none';
                }
            } catch (e) {
                this.classList.add('is-invalid');
                
                // Show error message
                let errorElement = document.getElementById(`${this.id}-error`);
                if (!errorElement) {
                    errorElement = document.createElement('div');
                    errorElement.id = `${this.id}-error`;
                    errorElement.className = 'invalid-feedback d-block';
                    this.parentNode.appendChild(errorElement);
                }
                
                errorElement.textContent = 'Invalid JSON: ' + e.message;
                errorElement.style.display = 'block';
            }
        });
    });
}

/**
 * Format and validate JSON input
 * @param {HTMLElement} element - The textarea element
 * @returns {boolean} - True if valid JSON
 */
function validateJson(element) {
    try {
        const jsonValue = JSON.parse(element.value);
        element.value = JSON.stringify(jsonValue, null, 2);
        return true;
    } catch (e) {
        return false;
    }
}

/**
 * Show confirmation dialog before deleting setting
 * @param {string} settingName - Name of the setting to delete
 * @param {string} deleteUrl - URL to submit delete request to
 * @returns {boolean} - Whether to proceed with deletion
 */
function confirmDelete(settingName, deleteUrl) {
    if (confirm(`Are you sure you want to delete the setting "${settingName}"? This action cannot be undone.`)) {
        window.location.href = deleteUrl;
        return true;
    }
    return false;
}
