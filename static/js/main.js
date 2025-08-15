// Modern URL Shortener JavaScript

class URLShortener {
    constructor() {
        this.init();
    }

    init() {
        this.setupThemeToggle();
        this.setupFormHandling();
        this.setupCopyFunctionality();
        this.setupAnimations();
        this.loadTheme();
    }

    // Theme management
    setupThemeToggle() {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.addEventListener('click', () => this.toggleTheme());
        }
    }

    toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
        
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        
        // Update theme toggle icon
        this.updateThemeIcon(newTheme);
        
        // Add transition effect
        document.body.style.transition = 'all 0.3s ease';
        setTimeout(() => {
            document.body.style.transition = '';
        }, 300);
    }

    loadTheme() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        document.documentElement.setAttribute('data-theme', savedTheme);
        this.updateThemeIcon(savedTheme);
    }

    updateThemeIcon(theme) {
        const themeToggle = document.getElementById('theme-toggle');
        if (themeToggle) {
            themeToggle.innerHTML = theme === 'dark' ? '☀️' : '🌙';
        }
    }

    // Form handling
    setupFormHandling() {
        const form = document.getElementById('url-form');
        if (form) {
            form.addEventListener('submit', (e) => this.handleFormSubmit(e));
        }

        // Real-time URL validation
        const urlInput = document.getElementById('url-input');
        if (urlInput) {
            urlInput.addEventListener('input', (e) => this.validateURL(e.target.value));
            urlInput.addEventListener('paste', (e) => {
                setTimeout(() => this.validateURL(e.target.value), 10);
            });
        }
    }

    handleFormSubmit(e) {
        const submitBtn = e.target.querySelector('button[type="submit"]');
        const originalText = submitBtn.innerHTML;
        
        // Show loading state
        submitBtn.innerHTML = '<span class="loading"></span> Shortening...';
        submitBtn.disabled = true;
        
        // The form will submit normally, but we enhance the UX
        setTimeout(() => {
            if (submitBtn) {
                submitBtn.innerHTML = originalText;
                submitBtn.disabled = false;
            }
        }, 2000);
    }

    validateURL(url) {
        const urlInput = document.getElementById('url-input');
        const errorElement = document.getElementById('url-error');
        
        if (!url) {
            this.clearValidation();
            return;
        }

        const urlPattern = /^(https?:\/\/)?([\da-z\.-]+)\.([a-z\.]{2,6})([\/\w \.-]*)*\/?$/;
        const isValid = urlPattern.test(url);
        
        if (isValid) {
            urlInput.style.borderColor = 'var(--success-color)';
            if (errorElement) errorElement.style.display = 'none';
        } else {
            urlInput.style.borderColor = 'var(--error-color)';
            this.showError('Please enter a valid URL');
        }
    }

    clearValidation() {
        const urlInput = document.getElementById('url-input');
        const errorElement = document.getElementById('url-error');
        
        if (urlInput) urlInput.style.borderColor = 'var(--border-color)';
        if (errorElement) errorElement.style.display = 'none';
    }

    showError(message) {
        let errorElement = document.getElementById('url-error');
        if (!errorElement) {
            errorElement = document.createElement('div');
            errorElement.id = 'url-error';
            errorElement.className = 'error';
            const urlInput = document.getElementById('url-input');
            if (urlInput && urlInput.parentNode) {
                urlInput.parentNode.appendChild(errorElement);
            }
        }
        errorElement.innerHTML = `⚠️ ${message}`;
        errorElement.style.display = 'flex';
    }

    // Copy functionality
    setupCopyFunctionality() {
        // Handle copy buttons in results
        document.addEventListener('click', (e) => {
            if (e.target.classList.contains('copy-btn') || e.target.closest('.copy-btn')) {
                e.preventDefault();
                const button = e.target.classList.contains('copy-btn') ? e.target : e.target.closest('.copy-btn');
                this.copyToClipboard(button);
            }
        });
    }

    async copyToClipboard(button) {
        const textToCopy = button.getAttribute('data-copy') || button.previousElementSibling?.value;
        
        if (!textToCopy) return;

        try {
            await navigator.clipboard.writeText(textToCopy);
            this.showCopySuccess(button);
        } catch (err) {
            // Fallback for older browsers
            this.fallbackCopyTextToClipboard(textToCopy, button);
        }
    }

    fallbackCopyTextToClipboard(text, button) {
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.left = '-999999px';
        textArea.style.top = '-999999px';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        
        try {
            document.execCommand('copy');
            this.showCopySuccess(button);
        } catch (err) {
            console.error('Fallback: Oops, unable to copy', err);
        }
        
        document.body.removeChild(textArea);
    }

    showCopySuccess(button) {
        const originalText = button.innerHTML;
        button.innerHTML = '✓ Copied!';
        button.style.background = 'var(--success-color)';
        
        setTimeout(() => {
            button.innerHTML = originalText;
            button.style.background = '';
        }, 2000);
    }

    // Animations
    setupAnimations() {
        // Intersection Observer for scroll animations
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.style.animationPlayState = 'running';
                }
            });
        }, observerOptions);

        // Observe animated elements
        document.querySelectorAll('[class*="animate"]').forEach(el => {
            observer.observe(el);
        });

        // Add hover effects to cards
        this.setupHoverEffects();
    }

    setupHoverEffects() {
        const cards = document.querySelectorAll('.url-card');
        cards.forEach(card => {
            card.addEventListener('mouseenter', () => {
                card.style.transform = 'translateY(-5px) scale(1.02)';
            });
            
            card.addEventListener('mouseleave', () => {
                card.style.transform = 'translateY(0) scale(1)';
            });
        });
    }

    // Utility methods
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <span>${message}</span>
            <button onclick="this.parentElement.remove()">×</button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
            if (notification.parentElement) {
                notification.remove();
            }
        }, 5000);
    }

    // URL preview functionality
    async previewURL(url) {
        try {
            // This would typically call an API to get URL metadata
            // For now, we'll just validate and show basic info
            const urlObj = new URL(url);
            return {
                title: urlObj.hostname,
                description: `Preview for ${urlObj.hostname}`,
                favicon: `https://www.google.com/s2/favicons?domain=${urlObj.hostname}`
            };
        } catch (error) {
            return null;
        }
    }

    // Analytics tracking (placeholder)
    trackEvent(eventName, data = {}) {
        // This would integrate with analytics services
        console.log(`Event: ${eventName}`, data);
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new URLShortener();
});

// Handle SweetAlert2 customization for better integration
if (typeof Swal !== 'undefined') {
    // Custom SweetAlert2 styling
    const swalCustomClass = {
        popup: 'custom-swal-popup',
        title: 'custom-swal-title',
        content: 'custom-swal-content',
        confirmButton: 'custom-swal-confirm',
        cancelButton: 'custom-swal-cancel'
    };

    // Override default SweetAlert2 styling
    Swal.mixin({
        customClass: swalCustomClass,
        buttonsStyling: false
    });
}

// Export for potential module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = URLShortener;
}
