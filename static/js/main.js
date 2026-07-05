// static/js/main.js

/**
 * Shop Management System - Main JavaScript
 * Version: 1.0.0
 * Author: Your Name
 * Description: Complete client-side functionality for the shop management system
 */

// ============================================
// 1. DOM READY - Initialize Everything
// ============================================
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 Shop Management System Initialized');
    console.log('📊 Version: 1.0.0');
    console.log('🔐 User: ' + (window.currentUser || 'Guest'));
    
    // Initialize all modules
    initTheme();
    initSidebar();
    initNotifications();
    initCharts();
    initDataTables();
    initFormValidation();
    initSearch();
    initKeyboardShortcuts();
    initAutoRefresh();
    initTooltips();
    initPopovers();
});

// ============================================
// 2. THEME MANAGEMENT
// ============================================
function initTheme() {
    // Get saved theme from localStorage or default to light
    const savedTheme = localStorage.getItem('shopTheme') || 'light';
    const htmlElement = document.documentElement;
    const themeToggle = document.getElementById('themeToggle');
    const themeIcon = document.getElementById('themeIcon');
    const themeThumb = document.getElementById('themeThumb');
    
    // Apply saved theme
    applyTheme(savedTheme);
    
    // Theme toggle click handler
    if (themeToggle) {
        themeToggle.addEventListener('click', function() {
            const currentTheme = htmlElement.getAttribute('data-bs-theme');
            const newTheme = currentTheme === 'light' ? 'dark' : 'light';
            
            // Apply theme
            applyTheme(newTheme);
            
            // Save preference
            localStorage.setItem('shopTheme', newTheme);
            
            // Update icon
            updateThemeIcon(newTheme, themeIcon, themeThumb);
            
            // Show feedback
            showToast(`Theme switched to ${newTheme} mode`, 'info');
            
            // Notify server (optional)
            fetch('/api/theme/' + newTheme)
                .then(response => response.json())
                .catch(err => console.log('Theme saved locally'));
        });
    }
}

function applyTheme(theme) {
    const htmlElement = document.documentElement;
    htmlElement.setAttribute('data-bs-theme', theme);
    document.body.style.transition = 'background-color 0.3s ease, color 0.3s ease';
    
    // Update Bootstrap theme
    if (typeof bootstrap !== 'undefined') {
        document.querySelectorAll('.btn-close').forEach(el => {
            el.style.filter = theme === 'dark' ? 'invert(1)' : 'none';
        });
    }
}

function updateThemeIcon(theme, iconElement, thumbElement) {
    if (!iconElement) return;
    
    if (theme === 'dark') {
        iconElement.className = 'fas fa-sun';
        if (thumbElement) {
            thumbElement.parentElement.classList.add('dark');
        }
    } else {
        iconElement.className = 'fas fa-moon';
        if (thumbElement) {
            thumbElement.parentElement.classList.remove('dark');
        }
    }
}

// ============================================
// 3. SIDEBAR MANAGEMENT
// ============================================
function initSidebar() {
    const sidebarToggle = document.getElementById('sidebarToggle');
    const sidebar = document.getElementById('sidebar');
    
    if (sidebarToggle && sidebar) {
        // Toggle sidebar on button click
        sidebarToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            sidebar.classList.toggle('show');
        });
        
        // Close sidebar on outside click (mobile)
        document.addEventListener('click', function(e) {
            if (window.innerWidth <= 992) {
                if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                    sidebar.classList.remove('show');
                }
            }
        });
        
        // Close sidebar on escape key
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape' && sidebar.classList.contains('show')) {
                sidebar.classList.remove('show');
            }
        });
    }
    
    // Highlight current page in sidebar
    highlightCurrentPage();
}

function highlightCurrentPage() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.sidebar-menu .nav-link');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && href !== '#' && currentPath.includes(href)) {
            link.closest('.nav-item').classList.add('active');
        }
    });
}

// ============================================
// 4. NOTIFICATION SYSTEM
// ============================================
function initNotifications() {
    const notificationBtn = document.getElementById('notificationBtn');
    const notificationCount = document.getElementById('notificationCount');
    
    if (notificationBtn) {
        notificationBtn.addEventListener('click', function() {
            loadNotifications();
        });
    }
    
    // Initial load
    loadNotifications();
    
    // Auto-refresh notifications every 60 seconds
    setInterval(loadNotifications, 60000);
}

