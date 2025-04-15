// Common reporting functions and utilities

/**
 * Formats numbers with commas as thousands separators
 */
function formatNumber(num) {
    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * Formats a date object to YYYY-MM-DD string
 */
function formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
}

/**
 * Calculates the difference in days between two dates
 */
function daysBetween(date1, date2) {
    const oneDay = 24 * 60 * 60 * 1000;
    return Math.round(Math.abs((date1 - date2) / oneDay));
}

/**
 * Calculates business days (Mon-Fri) between two dates
 */
function businessDaysBetween(startDate, endDate) {
    let count = 0;
    const curDate = new Date(startDate.getTime());
    while (curDate <= endDate) {
        const dayOfWeek = curDate.getDay();
        if (dayOfWeek !== 0 && dayOfWeek !== 6) count++;
        curDate.setDate(curDate.getDate() + 1);
    }
    return count;
}

/**
 * Gets a color for a data visualization based on index
 */
function getChartColor(index, alpha = 0.8) {
    const colors = [
        `rgba(63, 81, 181, ${alpha})`,   // Indigo
        `rgba(244, 67, 54, ${alpha})`,   // Red
        `rgba(76, 175, 80, ${alpha})`,   // Green
        `rgba(255, 152, 0, ${alpha})`,   // Orange
        `rgba(33, 150, 243, ${alpha})`,  // Blue
        `rgba(156, 39, 176, ${alpha})`,  // Purple
        `rgba(0, 188, 212, ${alpha})`,   // Cyan
        `rgba(255, 87, 34, ${alpha})`,   // Deep Orange
        `rgba(0, 150, 136, ${alpha})`,   // Teal
        `rgba(121, 85, 72, ${alpha})`,   // Brown
    ];
    return colors[index % colors.length];
}

/**
 * Creates a chart.js instance with common defaults
 */
function createChart(canvasId, type, data, options = {}) {
    const ctx = document.getElementById(canvasId).getContext('2d');
    
    // Default options
    const defaultOptions = {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
            legend: {
                position: 'top',
            },
            tooltip: {
                mode: 'index',
                intersect: false,
            }
        }
    };
    
    // Merge options
    const chartOptions = {...defaultOptions, ...options};
    
    return new Chart(ctx, {
        type: type,
        data: data,
        options: chartOptions
    });
}

/**
 * Handles form submission for exporting reports
 */
function setupExportHandlers() {
    document.querySelectorAll('.export-form').forEach(form => {
        form.addEventListener('submit', function(e) {
            const exportFormat = this.querySelector('[name="export_format"]').value;
            const exportType = this.querySelector('[name="export"]').value;
            
            // Add loading indicator
            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Exporting...';
            submitBtn.disabled = true;
            
            // Create a notification when export is complete
            window.addEventListener('focus', function onFocus() {
                setTimeout(() => {
                    submitBtn.innerHTML = originalText;
                    submitBtn.disabled = false;
                }, 1000);
                window.removeEventListener('focus', onFocus);
            });
        });
    });
}

/**
 * Initialize date range pickers with common options
 */
function initDateRangePickers() {
    // Initialize single date pickers
    document.querySelectorAll('.date-picker').forEach(element => {
        flatpickr(element, {
            dateFormat: "Y-m-d",
            allowInput: true
        });
    });
    
    // Initialize date range pickers
    document.querySelectorAll('.date-range-picker').forEach(element => {
        const startInput = element.querySelector('.start-date');
        const endInput = element.querySelector('.end-date');
        
        if (startInput && endInput) {
            flatpickr(startInput, {
                dateFormat: "Y-m-d",
                allowInput: true,
                onChange: function(selectedDates, dateStr) {
                    // Update end date min when start date changes
                    endDatePicker.set('minDate', dateStr);
                }
            });
            
            const endDatePicker = flatpickr(endInput, {
                dateFormat: "Y-m-d",
                allowInput: true,
                minDate: startInput.value || null
            });
        }
    });
}

/**
 * Set up quick date range selectors (This Month, Last Month, etc.)
 */
