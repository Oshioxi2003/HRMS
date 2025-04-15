document.addEventListener('DOMContentLoaded', function() {
    // Toggle password visibility
    const togglePassword = document.querySelector('.toggle-password');
    const passwordInput = document.querySelector('#password');
    
    if (togglePassword && passwordInput) {
        togglePassword.addEventListener('click', function() {
            // Toggle the type attribute
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);
            
            // Toggle the eye icon
            this.querySelector('i').classList.toggle('fa-eye');
            this.querySelector('i').classList.toggle('fa-eye-slash');
        });
    }
    
    // Close alert messages
    const closeButtons = document.querySelectorAll('.close-alert');
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            this.parentElement.style.opacity = '0';
            setTimeout(() => {
                this.parentElement.style.display = 'none';
            }, 300);
        });
    });
    
    // Add form animation effects
    const formInputs = document.querySelectorAll('.form-control');
    formInputs.forEach(input => {
        // Add focus effect
        input.addEventListener('focus', function() {
            this.parentElement.style.transform = 'translateY(-2px)';
            this.parentElement.style.transition = 'transform 0.3s ease';
        });
        
        // Remove focus effect
        input.addEventListener('blur', function() {
            this.parentElement.style.transform = 'translateY(0)';
        });
    });
    
    // Login form validation
    const loginForm = document.querySelector('.login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(event) {
            const username = document.querySelector('#username').value.trim();
            const password = document.querySelector('#password').value;
            
            let isValid = true;
            
            // Simple validation
            if (username === '') {
                showValidationError('username', 'Vui lòng nhập tên đăng nhập hoặc email');
                isValid = false;
            } else {
                clearValidationError('username');
            }
            
            if (password === '') {
                showValidationError('password', 'Vui lòng nhập mật khẩu');
                isValid = false;
            } else {
                clearValidationError('password');
            }
            
            if (!isValid) {
                event.preventDefault();
            }
        });
    }
    
    // Show validation error
    function showValidationError(inputId, message) {
        const input = document.querySelector(`#${inputId}`);
        const errorDiv = document.querySelector(`#${inputId}-error`);
        
        input.classList.add('error');
        
        // Create error message element if it doesn't exist
        if (!errorDiv) {
            const errorElement = document.createElement('div');
            errorElement.id = `${inputId}-error`;
            errorElement.className = 'validation-error';
            errorElement.textContent = message;
            
            input.parentElement.insertAdjacentElement('afterend', errorElement);
        } else {
            errorDiv.textContent = message;
            errorDiv.style.display = 'block';
        }
    }
    
    // Clear validation error
    function clearValidationError(inputId) {
        const input = document.querySelector(`#${inputId}`);
        const errorDiv = document.querySelector(`#${inputId}-error`);
        
        input.classList.remove('error');
        
        if (errorDiv) {
            errorDiv.style.display = 'none';
        }
    }
    
    // Add remember me functionality
    const rememberCheckbox = document.querySelector('#remember');
    if (rememberCheckbox) {
        // Check if username is stored in localStorage
        const savedUsername = localStorage.getItem('rememberedUsername');
        if (savedUsername) {
            document.querySelector('#username').value = savedUsername;
            rememberCheckbox.checked = true;
        }
        
        // Save username to localStorage when checkbox is checked
        loginForm.addEventListener('submit', function() {
            const username = document.querySelector('#username').value.trim();
            if (rememberCheckbox.checked) {
                localStorage.setItem('rememberedUsername', username);
            } else {
                localStorage.removeItem('rememberedUsername');
            }
        });
    }
});