function loadNotifications() {
    fetch('/api/notifications')
        .then(response => response.json())
        .then(data => {
            const count = document.getElementById('notificationCount');
            if (count) {
                count.textContent = data.length;
                if (data.length > 0) {
                    count.style.display = 'flex';
                    count.style.animation = 'pulse-dot 2s infinite';
                } else {
                    count.style.display = 'none';
                }
            }
            
            // Show notification dropdown if available
            const notificationList = document.getElementById('notificationList');
            if (notificationList) {
                renderNotifications(data, notificationList);
            }
        })
        .catch(error => console.error('Error loading notifications:', error));
}

function renderNotifications(notifications, container) {
    container.innerHTML = '';
    
    if (notifications.length === 0) {
        container.innerHTML = `
            <div class="text-center text-muted py-3">
                <i class="fas fa-bell-slash fa-2x mb-2 d-block"></i>
                <small>No new notifications</small>
            </div>
        `;
        return;
    }
    
    notifications.forEach(notification => {
        const item = document.createElement('div');
        item.className = 'notification-item p-3 border-bottom';
        item.style.cursor = 'pointer';
        item.innerHTML = `
            <div class="d-flex align-items-start">
                <div class="me-2">
                    <i class="fas ${getNotificationIcon(notification.type)} text-${getNotificationColor(notification.type)}"></i>
                </div>
                <div class="flex-grow-1">
                    <div class="fw-semibold">${notification.title}</div>
                    <small class="text-muted">${notification.message}</small>
                    <br>
                    <small class="text-muted" style="font-size: 0.7rem;">${notification.created_at}</small>
                </div>
                <button class="btn btn-sm btn-outline-secondary" onclick="markNotificationRead(${notification.id})">
                    <i class="fas fa-check"></i>
                </button>
            </div>
        `;
        container.appendChild(item);
    });
}

function getNotificationIcon(type) {
    const icons = {
        'info': 'fa-info-circle',
        'success': 'fa-check-circle',
        'warning': 'fa-exclamation-triangle',
        'danger': 'fa-times-circle'
    };
    return icons[type] || 'fa-bell';
}

function getNotificationColor(type) {
    const colors = {
        'info': 'info',
        'success': 'success',
        'warning': 'warning',
        'danger': 'danger'
    };
    return colors[type] || 'primary';
}

