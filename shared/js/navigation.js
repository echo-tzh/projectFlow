// shared/static/js/navigation.js

// Sidebar functionality
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const toggleIcon = document.getElementById('toggleIcon');
    
    sidebar.classList.toggle('collapsed');
    
    if (sidebar.classList.contains('collapsed')) {
        toggleIcon.textContent = '›';
    } else {
        toggleIcon.textContent = '‹';
    }
}

// Sub-navigation toggle
function toggleSubNav(element, event) {
    // Prevent default link behavior only for items with children
    const navItem = element.closest('.nav-item');
    if (navItem && navItem.classList.contains('has-children')) {
        event.preventDefault();
        navItem.classList.toggle('expanded');
    }
}

// Mobile sidebar functions
function openMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    sidebar.classList.add('show');
    overlay.classList.add('show');
    document.body.style.overflow = 'hidden';
}

function closeMobileSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    sidebar.classList.remove('show');
    overlay.classList.remove('show');
    document.body.style.overflow = '';
}

// Auto-hide flash messages
document.addEventListener('DOMContentLoaded', function () {
    const flashMessages = document.querySelectorAll('.flash-message');
    flashMessages.forEach(function (message) {
        setTimeout(function () {
            if (message.parentElement) {
                message.style.animation = 'slideInDown 0.3s ease-out reverse';
                setTimeout(function () {
                    message.remove();
                }, 300);
            }
        }, 5000);
    });
    
    // Initialize navigation state based on current page
    initializeNavigationState();
    
    // Ensure sidebar is visible on desktop - macOS Safari fix
    const sidebar = document.getElementById('sidebar');
    if (sidebar && window.innerWidth > 1024) {
        // Force sidebar to be visible on desktop
        sidebar.style.display = 'block';
        sidebar.style.visibility = 'visible';
        
        // Add a small delay to ensure styles are applied
        setTimeout(function() {
            sidebar.classList.add('sidebar-loaded');
        }, 100);
    }
});

// Initialize navigation state
function initializeNavigationState() {
    // Auto-expand parent nav items if child is active
    const activeSubNavLink = document.querySelector('.sub-nav-link.active');
    if (activeSubNavLink) {
        const parentNavItem = activeSubNavLink.closest('.nav-item');
        if (parentNavItem) {
            parentNavItem.classList.add('expanded');
        }
    }
}

// Handle window resize
window.addEventListener('resize', function() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    
    if (sidebar && overlay) {
        if (window.innerWidth > 1024) {
            // Desktop: ensure mobile states are cleared
            sidebar.classList.remove('show');
            overlay.classList.remove('show');
            document.body.style.overflow = '';
        }
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // Toggle sidebar with Ctrl/Cmd + B
    if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault();
        toggleSidebar();
    }
    
    // Close mobile sidebar with Escape
    if (e.key === 'Escape') {
        closeMobileSidebar();
    }
});

// Smooth scrolling for anchor links
document.addEventListener('DOMContentLoaded', function() {
    const anchorLinks = document.querySelectorAll('a[href^="#"]');
    anchorLinks.forEach(function(link) {
        link.addEventListener('click', function(e) {
            const targetId = this.getAttribute('href').substring(1);
            const targetElement = document.getElementById(targetId);
            
            if (targetElement) {
                e.preventDefault();
                targetElement.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        });
    });
});

//