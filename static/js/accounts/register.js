document.addEventListener('DOMContentLoaded', function() {
    // Toggle password visibility
    const toggleButtons = document.querySelectorAll('.toggle-password');
    
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
    
    // Password strength checker
    const passwordInput = document.getElementById('id_password1');
    const strengthBar = document.querySelector('.strength-bar');
    const strengthText = document.querySelector('.strength-text');
    const rules = document.querySelectorAll('.rule');
    
    if (passwordInput) {
        passwordInput.addEventListener('input', function() {
            const password = this.value;
            let strength = 0;
            
            // Update rule validation
            rules.forEach(rule => {
                const ruleType = rule.getAttribute('data-rule');
                
                switch(ruleType) {
                    case 'length':
                        rule.classList.toggle('valid', password.length >= 8);
                        if (password.length >= 8) strength += 25;
                        break;
                    case 'letter':
                        const hasLetter = /[a-zA-Z]/.test(password);
                        rule.classList.toggle('valid', hasLetter);
                        if (hasLetter) strength += 25;
                        break;
                    case 'digit':
                        const hasDigit = /\d/.test(password);
                        rule.classList.toggle('valid', hasDigit);
                        if (hasDigit) strength += 25;
                        break;
                    case 'notcommon':
                        // This is simplified - in real world you'd check against a list
                        const isNotCommon = password.length >= 8 && 
                                         !/^12345|password|admin|qwerty/i.test(password);
                        rule.classList.toggle('valid', isNotCommon);
                        if (isNotCommon) strength += 25;
                        break;
                }
            });
            
            // Update strength bar
            strengthBar.style.width = `${strength}%`;
            
            // Set the color based on strength
            if (strength <= 25) {
                strengthBar.style.backgroundColor = '#e74c3c';
                strengthText.textContent = 'Yếu';
            } else if (strength <= 50) {
                strengthBar.style.backgroundColor = '#f39c12';
                strengthText.textContent = 'Trung bình';
            } else if (strength <= 75) {
                strengthBar.style.backgroundColor = '#3498db';
                strengthText.textContent = 'Khá mạnh';
            } else {
                strengthBar.style.backgroundColor = '#2ecc71';
                strengthText.textContent = 'Mạnh';
            }
            
            if (password === '') {
                strengthText.textContent = 'Chưa nhập mật khẩu';
                strengthBar.style.width = '0%';
            }
        });
    }
    
    // Password confirmation matcher
    const confirmInput = document.getElementById('id_password2');
    if (confirmInput && passwordInput) {
        confirmInput.addEventListener('input', function() {
            const password = passwordInput.value;
            const confirm = this.value;
            
            if (password === confirm) {
                this.parentElement.classList.remove('error');
                this.parentElement.classList.add('match');
            } else {
                this.parentElement.classList.remove('match');
                if (confirm !== '') {
                    this.parentElement.classList.add('error');
                } else {
                    this.parentElement.classList.remove('error');
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
            setTimeout(() => {
                alert.style.display = 'none';
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
    
    // Form validation
    const registerForm = document.querySelector('.register-form');
    const termsCheckbox = document.getElementById('terms');
    
    if (registerForm) {
        registerForm.addEventListener('submit', function(event) {
            let isValid = true;
            
            // Validate terms checkbox
            if (termsCheckbox && !termsCheckbox.checked) {
                isValid = false;
                const checkbox = termsCheckbox.parentElement;
                
                if (!checkbox.nextElementSibling || !checkbox.nextElementSibling.classList.contains('terms-error')) {
                    const errorMessage = document.createElement('div');
                    errorMessage.className = 'invalid-feedback terms-error';
                    errorMessage.innerHTML = '<p><i class="fas fa-exclamation-circle"></i> Bạn phải đồng ý với các điều khoản</p>';
                    checkbox.parentElement.insertBefore(errorMessage, checkbox.nextElementSibling);
                }
            } else if (termsCheckbox) {
                const errorElement = termsCheckbox.parentElement.nextElementSibling;
                if (errorElement && errorElement.classList.contains('terms-error')) {
                    errorElement.remove();
                }
            }
            
            // Simple check for password match
            if (passwordInput && confirmInput && passwordInput.value !== confirmInput.value) {
                isValid = false;
                
                // Add error message if not already present
                const inputGroup = confirmInput.parentElement;
                const errorContainer = inputGroup.nextElementSibling;
                
                if (!errorContainer || !errorContainer.classList.contains('invalid-feedback')) {
                    const errorMessage = document.createElement('div');
                    errorMessage.className = 'invalid-feedback';
                    errorMessage.innerHTML = '<p><i class="fas fa-exclamation-circle"></i> Mật khẩu không khớp</p>';
                    inputGroup.parentElement.insertBefore(errorMessage, inputGroup.nextElementSibling);
                }
            }
            
            if (!isValid) {
                event.preventDefault();
            }
        });
    }
    
    // Animate entrance of form groups
    const formGroups = document.querySelectorAll('.form-group');
    formGroups.forEach((group, index) => {
        group.style.opacity = '0';
        group.style.transform = 'translateY(20px)';
        group.style.transition = 'opacity 0.5s ease, transform 0.5s ease';
        
        setTimeout(() => {
            group.style.opacity = '1';
            group.style.transform = 'translateY(0)';
        }, 100 + (index * 100));
    });
});
