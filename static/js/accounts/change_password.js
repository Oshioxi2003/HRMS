document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const newPassword = document.getElementById('id_new_password');
    const confirmPassword = document.getElementById('id_confirm_password');
    const passwordMatchStatus = document.getElementById('passwordMatchStatus');
    const lengthCheck = document.getElementById('length-check');
    const letterCheck = document.getElementById('letter-check');
    const numberCheck = document.getElementById('number-check');
    const specialCheck = document.getElementById('special-check');
    const strengthBars = document.querySelectorAll('.strength-segment');
    const strengthText = document.getElementById('passwordStrengthText');
    const passwordForm = document.getElementById('passwordChangeForm');
    const submitButton = document.getElementById('changePasswordBtn');
    
    // Toggle password visibility
    document.querySelectorAll('.toggle-password').forEach(function(toggle) {
        toggle.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const target = document.getElementById(targetId);
            const icon = this.querySelector('i');
            
            if (target.type === 'password') {
                target.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
            } else {
                target.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
            }
        });
    });
    
    // Password strength meter
    function updatePasswordStrength() {
        const password = newPassword.value;
        let strength = 0;
        let message = '';
        
        // Reset the validation indicators
        resetValidationIcons();
        
        if (!password) {
            strengthText.textContent = 'Password strength';
            strengthBars.forEach(bar => bar.className = 'strength-segment');
            return;
        }
        
        // Check requirements and update checklist
        if (password.length >= 8) {
            updateCheckIcon(lengthCheck, true);
            strength++;
        } else {
            updateCheckIcon(lengthCheck, false);
        }
        
        if (/[a-zA-Z]/.test(password)) {
            updateCheckIcon(letterCheck, true);
            strength++;
        } else {
            updateCheckIcon(letterCheck, false);
        }
        
        if (/\d/.test(password)) {
            updateCheckIcon(numberCheck, true);
            strength++;
        } else {
            updateCheckIcon(numberCheck, false);
        }
        
        if (/[^a-zA-Z0-9]/.test(password)) {
            updateCheckIcon(specialCheck, true);
            strength++;
        } else {
            updateCheckIcon(specialCheck, false);
        }
        
        // Update strength meter
        switch(strength) {
            case 0:
            case 1:
                message = 'Weak';
                updateStrengthBars(1, 'segment-weak');
                break;
            case 2:
                message = 'Fair';
                updateStrengthBars(2, 'segment-fair');
                break;
            case 3:
                message = 'Good';
                updateStrengthBars(3, 'segment-good');
                break;
            case 4:
                message = 'Strong';
                updateStrengthBars(4, 'segment-strong');
                break;
        }
        
        strengthText.textContent = message;
        
        // Check if passwords match
        checkPasswordsMatch();
    }
    
    function resetValidationIcons() {
        [lengthCheck, letterCheck, numberCheck, specialCheck].forEach(element => {
            const icon = element.querySelector('i');
            icon.className = 'far fa-circle';
            element.classList.remove('validated');
        });
    }
    
    function updateCheckIcon(element, isValid) {
        const icon = element.querySelector('i');
        if (isValid) {
            icon.className = 'fas fa-check-circle';
            element.classList.add('validated');
        } else {
            icon.className = 'far fa-circle';
            element.classList.remove('validated');
        }
    }
    
    function updateStrengthBars(level, className) {
        strengthBars.forEach((bar, index) => {
            bar.className = 'strength-segment'; // Reset
            if (index < level) {
                bar.classList.add(className);
            }
        });
    }
    
    function checkPasswordsMatch() {
        if (!confirmPassword.value) {
            passwordMatchStatus.textContent = '';
            return;
        }
        
        if (newPassword.value === confirmPassword.value) {
            passwordMatchStatus.textContent = 'Passwords match';
            passwordMatchStatus.style.color = '#28a745';
            passwordMatchStatus.innerHTML = '<i class="fas fa-check-circle"></i> Passwords match';
        } else {
            passwordMatchStatus.textContent = 'Passwords do not match';
            passwordMatchStatus.style.color = '#dc3545';
            passwordMatchStatus.innerHTML = '<i class="fas fa-times-circle"></i> Passwords do not match';
        }
    }
    
    // Add event listeners
    newPassword.addEventListener('input', updatePasswordStrength);
    confirmPassword.addEventListener('input', checkPasswordsMatch);
    
    // Validate form before submit
    passwordForm.addEventListener('submit', function(e) {
        const password = newPassword.value;
        const confirmPwd = confirmPassword.value;
        
        // Check basic requirements
        let valid = true;
        
        if (password.length < 8) {
            valid = false;
        }
        
        if (!(/[a-zA-Z]/.test(password) && /\d/.test(password))) {
            valid = false;
        }
        
        if (password !== confirmPwd) {
            valid = false;
        }
        
        if (!valid) {
            // Form will still submit due to server-side validation,
            // but we add a visual indicator
            submitButton.classList.add('btn-shake');
            setTimeout(() => {
                submitButton.classList.remove('btn-shake');
            }, 500);
        }
    });
    
    // Add animation to alerts
    document.querySelectorAll('.alert').forEach(alert => {
        // Auto hide success messages after 5 seconds
        if (alert.classList.contains('alert-success')) {
            setTimeout(() => {
                alert.style.opacity = '0';
                setTimeout(() => {
                    alert.style.display = 'none';
                }, 300);
            }, 5000);
        }
    });
    
    // Initialize on page load
    updatePasswordStrength();
});

// Add btn-shake animation in CSS for invalid form submission
document.head.insertAdjacentHTML('beforeend', `
<style>
.btn-shake {
    animation: shake 0.5s;
}

@keyframes shake {
    0% { transform: translateX(0); }
    20% { transform: translateX(-10px); }
    40% { transform: translateX(10px); }
    60% { transform: translateX(-10px); }
    80% { transform: translateX(10px); }
    100% { transform: translateX(0); }
}
</style>
`);