function markNotificationRead(id) {
    fetch(`/api/notifications/read/${id}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            loadNotifications();
            showToast('Notification marked as read', 'success');
        }
    })
    .catch(error => console.error('Error:', error));
}

// ============================================
// 5. TOAST NOTIFICATIONS
// ============================================
function showToast(message, type = 'info', duration = 5000) {
    const container = document.getElementById('toastContainer');
    if (!container) {
        // Create container if it doesn't exist
        const newContainer = document.createElement('div');
        newContainer.id = 'toastContainer';
        newContainer.className = 'toast-container';
        document.body.appendChild(newContainer);
        return showToast(message, type, duration);
    }
    
    const toast = document.createElement('div');
    toast.className = 'toast-custom animate-fade-in';
    
    const icons = {
        success: 'fa-check-circle',
        danger: 'fa-exclamation-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };
    
    const colors = {
        success: '#00b894',
        danger: '#e17055',
        warning: '#fdcb6e',
        info: '#667eea'
    };
    
    toast.innerHTML = `
        <div style="display: flex; align-items: center; gap: 12px; width: 100%;">
            <i class="fas ${icons[type] || icons.info}" style="color: ${colors[type] || colors.info}; font-size: 1.2rem;"></i>
            <span style="flex: 1;">${message}</span>
            <button onclick="this.parentElement.parentElement.remove()" style="background: none; border: none; color: var(--text-muted); cursor: pointer; padding: 5px;">
                <i class="fas fa-times"></i>
            </button>
        </div>
    `;
    
    container.appendChild(toast);
    
    // Auto-remove after duration
    setTimeout(() => {
        if (toast.parentNode) {
            toast.style.animation = 'slideOutRight 0.5s ease forwards';
            setTimeout(() => {
                if (toast.parentNode) {
                    toast.remove();
                }
            }, 500);
        }
    }, duration);
}

// ============================================
// 6. CHARTS
// ============================================
function initCharts() {
    // Sales chart
    const salesChartEl = document.getElementById('salesChart');
    if (salesChartEl) {
        createSalesChart(salesChartEl);
    }
    
    // Revenue chart
    const revenueChartEl = document.getElementById('revenueChart');
    if (revenueChartEl) {
        createRevenueChart(revenueChartEl);
    }
    
    // Category chart
    const categoryChartEl = document.getElementById('categoryChart');
    if (categoryChartEl) {
        createCategoryChart(categoryChartEl);
    }
}

function createSalesChart(element) {
    const ctx = element.getContext('2d');
    
    // Get data from data attributes or use default
    const labels = JSON.parse(element.dataset.labels || '["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]');
    const data = JSON.parse(element.dataset.data || '[0,0,0,0,0,0,0]');
    
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Sales Revenue',
                data: data,
                borderColor: '#667eea',
                backgroundColor: 'rgba(102, 126, 234, 0.1)',
                fill: true,
                tension: 0.4,
                pointBackgroundColor: '#667eea',
                pointBorderColor: '#ffffff',
                pointBorderWidth: 2,
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    backgroundColor: 'rgba(0,0,0,0.8)',
                    titleColor: '#fff',
                    bodyColor: '#fff',
                    cornerRadius: 10,
                    padding: 12
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return 'PKR ' + value.toLocaleString();
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            },
            interaction: {
                intersect: false,
                mode: 'index'
            }
        }
    });
    
    // Save chart instance for later updates
    window.salesChart = chart;
    return chart;
}

function createRevenueChart(element) {
    const ctx = element.getContext('2d');
    
    const chart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Sales', 'Photocopy', 'Other'],
            datasets: [{
                data: [70, 20, 10],
                backgroundColor: ['#667eea', '#00b894', '#fdcb6e'],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 20,
                        usePointStyle: true,
                        pointStyle: 'circle'
                    }
                }
            },
            cutout: '70%'
        }
    });
    
    window.revenueChart = chart;
    return chart;
}

function createCategoryChart(element) {
    const ctx = element.getContext('2d');
    
    const chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Screen Protectors', 'Cases', 'Cables', 'Chargers', 'Accessories'],
            datasets: [{
                label: 'Sales by Category',
                data: [120, 85, 60, 45, 30],
                backgroundColor: [
                    'rgba(102, 126, 234, 0.8)',
                    'rgba(0, 184, 148, 0.8)',
                    'rgba(253, 203, 110, 0.8)',
                    'rgba(225, 112, 85, 0.8)',
                    'rgba(0, 206, 201, 0.8)'
                ],
                borderColor: [
                    '#667eea',
                    '#00b894',
                    '#fdcb6e',
                    '#e17055',
                    '#00cec9'
                ],
                borderWidth: 1,
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0,0,0,0.05)'
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });
    
    window.categoryChart = chart;
    return chart;
}

// ============================================
// 7. DATA TABLES
// ============================================
function initDataTables() {
    // Find all tables with data-table class
    document.querySelectorAll('.data-table').forEach(function(table) {
        const options = {
            responsive: true,
            pageLength: 25,
            language: {
                search: "Search:",
                lengthMenu: "Show _MENU_ entries",
                info: "Showing _START_ to _END_ of _TOTAL_ entries",
                infoEmpty: "No entries found",
                infoFiltered: "(filtered from _MAX_ total entries)",
                zeroRecords: "No matching records found",
                emptyTable: "No data available in table"
            },
            columnDefs: [
                { orderable: false, targets: table.dataset.noSort ? table.dataset.noSort.split(',') : [] }
            ]
        };
        
        // Initialize DataTable
        $(table).DataTable(options);
    });
}

// ============================================
// 8. FORM VALIDATION
// ============================================
function initFormValidation() {
    // Form validation for all forms
    document.querySelectorAll('form[data-validate]').forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!validateForm(this)) {
                e.preventDefault();
                return false;
            }
        });
    });
    
    // Real-time validation for required fields
    document.querySelectorAll('input[required], select[required], textarea[required]').forEach(function(field) {
        field.addEventListener('blur', function() {
            validateField(this);
        });
        
        field.addEventListener('input', function() {
            if (this.classList.contains('is-invalid')) {
                validateField(this);
            }
        });
    });
}

function validateForm(form) {
    let isValid = true;
    const requiredFields = form.querySelectorAll('[required]');
    
    requiredFields.forEach(function(field) {
        if (!validateField(field)) {
            isValid = false;
        }
    });
    
    return isValid;
}

function validateField(field) {
    const value = field.value.trim();
    const isValid = value.length > 0;
    
    if (!isValid) {
        field.classList.add('is-invalid');
        field.classList.remove('is-valid');
        
        // Show error message
        const feedback = field.nextElementSibling;
        if (feedback && feedback.classList.contains('invalid-feedback')) {
            feedback.style.display = 'block';
        }
    } else {
        field.classList.remove('is-invalid');
        field.classList.add('is-valid');
        
        const feedback = field.nextElementSibling;
        if (feedback && feedback.classList.contains('invalid-feedback')) {
            feedback.style.display = 'none';
        }
    }
    
    return isValid;
}

// ============================================
// 9. SEARCH FUNCTIONALITY
// ============================================
function initSearch() {
    const searchInput = document.getElementById('globalSearch');
    if (searchInput) {
        // Search on enter key
        searchInput.addEventListener('keyup', function(e) {
            if (e.key === 'Enter') {
                performSearch(this.value);
            }
        });
        
        // Debounced search
        let searchTimeout;
        searchInput.addEventListener('input', function() {
            clearTimeout(searchTimeout);
            searchTimeout = setTimeout(() => {
                const query = this.value.trim();
                if (query.length >= 3) {
                    performSearch(query);
                }
            }, 500);
        });
    }
}

function performSearch(query) {
    if (query.length === 0) {
        return;
    }
    
    // Show loading state
    showToast('Searching for: ' + query, 'info');
    
    // Redirect to products page with search query
    window.location.href = '/products?search=' + encodeURIComponent(query);
}

// ============================================
// 10. KEYBOARD SHORTCUTS
// ============================================
function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // Ctrl+N - New Sale
        if (e.ctrlKey && e.key === 'n') {
            e.preventDefault();
            window.location.href = '/new_sale';
        }
        
        // Ctrl+P - New Photocopy
        if (e.ctrlKey && e.key === 'p') {
            e.preventDefault();
            window.location.href = '/new_photocopy';
        }
        
        // Ctrl+Shift+D - Dashboard
        if (e.ctrlKey && e.shiftKey && e.key === 'd') {
            e.preventDefault();
            window.location.href = '/dashboard';
        }
        
        // Escape - Close modals
        if (e.key === 'Escape') {
            const openModal = document.querySelector('.modal.show');
            if (openModal) {
                const modal = bootstrap.Modal.getInstance(openModal);
                if (modal) {
                    modal.hide();
                }
            }
        }
    });
}

// ============================================
// 11. AUTO REFRESH
// ============================================
function initAutoRefresh() {
    // Only on dashboard page
    if (window.location.pathname === '/dashboard') {
        let refreshInterval = 60000; // 60 seconds
        
        // Check if auto-refresh is enabled
        const autoRefresh = localStorage.getItem('autoRefresh') !== 'false';
        
        if (autoRefresh) {
            setInterval(function() {
                // Only refresh if page is visible
                if (!document.hidden) {
                    // Show subtle update
                    showToast('🔄 Refreshing data...', 'info', 2000);
                    
                    // Refresh specific sections via AJAX instead of full page reload
                    refreshDashboardData();
                }
            }, refreshInterval);
        }
    }
}

function refreshDashboardData() {
    // Fetch updated stats
    fetch('/api/dashboard/stats')
        .then(response => response.json())
        .then(data => {
            // Update stats without page reload
            updateDashboardStats(data);
            showToast('✅ Dashboard updated', 'success', 1500);
        })
        .catch(error => {
            console.error('Error refreshing dashboard:', error);
            // Fallback to full page reload
            location.reload();
        });
}

function updateDashboardStats(data) {
    // Update stat cards
    const statElements = document.querySelectorAll('.stat-number');
    if (statElements.length >= 4) {
        statElements[0].textContent = data.total_sales_today.toLocaleString();
        statElements[1].textContent = data.total_sales_count;
        statElements[2].textContent = data.low_stock_count;
    }
}

// ============================================
// 12. TOOLTIPS AND POPOVERS
// ============================================
function initTooltips() {
    // Initialize Bootstrap tooltips
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl, {
                trigger: 'hover',
                placement: 'auto'
            });
        });
    }
}

function initPopovers() {
    // Initialize Bootstrap popovers
    if (typeof bootstrap !== 'undefined' && bootstrap.Popover) {
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function(popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    }
}

// ============================================
// 13. PRODUCT MANAGEMENT
// ============================================
// Delete product with confirmation
function deleteProduct(productId, productName) {
    Swal.fire({
        title: 'Delete Product?',
        text: `Are you sure you want to delete "${productName}"?`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#e17055',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Yes, delete it!',
        showLoaderOnConfirm: true,
        preConfirm: () => {
            return fetch(`/delete_product/${productId}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    return data;
                } else {
                    throw new Error('Failed to delete product');
                }
            })
            .catch(error => {
                Swal.showValidationMessage(`Error: ${error.message}`);
            });
        },
        allowOutsideClick: () => !Swal.isLoading()
    }).then((result) => {
        if (result.isConfirmed) {
            showToast('Product deleted successfully', 'success');
            location.reload();
        }
    });
}

