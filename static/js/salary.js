// static/js/salary.js
// Common scripts for salary management module

// Format number as currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(amount);
}

// Calculate net salary dynamically in forms
function calculateNetSalary() {
    let baseSalary = parseFloat($('#id_base_salary').val()) || 0;
    let allowance = parseFloat($('#id_allowance').val()) || 0;
    let seniorityAllowance = parseFloat($('#id_seniority_allowance').val()) || 0;
    let bonus = parseFloat($('#id_bonus').val()) || 0;
    
    let incomeTax = parseFloat($('#id_income_tax').val()) || 0;
    let socialInsurance = parseFloat($('#id_social_insurance').val()) || 0;
    let healthInsurance = parseFloat($('#id_health_insurance').val()) || 0;
    let unemploymentInsurance = parseFloat($('#id_unemployment_insurance').val()) || 0;
    let deductions = parseFloat($('#id_deductions').val()) || 0;
    let advance = parseFloat($('#id_advance').val()) || 0;
    
    let totalEarnings = baseSalary + allowance + seniorityAllowance + bonus;
    let totalDeductions = incomeTax + socialInsurance + healthInsurance + unemploymentInsurance + deductions + advance;
    let netSalary = totalEarnings - totalDeductions;
    
    // Update the net salary field if it exists
    if ($('#id_net_salary').length) {
        $('#id_net_salary').val(netSalary.toFixed(2));
    }
    
    // Update summary display if it exists
    if ($('#net-salary-display').length) {
        $('#net-salary-display').text(formatCurrency(netSalary));
        $('#total-earnings-display').text(formatCurrency(totalEarnings));
        $('#total-deductions-display').text(formatCurrency(totalDeductions));
    }
}

// Calculate standard deductions based on base salary
function calculateStandardDeductions() {
    let baseSalary = parseFloat($('#id_base_salary').val()) || 0;
    
    // Example rates - adjust as needed
    let socialInsuranceRate = 0.08; // 8%
    let healthInsuranceRate = 0.015; // 1.5%
    let unemploymentInsuranceRate = 0.01; // 1%
    
    let socialInsurance = baseSalary * socialInsuranceRate;
    let healthInsurance = baseSalary * healthInsuranceRate;
    let unemploymentInsurance = baseSalary * unemploymentInsuranceRate;
    
    // Update fields
    $('#id_social_insurance').val(socialInsurance.toFixed(2));
    $('#id_health_insurance').val(healthInsurance.toFixed(2));
    $('#id_unemployment_insurance').val(unemploymentInsurance.toFixed(2));
    
    // Calculate simple income tax (example)
    let taxableIncome = baseSalary - socialInsurance - healthInsurance - unemploymentInsurance;
    let incomeTax = 0;
    
    if (taxableIncome > 5000000) { // Example threshold
        incomeTax = (taxableIncome - 5000000) * 0.1; // 10% on amount over threshold
    }
    
    $('#id_income_tax').val(incomeTax.toFixed(2));
    
    // Recalculate net salary
    calculateNetSalary();
}

// Initialize when document is ready
$(document).ready(function() {
    // Add event listeners to salary form fields
    $('.salary-input').on('change', calculateNetSalary);
    
    // Listener for base salary to calculate standard deductions
    $('#id_base_salary').on('change', calculateStandardDeductions);
    
    // Calculate on page load
    calculateNetSalary();
});
