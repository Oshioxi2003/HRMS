document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const toggleButtons = document.querySelectorAll('.toggle-password');
    const passwordInput = document.getElementById('id_new_password1');
    const confirmInput = document.getElementById('id_new_password2');
    const strengthBar = document.querySelector('.strength-bar');
    const strengthText = document.querySelector('.strength-text');
    const rules = document.querySelectorAll('.rule');
    const matchStatus = document.querySelector('.match-status');
    const newPasswordForm = document.getElementById('newPasswordForm');
    const resetButton = document.getElementById('resetButton');
    
    // 1. Toggle password visibility
    toggleButtons.forEach(button => {
        button.addEventListener('click', function() {
            const input = this.previousElementSibling;
            const type = input.getAttribute('type') === 'password' ? 'text' : 'password';
            input.setAttribute('type', type);
            
            // Toggle the eye icon
            this.querySelector('i').classList.toggle('fa-eye');
            this.querySelector('i').classList.toggle('fa-eye-slash');
        });
    });
    
    // 2. Password strength checker
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            let strength = 0;
            let messages = ["Trống", "Yếu", "Trung bình", "Khá mạnh", "Mạnh"];
            let colors = ["#e74c3c", "#e74c3c", "#f39c12", "#3498db", "#2ecc71"];
            
            // Check password length
            const lengthValid = password.length >= 8;
            if (lengthValid) strength += 25;
            
            // Check for letters
            const hasLetter = /[a-zA-Z]/.test(password);
            if (hasLetter) strength += 25;
            
            // Check for numbers
            const hasDigit = /\d/.test(password);
            if (hasDigit) strength += 25;
            
            // Check for special characters
            const hasSpecial = /[^a-zA-Z0-9]/.test(password);
            if (hasSpecial) strength += 25;
            
            // Check common passwords (simplified)
            const isCommon = /^(123456|password|qwerty|admin|welcome)$/i.test(password);
            if (isCommon) strength = 10;
            
            // Update visual indicators
            if (password === '') {
                strengthBar.style.width = '0%';
                strengthBar.style.backgroundPosition = '0% 0%';
                strengthText.textContent = "Chưa nhập mật khẩu";
                strengthText.style.color = '';
            } else {
                strengthBar.style.width = strength + '%';
                // Adjust gradient position based on strength
                const position = Math.max(0, Math.min(100, strength)) / 100 * 100;
                strengthBar.style.backgroundPosition = position + '% 0%';
                
                const strengthIndex = Math.floor(strength / 25);
                strengthText.textContent = messages[strengthIndex];
                strengthText.style.color = colors[strengthIndex];
            }
            
            // Update rule validations
            rules.forEach(rule => {
                const ruleType = rule.getAttribute('data-rule');
                
                switch(ruleType) {
                    case 'length':
                        rule.classList.toggle('valid', lengthValid);
                        break;
                    case 'letter':
                        rule.classList.toggle('valid', hasLetter);
                        break;
                    case 'digit':
                        rule.classList.toggle('valid', hasDigit);
                        break;
                    case 'notcommon':
                        rule.classList.toggle('valid', !isCommon && password.length >= 8);
                        break;
                }
            });
            
            // Check password match if confirm field has value
            if (confirmInput && confirmInput.value) {
                checkPasswordMatch();
            }
        });
    }
    
    // 3. Password match checker
    function checkPasswordMatch() {
        if (passwordInput && confirmInput && matchStatus) {
            const password = passwordInput.value;
            const confirm = confirmInput.value;
            
            if (confirm === '') {
                matchStatus.innerHTML = '<i class="fas fa-info-circle"></i> Nhập lại mật khẩu để xác nhận';
                matchStatus.className = 'form-help-text match-status';
                confirmInput.parentElement.classList.remove('match', 'mismatch');
            } else if (password === confirm) {
                matchStatus.innerHTML = '<i class="fas fa-check-circle"></i> Mật khẩu khớp';
                matchStatus.className = 'form-help-text match-status match';
                confirmInput.parentElement.classList.add('match');
                confirmInput.parentElement.classList.remove('mismatch');
            } else {
                matchStatus.innerHTML = '<i class="fas fa-times-circle"></i> Mật khẩu không khớp';
                matchStatus.className = 'form-help-text match-status mismatch';
                confirmInput.parentElement.classList.add('mismatch');
                confirmInput.parentElement.classList.remove('match');
            }
        }
    }
    
    if (confirmInput) {
        confirmInput.addEventListener('input', checkPasswordMatch);
    }
    
    // 4. Field focus effects
    const formInputs = document.querySelectorAll('.form-control');
    
    formInputs.forEach(input => {
        // Add focus effect
        input.addEventListener('focus', function() {
            this.parentElement.style.transform = 'translateY(-2px)';
            this.parentElement.style.boxShadow = '0 5px 15px rgba(78, 84, 200, 0.1)';
            this.parentElement.style.transition = 'all 0.3s ease';
        });
        
        // Remove focus effect
        input.addEventListener('blur', function() {
            this.parentElement.style.transform = 'translateY(0)';
            this.parentElement.style.boxShadow = 'none';
        });
    });
    
    // 5. Form validation and submission
    if (newPasswordForm) {
        newPasswordForm.addEventListener('submit', function(e) {
            // Clear existing error messages
            clearErrors();
            
            // Validation
            const password = passwordInput.value;
            const confirm = confirmInput.value;
            let valid = true;
            
            // Check password emptiness
            if (!password) {
                e.preventDefault();
                showError('Vui lòng nhập mật khẩu mới');
                valid = false;
            }
            
            // Check confirmation emptiness
            if (!confirm) {
                e.preventDefault();
                showError('Vui lòng xác nhận mật khẩu mới');
                valid = false;
            }
            
            // Password requirements validation
            if (password) {
                const lengthValid = password.length >= 8;
                const letterValid = /[a-zA-Z]/.test(password);
                const digitValid = /\d/.test(password);
                
                if (!lengthValid || !letterValid || !digitValid) {
                    e.preventDefault();
                    showError('Mật khẩu không đáp ứng các yêu cầu tối thiểu');
                    valid = false;
                    
                    // Highlight the specific rule that's failing
                    if (!lengthValid) highlightRule('length');
                    if (!letterValid) highlightRule('letter');
                    if (!digitValid) highlightRule('digit');
                }
            }
            
            // Passwords match validation
            if (password && confirm && password !== confirm) {
                e.preventDefault();
                showError('Mật khẩu không khớp');
                valid = false;
            }
            
            // If valid, show loading state
            if (valid) {
                resetButton.classList.add('loading');
            }
        });
    }
    
    // Helper function to show validation errors
    function showError(message) {
        const errorMessage = document.createElement('div');
        errorMessage.className = 'alert alert-danger';
        errorMessage.innerHTML = `
            <i class="fas fa-exclamation-triangle alert-icon"></i>
            <div class="alert-content">${message}</div>
            <button type="button" class="close-alert">&times;</button>
        `;
        
        // Add event listener to close button
        const closeButton = errorMessage.querySelector('.close-alert');
        closeButton.addEventListener('click', function() {
            errorMessage.style.opacity = '0';
            errorMessage.style.transform = 'translateY(-10px)';
            errorMessage.style.transition = 'opacity 0.3s, transform 0.3s';
            setTimeout(() => {
                errorMessage.remove();
            }, 300);
        });
        
        // Add to alert container or create a new one
        const alertContainer = document.querySelector('.alert-container');
        if (alertContainer) {
            alertContainer.appendChild(errorMessage);
        } else {
            const newAlertContainer = document.createElement('div');
            newAlertContainer.className = 'alert-container';
            newAlertContainer.appendChild(errorMessage);
            
            const resetHeader = document.querySelector('.reset-header');
            resetHeader.insertAdjacentElement('afterend', newAlertContainer);
        }
    }
    
    // Clear previous error messages
    function clearErrors() {
        const alertContainer = document.querySelector('.alert-container');
        if (alertContainer) {
            const alerts = alertContainer.querySelectorAll('.alert-danger');
            alerts.forEach(alert => alert.remove());
        }
    }
    
    // Highlight failing rule with a bounce animation
    function highlightRule(ruleType) {
        const rule = document.querySelector(`.rule[data-rule="${ruleType}"]`);
        if (rule) {
            rule.style.animation = 'none';
            // Trigger a reflow
            void rule.offsetWidth;
            rule.style.animation = 'highlight 0.6s';
        }
    }
    
    // Add animation for highlight
    const style = document.createElement('style');
    style.textContent = `
        @keyframes highlight {
            0%, 100% { transform: translateX(0); }
            20%, 60% { transform: translateX(-5px); background-color: rgba(231, 76, 60, 0.1); }
            40%, 80% { transform: translateX(5px); background-color: rgba(231, 76, 60, 0.1); }
        }
    `;
    document.head.appendChild(style);
    
    // 6. Close existing alert messages
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
    
    // 7. Initialize strength meter and rule validation on page load
    if (passwordInput && passwordInput.value) {
        // Trigger the input event to update the strength meter and rules
        const event = new Event('input', { bubbles: true });
        passwordInput.dispatchEvent(event);
    }
    
    // 8. Initialize match status on page load
    if (confirmInput && confirmInput.value) {
        checkPasswordMatch();
    }
});
