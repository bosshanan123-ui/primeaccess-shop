// ============================================
// PRIMEACCESS - Custom JavaScript v2.0
// ============================================

document.addEventListener('DOMContentLoaded', function() {
    
    // ============================================
    // 1. PAGE LOADER
    // ============================================
    const loader = document.getElementById('pageLoader');
    if (loader) {
        setTimeout(() => {
            loader.classList.add('hidden');
        }, 500);
    }

    // ============================================
    // 2. ANIMATED STATISTICS CARDS (Count Up)
    // ============================================
    function animateNumbers() {
        document.querySelectorAll('.stat-number[data-count]').forEach(el => {
            const target = parseFloat(el.dataset.count);
            if (isNaN(target)) return;
            
            const duration = 1500;
            const startTime = performance.now();
            const isCurrency = el.dataset.currency === 'true';
            
            function update(currentTime) {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                
                // Easing function
                const ease = 1 - Math.pow(1 - progress, 3);
                const current = target * ease;
                
                if (isCurrency) {
                    el.textContent = 'PKR ' + Math.round(current).toLocaleString();
                } else {
                    el.textContent = Math.round(current).toLocaleString();
                }
                
                if (progress < 1) {
                    requestAnimationFrame(update);
                }
            }
            
            requestAnimationFrame(update);
        });
    }

    // ============================================
    // 3. ANIMATE ON SCROLL (Intersection Observer)
    // ============================================
    function setupScrollAnimations() {
        const elements = document.querySelectorAll('.animate-on-scroll');
        
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animated');
                    observer.unobserve(entry.target);
                }
            });
        }, {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        });
        
        elements.forEach(el => observer.observe(el));
    }

    // ============================================
    // 4. FLOATING ACTION BUTTON
    // ============================================
    const fabToggle = document.getElementById('fabToggle');
    const fabContainer = document.querySelector('.fab-container');
    
    if (fabToggle && fabContainer) {
        fabToggle.addEventListener('click', function() {
            fabContainer.classList.toggle('open');
        });
        
        // Close FAB on outside click
        document.addEventListener('click', function(e) {
            if (!fabContainer.contains(e.target)) {
                fabContainer.classList.remove('open');
            }
        });
    }

    // ============================================
    // 5. SIDEBAR SEARCH
    // ============================================
    const sidebarSearch = document.getElementById('sidebarSearch');
    if (sidebarSearch) {
        sidebarSearch.addEventListener('input', function() {
            const query = this.value.toLowerCase();
            const items = document.querySelectorAll('.sidebar-menu .nav-item:not(.menu-label)');
            
            items.forEach(item => {
                const text = item.textContent.toLowerCase();
                if (text.includes(query)) {
                    item.style.display = '';
                } else {
                    item.style.display = 'none';
                }
            });
        });
    }

    // ============================================
    // 6. COLLAPSIBLE SUB-MENUS
    // ============================================
    document.querySelectorAll('.sidebar-menu .nav-item.has-sub .nav-link').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const parent = this.closest('.nav-item.has-sub');
            parent.classList.toggle('open');
        });
    });

    // ============================================
    // 7. RECENT ACTIVITY FEED (Auto-refresh)
    // ============================================
    function loadRecentActivity() {
        const container = document.getElementById('recentActivity');
        if (!container) return;
        
        fetch('/api/recent-activity')
            .then(response => response.json())
            .then(data => {
                // Update activity feed
                container.innerHTML = data.map(item => `
                    <div class="activity-item animate-fade-in">
                        <div class="activity-icon ${item.type}">
                            <i class="fas fa-${item.icon}"></i>
                        </div>
                        <div class="activity-content">
                            <p class="activity-text">${item.text}</p>
                            <small class="activity-time">${item.time}</small>
                        </div>
                    </div>
                `).join('');
            })
            .catch(err => console.log('Activity feed: ', err));
    }

    // Auto-refresh every 30 seconds
    if (document.getElementById('recentActivity')) {
        loadRecentActivity();
        setInterval(loadRecentActivity, 30000);
    }

    // ============================================
    // 8. QUICK ACTION SHORTCUTS (Keyboard)
    // ============================================
    document.addEventListener('keydown', function(e) {
        // Ctrl + N = New Sale
        if (e.ctrlKey && e.key === 'n') {
            e.preventDefault();
            window.location.href = '/new_sale';
        }
        // Ctrl + P = New Purchase
        if (e.ctrlKey && e.key === 'p') {
            e.preventDefault();
            window.location.href = '/new_purchase';
        }
        // Ctrl + C = New Customer
        if (e.ctrlKey && e.key === 'c') {
            e.preventDefault();
            window.location.href = '/add_customer';
        }
        // Ctrl + F = Focus Search
        if (e.ctrlKey && e.key === 'f') {
            e.preventDefault();
            const search = document.querySelector('.search-box input, #sidebarSearch');
            if (search) search.focus();
        }
        // Escape = Close FAB
        if (e.key === 'Escape') {
            const fab = document.querySelector('.fab-container');
            if (fab) fab.classList.remove('open');
        }
    });

    // ============================================
    // 9. NOTIFICATION BADGE UPDATE
    // ============================================
    function updateNotificationBadge() {
        fetch('/api/notifications/count')
            .then(response => response.json())
            .then(data => {
                const badge = document.getElementById('notificationCount');
                if (badge) {
                    badge.textContent = data.count || 0;
                    badge.style.display = data.count > 0 ? 'flex' : 'none';
                }
            })
            .catch(err => console.log('Notification badge: ', err));
    }

    // Update every 60 seconds
    if (document.getElementById('notificationCount')) {
        updateNotificationBadge();
        setInterval(updateNotificationBadge, 60000);
    }

    // ============================================
    // 10. THEME SELECTOR
    // ============================================
    function setTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
    }

    function getTheme() {
        return localStorage.getItem('theme') || 'default';
    }

    // Apply saved theme
    const savedTheme = getTheme();
    setTheme(savedTheme);

    // Theme selector buttons
    document.querySelectorAll('.theme-option').forEach(btn => {
        btn.addEventListener('click', function() {
            const theme = this.dataset.theme;
            setTheme(theme);
            // Update active state
            document.querySelectorAll('.theme-option').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });

    // ============================================
    // 11. TOOLTIP INITIALIZATION
    // ============================================
    document.querySelectorAll('[data-tooltip]').forEach(el => {
        el.addEventListener('mouseenter', function(e) {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip-custom';
            tooltip.textContent = this.dataset.tooltip;
            tooltip.style.position = 'fixed';
            tooltip.style.background = 'var(--bg-card)';
            tooltip.style.color = 'var(--text-primary)';
            tooltip.style.padding = '6px 12px';
            tooltip.style.borderRadius = '6px';
            tooltip.style.fontSize = '0.7rem';
            tooltip.style.border = '1px solid var(--border-color)';
            tooltip.style.boxShadow = 'var(--shadow-md)';
            tooltip.style.zIndex = '9999';
            tooltip.style.pointerEvents = 'none';
            tooltip.style.transition = 'opacity 0.2s';
            
            const rect = this.getBoundingClientRect();
            tooltip.style.left = rect.left + rect.width/2 - tooltip.offsetWidth/2 + 'px';
            tooltip.style.top = rect.top - 30 + 'px';
            
            document.body.appendChild(tooltip);
            
            this.addEventListener('mouseleave', function() {
                tooltip.remove();
            }, { once: true });
        });
    });

    // ============================================
    // 12. SALES FORECAST CHART (Demo)
    // ============================================
    function initForecastChart() {
        const canvas = document.getElementById('forecastChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        // Chart.js will be initialized if available
        if (typeof Chart !== 'undefined') {
            new Chart(ctx, {
                type: 'line',
                data: {
                    labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
                    datasets: [{
                        label: 'Actual Sales',
                        data: [12000, 15000, 18000, 14000, 20000, 25000, 22000],
                        borderColor: '#0088FF',
                        backgroundColor: 'rgba(0, 136, 255, 0.05)',
                        fill: true,
                        tension: 0.4
                    }, {
                        label: 'Forecast',
                        data: [11000, 16000, 17000, 15000, 21000, 24000, 23000],
                        borderColor: '#6C63FF',
                        backgroundColor: 'rgba(108, 99, 255, 0.05)',
                        fill: true,
                        tension: 0.4,
                        borderDash: [6, 4]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: {
                            labels: {
                                color: 'var(--text-secondary)',
                                font: { size: 11 }
                            }
                        }
                    },
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                color: 'var(--text-muted)',
                                callback: function(value) {
                                    return 'PKR ' + value.toLocaleString();
                                }
                            },
                            grid: {
                                color: 'var(--border-color)'
                            }
                        },
                        x: {
                            ticks: {
                                color: 'var(--text-muted)'
                            },
                            grid: {
                                color: 'var(--border-color)'
                            }
                        }
                    }
                }
            });
        }
    }

    // Initialize forecast chart
    if (document.getElementById('forecastChart')) {
        setTimeout(initForecastChart, 300);
    }

    // ============================================
    // 13. TOP CUSTOMERS WIDGET
    // ============================================
    function loadTopCustomers() {
        const container = document.getElementById('topCustomers');
        if (!container) return;
        
        fetch('/api/top-customers')
            .then(response => response.json())
            .then(data => {
                container.innerHTML = data.map((customer, index) => `
                    <div class="top-customer-item">
                        <div class="rank">#${index + 1}</div>
                        <img src="https://ui-avatars.com/api/?name=${customer.name}&background=0088FF&color=fff&size=32" 
                             alt="${customer.name}" class="avatar">
                        <div class="info">
                            <div class="name">${customer.name}</div>
                            <div class="purchases">${customer.total_purchases} purchases</div>
                        </div>
                        <div class="amount">PKR ${customer.total_spent.toLocaleString()}</div>
                    </div>
                `).join('');
            })
            .catch(err => console.log('Top customers: ', err));
    }

    if (document.getElementById('topCustomers')) {
        loadTopCustomers();
    }

    // ============================================
    // 14. KEYBOARD SHORTCUTS HELP
    // ============================================
    document.addEventListener('keydown', function(e) {
        // Ctrl + / = Show shortcuts
        if (e.ctrlKey && e.key === '/') {
            e.preventDefault();
            showToast('⌨️ Ctrl+N: New Sale | Ctrl+P: New Purchase | Ctrl+C: New Customer | Ctrl+F: Search', 'info');
        }
    });

    // ============================================
    // 15. CONSOLE WELCOME
    // ============================================
    console.log('%c🚀 PRIMEACCESS v2.0', 'font-size:20px; font-weight:bold; color:#0088FF;');
    console.log('%c🔑 Shortcuts: Ctrl+N (New Sale) | Ctrl+P (New Purchase) | Ctrl+F (Search)', 'font-size:12px; color:#6C63FF;');
    console.log('%c💡 Type /help for more commands', 'font-size:12px; color:#8A9AAA;');

    // ============================================
    // 16. INITIALIZE ALL
    // ============================================
    // Run animations
    setTimeout(animateNumbers, 300);
    setupScrollAnimations();

    console.log('✅ All components initialized!');
});