/**
 * Luminate Cookbook - Frontend JavaScript
 */

// Banner processor state
let bannerFiles = [];
let currentCropIndex = 0;
let cropperInstance = null;
let cropData = {};

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

/**
 * Banner Processor Functions
 */

function handleBannerFileSelect(input) {
    const fileList = document.getElementById('file-list');
    const fileListItems = document.getElementById('file-list-items');
    const previewBtn = document.getElementById('preview-btn');
    const processBtn = document.getElementById('process-btn');
    
    bannerFiles = Array.from(input.files);
    
    if (bannerFiles.length > 0) {
        fileList.classList.remove('hidden');
        fileListItems.innerHTML = '';
        
        bannerFiles.forEach(file => {
            const sizeMB = (file.size / (1024 * 1024)).toFixed(2);
            const li = document.createElement('li');
            li.innerHTML = `<span class="text-gray-800">${file.name}</span> <span class="text-gray-500">(${sizeMB} MB)</span>`;
            fileListItems.appendChild(li);
        });
        
        previewBtn.disabled = false;
        processBtn.disabled = false;
    } else {
        fileList.classList.add('hidden');
        previewBtn.disabled = true;
        processBtn.disabled = true;
    }
}

async function previewAllCrops() {
    if (bannerFiles.length === 0) {
        showToast('Please select images first', 'error');
        return;
    }
    
    const previewBtn = document.getElementById('preview-btn');
    const previewSpinner = document.getElementById('preview-spinner');
    const previewText = document.getElementById('preview-text');
    
    previewBtn.disabled = true;
    previewSpinner.classList.remove('hidden');
    previewText.textContent = 'Loading previews...';
    
    try {
        // Reset state
        currentCropIndex = 0;
        cropData = {};
        
        // Show modal with first image
        await showCropPreview(0);
        
    } catch (error) {
        console.error('Error generating previews:', error);
        showToast('Failed to generate previews', 'error');
    } finally {
        previewBtn.disabled = false;
        previewSpinner.classList.add('hidden');
        previewText.textContent = '👁️ Preview & Adjust Crops';
    }
}

async function showCropPreview(index) {
    if (index >= bannerFiles.length) {
        // All images reviewed, proceed to processing
        closeCropModal();
        await processAllBanners();
        return;
    }
    
    const file = bannerFiles[index];
    currentCropIndex = index;
    
    // Get settings
    const width = parseInt(document.getElementById('width').value) || 600;
    const height = parseInt(document.getElementById('height').value) || 340;
    const cropPadding = parseFloat(document.getElementById('crop_padding').value) || 0.15;
    
    // Create FormData for preview request
    const formData = new FormData();
    formData.append('file', file);
    formData.append('width', width);
    formData.append('height', height);
    formData.append('crop_padding', cropPadding);
    
    try {
        const response = await fetch('/api/banner/preview', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            // Update modal
            document.getElementById('modal-filename').textContent = file.name;
            document.getElementById('modal-detection-info').textContent = 
                `${data.people_detected} people, ${data.faces_detected} faces detected`;
            document.getElementById('modal-progress').textContent = 
                `Image ${index + 1} of ${bannerFiles.length}`;
            
            // Load image in cropper
            const imgElement = document.getElementById('crop-image');
            imgElement.src = data.image_base64;
            
            // Destroy previous cropper instance
            if (cropperInstance) {
                cropperInstance.destroy();
            }
            
            // Initialize cropper with detected crop box
            imgElement.onload = () => {
                const cropBox = data.crop_box;
                const aspectRatio = width / height;
                
                cropperInstance = new Cropper(imgElement, {
                    aspectRatio: aspectRatio,
                    viewMode: 1,
                    data: {
                        x: cropBox.x1,
                        y: cropBox.y1,
                        width: cropBox.width,
                        height: cropBox.height
                    },
                    autoCropArea: 1,
                    responsive: true,
                    guides: true,
                    center: true,
                    highlight: true,
                    cropBoxMovable: true,
                    cropBoxResizable: true,
                    toggleDragModeOnDblclick: false,
                });
            };
            
            // Show modal
            document.getElementById('crop-modal').classList.remove('hidden');
            
        } else {
            showToast(`Failed to preview ${file.name}: ${data.error}`, 'error');
            // Skip to next
            await showCropPreview(index + 1);
        }
        
    } catch (error) {
        console.error('Error previewing crop:', error);
        showToast(`Error previewing ${file.name}`, 'error');
        await showCropPreview(index + 1);
    }
}

function acceptCurrentCrop() {
    if (!cropperInstance) return;
    
    const file = bannerFiles[currentCropIndex];
    const cropBoxData = cropperInstance.getData();
    
    // Store crop data for this file
    cropData[file.name] = {
        x1: Math.round(cropBoxData.x),
        y1: Math.round(cropBoxData.y),
        x2: Math.round(cropBoxData.x + cropBoxData.width),
        y2: Math.round(cropBoxData.y + cropBoxData.height)
    };
    
    // Move to next image
    showCropPreview(currentCropIndex + 1);
}

function skipCurrentImage() {
    // Don't store crop data, use automatic detection
    showCropPreview(currentCropIndex + 1);
}

function closeCropModal() {
    document.getElementById('crop-modal').classList.add('hidden');
    if (cropperInstance) {
        cropperInstance.destroy();
        cropperInstance = null;
    }
}

async function processAllBanners() {
    if (bannerFiles.length === 0) {
        showToast('Please select images first', 'error');
        return;
    }
    
    const processBtn = document.getElementById('process-btn');
    const processSpinner = document.getElementById('process-spinner');
    const processText = document.getElementById('process-text');
    
    processBtn.disabled = true;
    processSpinner.classList.remove('hidden');
    processText.textContent = 'Processing...';
    
    try {
        // Get settings
        const width = parseInt(document.getElementById('width').value) || 600;
        const height = parseInt(document.getElementById('height').value) || 340;
        const quality = parseInt(document.getElementById('quality').value) || 82;
        const includeRetina = document.getElementById('include_retina').checked;
        const filenamePrefix = document.getElementById('filename_prefix').value;
        const cropPadding = parseFloat(document.getElementById('crop_padding').value) || 0.15;
        
        // Create FormData
        const formData = new FormData();
        bannerFiles.forEach(file => {
            formData.append('files', file);
        });
        formData.append('width', width);
        formData.append('height', height);
        formData.append('quality', quality);
        formData.append('include_retina', includeRetina);
        formData.append('filename_prefix', filenamePrefix);
        formData.append('crop_padding', cropPadding);
        
        // Add manual crops if any
        if (Object.keys(cropData).length > 0) {
            formData.append('manual_crops', JSON.stringify(cropData));
        }
        
        const response = await fetch('/api/banner/process', {
            method: 'POST',
            body: formData
        });
        
        if (response.ok) {
            // Download ZIP file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filenamePrefix ? `${filenamePrefix}_email_banners.zip` : 'email_banners.zip';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            showToast('Banners processed successfully!', 'success');
            
            // Reset form
            document.getElementById('files').value = '';
            document.getElementById('file-list').classList.add('hidden');
            bannerFiles = [];
            cropData = {};
            document.getElementById('preview-btn').disabled = true;
            processBtn.disabled = true;
            
        } else {
            const error = await response.text();
            showToast(`Processing failed: ${error}`, 'error');
        }
        
    } catch (error) {
        console.error('Error processing banners:', error);
        showToast('An error occurred while processing', 'error');
    } finally {
        processBtn.disabled = false;
        processSpinner.classList.add('hidden');
        processText.textContent = '🚀 Process All Images';
    }
}