// Bulk delete products
function bulkDeleteProducts() {
    const selected = document.querySelectorAll('.product-checkbox:checked');
    if (selected.length === 0) {
        showToast('Please select at least one product', 'warning');
        return;
    }
    
    const productIds = Array.from(selected).map(el => el.value);
    const productNames = Array.from(selected).map(el => {
        const row = el.closest('tr');
        return row ? row.querySelector('td:nth-child(2)')?.textContent || 'Product' : 'Product';
    });
    
    Swal.fire({
        title: 'Bulk Delete?',
        text: `You are about to delete ${selected.length} product(s)`,
        icon: 'warning',
        showCancelButton: true,
        confirmButtonColor: '#e17055',
        cancelButtonColor: '#6c757d',
        confirmButtonText: 'Yes, delete all!',
        showLoaderOnConfirm: true,
        preConfirm: () => {
            return fetch('/products/bulk_delete', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ product_ids: productIds })
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    return data;
                } else {
                    throw new Error('Failed to delete products');
                }
            })
            .catch(error => {
                Swal.showValidationMessage(`Error: ${error.message}`);
            });
        },
        allowOutsideClick: () => !Swal.isLoading()
    }).then((result) => {
        if (result.isConfirmed) {
            showToast(`${selected.length} products deleted successfully`, 'success');
            location.reload();
        }
    });
}

