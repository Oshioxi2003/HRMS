document.addEventListener('DOMContentLoaded', function() {
    // Get form elements
    const resetForm = document.getElementById('resetForm');
    const resetButton = document.getElementById('resetButton');
    const emailInput = document.getElementById('email');
    
    if (resetForm) {
        resetForm.addEventListener('submit', function(e) {
            // We're not preventing the default form submission,
            // but we're adding some visual feedback
            
            // Validate email format
            const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            if (!emailPattern.test(emailInput.value)) {
                e.preventDefault();
                showFormError(emailInput, 'Vui lòng nhập địa chỉ email hợp lệ');
                return;
            }
            
            // Show loading state
            resetButton.classList.add('loading');
            
            // We'll let the form submit naturally
            // A real implementation might use AJAX/fetch here
        });
    }
    
    // Email input validation
    if (emailInput) {
        emailInput.addEventListener('input', function() {
            // Remove error state if present
            this.parentElement.classList.remove('error');
            const errorElement = document.getElementById('email-error');
            if (errorElement) {
                errorElement.remove();
            }
        });
        
        emailInput.addEventListener('focus', function() {
            this.parentElement.style.transform = 'translateY(-2px)';
            this.parentElement.style.transition = 'transform 0.3s ease';
        });
        
        emailInput.addEventListener('blur', function() {
            this.parentElement.style.transform = 'translateY(0)';
            
            // Validate email on blur
            if (this.value !== '') {
                const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
                if (!emailPattern.test(this.value)) {
                    showFormError(this, 'Địa chỉ email không hợp lệ');
                }
            }
        });
    }
    
    // Close alert messages
    const closeButtons = document.querySelectorAll('.close-alert');
    closeButtons.forEach(button => {
        button.addEventListener('click', function() {
            const alert = this.closest('.alert');
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-10px)';
            alert.style.transition = 'opacity 0.3s, transform 0.3s';
            setTimeout(() => {
                alert.style.display = 'none';
            }, 300);
        });
    });
    
    // Function to show form errors
    function showFormError(inputElement, message) {
        const inputGroup = inputElement.parentElement;
        inputGroup.classList.add('error');
        
        // Create error message if it doesn't exist
        if (!document.getElementById('email-error')) {
            const errorDiv = document.createElement('div');
            errorDiv.id = 'email-error';
            errorDiv.className = 'invalid-feedback';
            errorDiv.innerHTML = `<p><i class="fas fa-exclamation-circle"></i> ${message}</p>`;
            inputGroup.insertAdjacentElement('afterend', errorDiv);
        }
    }
    
    // Add some animation for the icon
    const keyIcon = document.querySelector('.icon-circle i');
    if (keyIcon) {
        // Add a slight rotation animation
        setTimeout(() => {
            keyIcon.style.transition = 'transform 0.5s ease';
            keyIcon.style.transform = 'rotate(15deg)';
            
            setTimeout(() => {
                keyIcon.style.transform = 'rotate(0deg)';
                
                // Add the pulse class after initial animation
                setTimeout(() => {
                    keyIcon.classList.add('pulse');
                }, 500);
            }, 500);
        }, 1000);
    }
});
