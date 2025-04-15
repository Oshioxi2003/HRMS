// static/js/performance.js
/**
 * Performance Management Module JavaScript
 */

// Chart color palette
const chartColors = {
    primary: 'rgba(63, 81, 181, 1)',
    primaryLight: 'rgba(63, 81, 181, 0.2)',
    success: 'rgba(76, 175, 80, 1)',
    successLight: 'rgba(76, 175, 80, 0.2)',
    info: 'rgba(33, 150, 243, 1)',
    infoLight: 'rgba(33, 150, 243, 0.2)',
    warning: 'rgba(255, 152, 0, 1)',
    warningLight: 'rgba(255, 152, 0, 0.2)',
    danger: 'rgba(244, 67, 54, 1)',
    dangerLight: 'rgba(244, 67, 54, 0.2)',
};

/**
 * Format achievement data with appropriate color and class
 * @param {number} achievement - The achievement percentage
 * @returns {Object} Object with color and class
 */
function formatAchievementData(achievement) {
    if (achievement >= 100) {
        return {
            color: chartColors.success,
            colorLight: chartColors.successLight,
            class: 'success',
            icon: 'trophy'
        };
    } else if (achievement >= 80) {
        return {
            color: chartColors.info,
            colorLight: chartColors.infoLight,
            class: 'info',
            icon: 'thumbs-up'
        };
    } else if (achievement >= 50) {
        return {
            color: chartColors.warning,
            colorLight: chartColors.warningLight,
            class: 'warning',
            icon: 'exclamation-circle'
        };
    } else {
        return {
            color: chartColors.danger,
            colorLight: chartColors.dangerLight,
            class: 'danger',
            icon: 'exclamation-triangle'
        };
    }
}

/**
 * Initialize charts in the performance module
 */
function initPerformanceCharts() {
    // Employee performance chart
    const employeeChartEl = document.getElementById('employeePerformanceChart');
    if (employeeChartEl) {
        const ctx = employeeChartEl.getContext('2d');
        new Chart(ctx, {
            type: 'line',
            data: {
                labels: employeeChartData.labels,
                datasets: [{
                    label: 'Achievement (%)',
                    data: employeeChartData.data,
                    backgroundColor: chartColors.primaryLight,
                    borderColor: chartColors.primary,
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return 'Achievement: ' + context.raw + '%';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 120,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Department performance chart
    const deptChartEl = document.getElementById('departmentPerformanceChart');
    if (deptChartEl) {
        const ctx = deptChartEl.getContext('2d');
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: departmentChartData.labels,
                datasets: [{
                    label: 'Average Achievement (%)',
                    data: departmentChartData.data,
                    backgroundColor: departmentChartData.data.map(val => {
                        return formatAchievementData(val).colorLight;
                    }),
                    borderColor: departmentChartData.data.map(val => {
                        return formatAchievementData(val).color;
                    }),
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return 'Achievement: ' + context.raw + '%';
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        max: 120,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                }
            }
        });
    }
}

/**
 * Initialize KPI form behavior
 */
function initKpiForm() {
    const kpiTypeField = document.getElementById('id_kpi_type');
    const minTargetField = document.getElementById('id_min_target');
    const maxTargetField = document.getElementById('id_max_target');
    
    if (kpiTypeField) {
        kpiTypeField.addEventListener('change', function() {
            // Default values for different KPI types
            const kpiDefaults = {
                'Individual': {
                    minRange: 80,
                    maxRange: 100
                },
                'Department': {
                    minRange: 70,
                    maxRange: 95
                },
                'Company': {
                    minRange: 75,
                    maxRange: 90
                }
            };
            
            const selectedType = this.value;
            if (selectedType in kpiDefaults) {
                const defaults = kpiDefaults[selectedType];
                
                if (!minTargetField.value) {
                    minTargetField.value = defaults.minRange;
                }
                
                if (!maxTargetField.value) {
                    maxTargetField.value = defaults.maxRange;
                }
            }
        });
    }
}

/**
 * Calculate achievement rate for evaluation forms
 */
function initAchievementCalculator() {
    const targetField = document.getElementById('id_target');
    const resultField = document.getElementById('id_result');
    
    if (targetField && resultField) {
        function calculateAchievement() {
            const target = parseFloat(targetField.value);
            const result = parseFloat(resultField.value);
            
            if (target && result && target > 0) {
                const achievement = (result / target * 100).toFixed(2);
                
                // Get or create achievement preview element
                let previewEl = document.getElementById('achievement-preview');
                if (!previewEl) {
                    previewEl = document.createElement('div');
                    previewEl.id = 'achievement-preview';
                    previewEl.className = 'mt-2';
                    resultField.parentNode.appendChild(previewEl);
                }
                
                const format = formatAchievementData(achievement);
                previewEl.innerHTML = `<small class="text-${format.class}"><i class="fas fa-${format.icon} me-1"></i> Achievement Rate: ${achievement}%</small>`;
            }
        }
        
        targetField.addEventListener('input', calculateAchievement);
        resultField.addEventListener('input', calculateAchievement);
        
        // Calculate on page load if values exist
        if (targetField.value && resultField.value) {
            calculateAchievement();
        }
    }
}

/**
 * Initialize date pickers
 */
function initDatePickers() {
    const datePickers = document.querySelectorAll('.datepicker');
    if (datePickers.length > 0) {
        datePickers.forEach(input => {
            flatpickr(input, {
                dateFormat: 'Y-m-d',
                allowInput: true
            });
        });
    }
}

/**
 * Initialize all performance module functionality
 */
function initPerformanceModule() {
    initPerformanceCharts();
    initKpiForm();
    initAchievementCalculator();
    initDatePickers();
    
    // Initialize Select2 for dropdowns if available
    if (typeof $.fn.select2 !== 'undefined') {
        $('.select2-dropdown').select2({
            placeholder: 'Select an option',
            allowClear: true,
            width: '100%'
        });
    }
}

// Execute when DOM is fully loaded
document.addEventListener('DOMContentLoaded', initPerformanceModule);