// ============================================
// 14. SALE MANAGEMENT
// ============================================
// Print receipt
function printReceipt(saleId) {
    const printWindow = window.open(`/sale/${saleId}/receipt`, '_blank', 'width=400,height=600');
    if (printWindow) {
        printWindow.onload = function() {
            printWindow.print();
        };
    } else {
        showToast('Please allow popups to print receipts', 'warning');
    }
}

// Validate sale before submission
function validateSale() {
    const items = document.querySelectorAll('.product-select');
    let hasItems = false;
    
    items.forEach(select => {
        if (select.value) hasItems = true;
    });
    
    if (!hasItems) {
        showToast('Please add at least one product to the sale', 'warning');
        return false;
    }
    
    // Check stock
    let hasError = false;
    document.querySelectorAll('.product-select').forEach(select => {
        if (select.value) {
            const option = select.options[select.selectedIndex];
            const stock = parseInt(option.dataset.stock) || 0;
            const quantity = parseInt(select.closest('tr').querySelector('.quantity-input').value) || 0;
            
            if (quantity > stock) {
                showToast(`Not enough stock for ${option.text}. Available: ${stock}`, 'danger');
                hasError = true;
            }
        }
    });
    
    return !hasError;
}

// ============================================
// 15. CUSTOMER MANAGEMENT
// ============================================
// Add customer from modal
function addCustomerFromModal(form) {
    const formData = new FormData(form);
    
    fetch('/add_customer', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('Customer added successfully', 'success');
            location.reload();
        } else {
            showToast(data.message || 'Failed to add customer', 'danger');
        }
    })
    .catch(error => {
        showToast('Error adding customer', 'danger');
        console.error('Error:', error);
    });
}

