/**
 * Luminate Cookbook - Frontend JavaScript
 */

// File drag and drop handling
document.addEventListener('DOMContentLoaded', function() {
    setupDragAndDrop();
    setupFormValidation();
});

/**
 * Setup drag and drop for file inputs
 */
function setupDragAndDrop() {
    const dropzones = document.querySelectorAll('[type="file"]');
    
    dropzones.forEach(input => {
        const parent = input.closest('.border-dashed');
        if (!parent) return;
        
        ['dragenter', 'dragover'].forEach(eventName => {
            parent.addEventListener(eventName, (e) => {
                e.preventDefault();
                parent.classList.add('dropzone-active');
            });
        });
        
        ['dragleave', 'drop'].forEach(eventName => {
            parent.addEventListener(eventName, (e) => {
                e.preventDefault();
                parent.classList.remove('dropzone-active');
            });
        });
        
        parent.addEventListener('drop', (e) => {
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                input.files = files;
                input.dispatchEvent(new Event('change'));
            }
        });
    });
}

/**
 * Setup form validation
 */
function setupFormValidation() {
    const forms = document.querySelectorAll('form');
    
    forms.forEach(form => {
        form.addEventListener('submit', (e) => {
            const submitBtn = form.querySelector('[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
                submitBtn.classList.add('loading');
            }
        });
    });
}

/**
 * Copy text to clipboard with visual feedback
 */
function copyToClipboard(text, element) {
    navigator.clipboard.writeText(text).then(() => {
        // Visual feedback
        if (element) {
            element.classList.add('copy-success');
            setTimeout(() => {
                element.classList.remove('copy-success');
            }, 1000);
        }
        
        // Toast notification
        showToast('Copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Failed to copy', 'error');
    });
}

/**
 * Show toast notification
 */
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `fixed top-4 right-4 px-4 py-2 rounded-lg shadow-lg z-50 transform transition-all duration-300 translate-y-0`;
    
    switch (type) {
        case 'success':
            toast.classList.add('bg-green-600', 'text-white');
            break;
        case 'error':
            toast.classList.add('bg-red-600', 'text-white');
            break;
        default:
            toast.classList.add('bg-blue-600', 'text-white');
    }
    
    toast.textContent = message;
    document.body.appendChild(toast);
    
    // Animate in
    requestAnimationFrame(() => {
        toast.style.transform = 'translateY(0)';
    });
    
    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.transform = 'translateY(-100%)';
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

/**
 * Format file size for display
 */
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Validate file before upload
 */
function validateFile(file, maxSizeMB = 10, allowedTypes = ['image/jpeg', 'image/png', 'image/gif']) {
    const errors = [];
    
    // Check size
    const sizeMB = file.size / (1024 * 1024);
    if (sizeMB > maxSizeMB) {
        errors.push(`File too large: ${sizeMB.toFixed(1)}MB (max ${maxSizeMB}MB)`);
    }
    
    // Check type
    if (!allowedTypes.includes(file.type)) {
        errors.push(`Invalid file type: ${file.type}`);
    }
    
    return errors;
}

/**
 * Download text content as file
 */
function downloadAsFile(content, filename, mimeType = 'text/plain') {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

/**
 * HTMX event handlers
 */
document.body.addEventListener('htmx:beforeRequest', function(event) {
    // Show loading state
    const target = event.detail.target;
    if (target) {
        target.classList.add('loading');
    }
});

document.body.addEventListener('htmx:afterRequest', function(event) {
    // Remove loading state
    const target = event.detail.target;
    if (target) {
        target.classList.remove('loading');
    }
});

document.body.addEventListener('htmx:responseError', function(event) {
    console.error('HTMX error:', event.detail);
    showToast('An error occurred. Please try again.', 'error');
});