function setupDateRangeSelectors() {
    document.querySelectorAll('.quick-date-range').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            
            const range = this.dataset.range;
            const startInput = document.querySelector('#id_start_date');
            const endInput = document.querySelector('#id_end_date');
            
            if (!startInput || !endInput) return;
            
            const today = new Date();
            let startDate, endDate;
            
            switch(range) {
                case 'today':
                    startDate = endDate = today;
                    break;
                case 'yesterday':
                    startDate = endDate = new Date(today);
                    startDate.setDate(today.getDate() - 1);
                    break;
                case 'this_week':
                    startDate = new Date(today);
                    startDate.setDate(today.getDate() - today.getDay());
                    endDate = today;
                    break;
                case 'last_week':
                    endDate = new Date(today);
                    endDate.setDate(today.getDate() - today.getDay() - 1);
                    startDate = new Date(endDate);
                    startDate.setDate(endDate.getDate() - 6);
                    break;
                case 'this_month':
                    startDate = new Date(today.getFullYear(), today.getMonth(), 1);
                    endDate = today;
                    break;
                case 'last_month':
                    startDate = new Date(today.getFullYear(), today.getMonth() - 1, 1);
                    endDate = new Date(today.getFullYear(), today.getMonth(), 0);
                    break;
                case 'this_year':
                    startDate = new Date(today.getFullYear(), 0, 1);
                    endDate = today;
                    break;
                    case 'last_year':
                        startDate = new Date(today.getFullYear() - 1, 0, 1);
                        endDate = new Date(today.getFullYear() - 1, 11, 31);
                        break;
                    case 'last_30_days':
                        startDate = new Date(today);
                        startDate.setDate(today.getDate() - 30);
                        endDate = today;
                        break;
                    case 'last_90_days':
                        startDate = new Date(today);
                        startDate.setDate(today.getDate() - 90);
                        endDate = today;
                        break;
                    default:
                        return;
                }
                
                // Set the values in the inputs
                startInput._flatpickr.setDate(startDate);
                endInput._flatpickr.setDate(endDate);
                
                // Update any related elements
                document.querySelectorAll('.quick-date-range').forEach(btn => {
                    btn.classList.remove('active');
                });
                this.classList.add('active');
            });
        });
    }
    
    /**
     * Dynamic filter handling for report tables
     */
    function setupTableFilters() {
        document.querySelectorAll('.table-filter').forEach(filter => {
            filter.addEventListener('change', function() {
                const targetTable = document.querySelector(this.dataset.target);
                if (!targetTable) return;
                
                const filterValue = this.value.toLowerCase();
                const filterColumn = parseInt(this.dataset.column, 10);
                
                // Filter table rows
                targetTable.querySelectorAll('tbody tr').forEach(row => {
                    const cellValue = row.cells[filterColumn].textContent.toLowerCase();
                    
                    if (filterValue === '' || cellValue.includes(filterValue)) {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            });
        });
    }
    
    /**
     * Setup for report comparison functionality
     */
    function setupReportComparison() {
        const comparisonForm = document.querySelector('#comparison-form');
        if (!comparisonForm) return;
        
        comparisonForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const period1Start = document.querySelector('#period1_start').value;
            const period1End = document.querySelector('#period1_end').value;
            const period2Start = document.querySelector('#period2_start').value;
            const period2End = document.querySelector('#period2_end').value;
            
            // Validate dates
            if (!period1Start || !period1End || !period2Start || !period2End) {
                alert('Please select all date ranges for comparison');
                return;
            }
            
            // Show loading indicator
            document.querySelector('#comparison-results').innerHTML = 
                '<div class="text-center my-5"><div class="spinner-border text-primary" role="status"></div><p class="mt-2">Generating comparison...</p></div>';
            
            // Fetch comparison data
            fetch(`/reports/compare-data/?period1_start=${period1Start}&period1_end=${period1End}&period2_start=${period2Start}&period2_end=${period2End}&type=${this.dataset.reportType}`)
                .then(response => response.json())
                .then(data => {
                    renderComparisonResults(data);
                })
                .catch(error => {
                    document.querySelector('#comparison-results').innerHTML = 
                        `<div class="alert alert-danger">Error loading comparison data: ${error.message}</div>`;
                });
        });
    }
    
    /**
     * Render comparison results with visualizations
     */
    function renderComparisonResults(data) {
        const resultsContainer = document.querySelector('#comparison-results');
        
        // Clear previous results
        resultsContainer.innerHTML = '';
        
        // Create container for the comparison chart
        const chartContainer = document.createElement('div');
        chartContainer.className = 'chart-container mt-4';
        chartContainer.style.height = '400px';
        
        const canvas = document.createElement('canvas');
        canvas.id = 'comparison-chart';
        chartContainer.appendChild(canvas);
        resultsContainer.appendChild(chartContainer);
        
        // Create a table for detailed comparison
        const tableDiv = document.createElement('div');
        tableDiv.className = 'table-responsive mt-4';
        
        const table = document.createElement('table');
        table.className = 'table table-hover';
        
        // Create table header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        
        // Add headers
        const headers = ['Metric', 'Period 1', 'Period 2', 'Change', '% Change'];
        headers.forEach(header => {
            const th = document.createElement('th');
            th.textContent = header;
            headerRow.appendChild(th);
        });
        
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Create table body
        const tbody = document.createElement('tbody');
        
        // Add rows for each metric
        for (const metric in data.metrics) {
            const row = document.createElement('tr');
            
            // Metric name cell
            const nameCell = document.createElement('td');
            nameCell.textContent = data.metrics[metric].label;
            row.appendChild(nameCell);
            
            // Period 1 value
            const period1Cell = document.createElement('td');
            period1Cell.textContent = data.metrics[metric].period1;
            row.appendChild(period1Cell);
            
            // Period 2 value
            const period2Cell = document.createElement('td');
            period2Cell.textContent = data.metrics[metric].period2;
            row.appendChild(period2Cell);
            
            // Change value
            const changeCell = document.createElement('td');
            const change = data.metrics[metric].change;
            changeCell.textContent = change > 0 ? `+${change}` : change;
            changeCell.className = change > 0 ? 'text-success' : (change < 0 ? 'text-danger' : '');
            row.appendChild(changeCell);
            
            // Percent change
            const percentCell = document.createElement('td');
            const percentChange = data.metrics[metric].percentChange;
            percentCell.textContent = percentChange > 0 ? `+${percentChange}%` : `${percentChange}%`;
            percentCell.className = percentChange > 0 ? 'text-success' : (percentChange < 0 ? 'text-danger' : '');
            row.appendChild(percentCell);
            
            tbody.appendChild(row);
        }
        
        table.appendChild(tbody);
        tableDiv.appendChild(table);
        resultsContainer.appendChild(tableDiv);
        
        // Create the comparison chart
        createComparisonChart('comparison-chart', data);
    }
    
    /**
     * Create a comparison chart for two time periods
     */
    function createComparisonChart(canvasId, data) {
        const ctx = document.getElementById(canvasId).getContext('2d');
        
        // Extract data for chart
        const labels = Object.keys(data.metrics).map(key => data.metrics[key].label);
        const period1Data = Object.keys(data.metrics).map(key => data.metrics[key].period1);
        const period2Data = Object.keys(data.metrics).map(key => data.metrics[key].period2);
        
        // Create chart
        new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: `Period 1 (${data.period1Label})`,
                        data: period1Data,
                        backgroundColor: 'rgba(63, 81, 181, 0.7)',
                        borderColor: 'rgba(63, 81, 181, 1)',
                        borderWidth: 1
                    },
                    {
                        label: `Period 2 (${data.period2Label})`,
                        data: period2Data,
                        backgroundColor: 'rgba(76, 175, 80, 0.7)',
                        borderColor: 'rgba(76, 175, 80, 1)',
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
    }
    
    // Initialize all report features when DOM is loaded
    document.addEventListener('DOMContentLoaded', function() {
        initDateRangePickers();
        setupDateRangeSelectors();
        setupTableFilters();
        setupExportHandlers();
        setupReportComparison();
    });