// ============================================
// 16. PHOTOCOPY MANAGEMENT
// ============================================
// Calculate photocopy total
function calculatePhotocopyTotal() {
    const pages = parseInt(document.querySelector('input[name="total_pages"]')?.value) || 0;
    const rate = parseFloat(document.getElementById('ratePerPage')?.value) || 0;
    const copies = parseInt(document.querySelector('input[name="copies"]')?.value) || 1;
    
    const total = pages * rate * copies;
    const totalInput = document.getElementById('totalAmount');
    if (totalInput) {
        totalInput.value = total.toFixed(2);
    }
    return total;
}

// Update rate based on page type
function updatePhotocopyRate() {
    const pageType = document.querySelector('select[name="page_type"]')?.value;
    const rateInput = document.getElementById('ratePerPage');
    
    if (!rateInput) return;
    
    if (pageType === 'b&w') {
        rateInput.value = 5;
    } else if (pageType === 'color') {
        rateInput.value = 15;
    }
    
    calculatePhotocopyTotal();
}

// ============================================
// 17. EXPENSE MANAGEMENT
// ============================================
// Add expense category from form
function addExpenseCategory(category) {
    const select = document.querySelector('select[name="category"]');
    if (select) {
        const option = document.createElement('option');
        option.value = category;
        option.textContent = category;
        select.appendChild(option);
        select.value = category;
    }
}

// ============================================
// 18. REPORT FUNCTIONS
// ============================================
// Export report to CSV
function exportToCSV(tableId, filename = 'report.csv') {
    const table = document.getElementById(tableId);
    if (!table) {
        showToast('Table not found', 'danger');
        return;
    }
    
    let csv = [];
    const rows = table.querySelectorAll('tr');
    
    rows.forEach(row => {
        const rowData = [];
        const cols = row.querySelectorAll('td, th');
        cols.forEach(col => {
            rowData.push(col.textContent.trim());
        });
        csv.push(rowData.join(','));
    });
    
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename;
    link.click();
    
    showToast('Report exported successfully', 'success');
}

// Print report
function printReport() {
    window.print();
}

// ============================================
// 19. SETTINGS FUNCTIONS
// ============================================
// Save settings
function saveSettings(form) {
    const formData = new FormData(form);
    
    fetch('/settings/preferences', {
        method: 'POST',
        body: formData
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            showToast('Settings saved successfully', 'success');
            if (data.theme) {
                applyTheme(data.theme);
                localStorage.setItem('shopTheme', data.theme);
            }
        } else {
            showToast('Failed to save settings', 'danger');
        }
    })
    .catch(error => {
        showToast('Error saving settings', 'danger');
        console.error('Error:', error);
    });
}

// ============================================
// 20. UTILITY FUNCTIONS
// ============================================
// Format currency
function formatCurrency(amount) {
    return new Intl.NumberFormat('en-PK', {
        style: 'currency',
        currency: 'PKR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0
    }).format(amount);
}

// Format date
function formatDate(dateString) {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-PK', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Get relative time
function getRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = Math.floor((now - date) / 1000);
    
    if (diff < 60) return 'Just now';
    if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
    if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
    return formatDate(dateString);
}

// Show loading overlay
function showLoading(message = 'Loading...') {
    Swal.fire({
        title: message,
        allowOutsideClick: false,
        didOpen: () => {
            Swal.showLoading();
        }
    });
}

// Hide loading overlay
function hideLoading() {
    Swal.close();
}

// Make AJAX request with loading
function ajaxRequest(url, method = 'GET', data = null, showLoader = true) {
    if (showLoader) showLoading();
    
    const options = {
        method: method,
        headers: {
            'Content-Type': 'application/json',
        }
    };
    
    if (data) {
        options.body = JSON.stringify(data);
    }
    
    return fetch(url, options)
        .then(response => {
            if (showLoader) hideLoading();
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .catch(error => {
            if (showLoader) hideLoading();
            throw error;
        });
}

// ============================================
// 21. EVENT DELEGATION
// ============================================
// Handle dynamic content events
document.addEventListener('click', function(e) {
    // Delete button
    if (e.target.closest('.btn-delete')) {
        const btn = e.target.closest('.btn-delete');
        const url = btn.dataset.url;
        const name = btn.dataset.name || 'item';
        if (url) {
            deleteProduct(url, name);
        }
    }
    
    // Print button
    if (e.target.closest('.btn-print')) {
        const btn = e.target.closest('.btn-print');
        const id = btn.dataset.id;
        if (id) {
            printReceipt(id);
        }
    }
    
    // Theme toggle via button
    if (e.target.closest('.theme-toggle-btn')) {
        const btn = e.target.closest('.theme-toggle-btn');
        const theme = btn.dataset.theme;
        if (theme) {
            applyTheme(theme);
            localStorage.setItem('shopTheme', theme);
            showToast(`Theme switched to ${theme}`, 'info');
        }
    }
});

// ============================================
// 22. CONSOLE HELPERS (Debug)
// ============================================
// Expose useful functions to console for debugging
window.debug = {
    theme: {
        toggle: () => {
            const current = document.documentElement.getAttribute('data-bs-theme');
            const next = current === 'light' ? 'dark' : 'light';
            applyTheme(next);
            localStorage.setItem('shopTheme', next);
            console.log(`Theme switched to: ${next}`);
        },
        current: () => document.documentElement.getAttribute('data-bs-theme')
    },
    notifications: {
        load: loadNotifications,
        show: (message, type) => showToast(message, type)
    },
    charts: {
        update: () => {
            if (window.salesChart) window.salesChart.update();
            if (window.revenueChart) window.revenueChart.update();
            if (window.categoryChart) window.categoryChart.update();
            console.log('Charts updated');
        }
    },
    data: {
        refresh: () => {
            location.reload();
        }
    }
};

console.log('💡 Type "debug" in console for debugging tools');
console.log('📋 Available commands:');
console.log('  debug.theme.toggle() - Toggle theme');
console.log('  debug.notifications.load() - Load notifications');
console.log('  debug.charts.update() - Update charts');
console.log('  debug.data.refresh() - Refresh page');

// ============================================
// 23. SERVICE WORKER REGISTRATION (Optional)
// ============================================
// Register service worker for PWA support
if ('serviceWorker' in navigator) {
    // Uncomment to enable PWA support
    // navigator.serviceWorker.register('/sw.js')
    //     .then(reg => console.log('Service Worker registered'))
    //     .catch(err => console.log('Service Worker registration failed:', err));
}

// ============================================
// 24. ANALYTICS (Optional)
// ============================================
// Track page views
function trackPageView(page) {
    if (window.gtag) {
        window.gtag('config', 'GA-XXXXX', {
            page_path: page
        });
    }
}

// ============================================
// 25. INITIALIZATION COMPLETE
// ============================================
console.log('✅ All systems initialized');
console.log('📊 Ready to manage your shop!');

// Export global functions for use in HTML
window.showToast = showToast;
window.deleteProduct = deleteProduct;
window.bulkDeleteProducts = bulkDeleteProducts;
window.printReceipt = printReceipt;
window.validateSale = validateSale;
window.formatCurrency = formatCurrency;
window.formatDate = formatDate;
window.getRelativeTime = getRelativeTime;
window.ajaxRequest = ajaxRequest;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.exportToCSV = exportToCSV;
window.printReport = printReport;
window.saveSettings = saveSettings;
window.calculatePhotocopyTotal = calculatePhotocopyTotal;
window.updatePhotocopyRate = updatePhotocopyRate;
window.markNotificationRead = markNotificationRead;