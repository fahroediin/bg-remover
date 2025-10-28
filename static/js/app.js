// Background Remover API - Frontend JavaScript

// Configuration
const API_BASE = 'http://127.0.0.1:5001';
let currentFiles = {
    preview: null,
    base64: null
};
let currentBase64Data = null;

// DOM Elements
const elements = {};

// Initialize DOM elements
function initializeElements() {
    console.log('DEBUG: Initializing DOM elements...');
    elements.previewFile = document.getElementById('preview-file');
    elements.base64Input = document.getElementById('base64-input');
    elements.previewBtn = document.getElementById('preview-btn');
    elements.base64Btn = document.getElementById('base64-btn');
    elements.previewLoading = document.getElementById('preview-loading');
    elements.base64Loading = document.getElementById('base64-loading');
    elements.previewResult = document.getElementById('preview-result');
    elements.base64Result = document.getElementById('base64-result');
    elements.appVersion = document.getElementById('app-version');

    // Debug: Check if all elements are found
    console.log('DEBUG: Elements found:', {
        previewFile: !!elements.previewFile,
        base64Input: !!elements.base64Input,
        previewBtn: !!elements.previewBtn,
        base64Btn: !!elements.base64Btn,
        previewLoading: !!elements.previewLoading,
        base64Loading: !!elements.base64Loading,
        previewResult: !!elements.previewResult,
        base64Result: !!elements.base64Result,
        appVersion: !!elements.appVersion
    });
}

// Tab Management
function switchTab(tabName, targetElement) {
    console.log('DEBUG: switchTab called with tabName:', tabName);

    // Hide all tabs
    document.querySelectorAll('.tab-content').forEach(tab => {
        tab.classList.remove('active');
    });

    // Remove active class from all buttons
    document.querySelectorAll('.tab').forEach(btn => {
        btn.classList.remove('active');
    });

    // Show selected tab
    document.getElementById(tabName + '-tab').classList.add('active');

    // Add active class to clicked button
    if (targetElement) {
        targetElement.classList.add('active');
    }
}

// Drag and Drop Handlers
function handleDragOver(event) {
    event.preventDefault();
    event.currentTarget.classList.add('dragover');
}

function handleDragLeave(event) {
    event.currentTarget.classList.remove('dragover');
}

function handleDrop(event, type) {
    event.preventDefault();
    event.currentTarget.classList.remove('dragover');

    const files = event.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0], type);
    }
}

function handleFileSelect(event, type) {
    const file = event.target.files[0];
    if (file) {
        handleFile(file, type);
    }
}

// File Validation and Processing
function handleFile(file, type) {
    // Validate file type
    const allowedTypes = ['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/bmp', 'image/tiff', 'image/webp'];
    if (!allowedTypes.includes(file.type)) {
        showResult(type, 'Please select a valid image file', true);
        return;
    }

    // Validate file size (16MB)
    const maxSize = 16 * 1024 * 1024;
    if (file.size > maxSize) {
        showResult(type, 'File size must be less than 16MB', true);
        return;
    }

    currentFiles[type] = file;

    // Enable button
    elements[type + 'Btn'].disabled = false;

    // Show file info
    const fileSize = (file.size / 1024 / 1024).toFixed(2);
    showResult(type, `Selected: ${file.name} (${fileSize} MB)`, false, 'info');
}

// Base64 Input Handler
function handleBase64Input() {
    const base64Data = elements.base64Input.value.trim();

    if (base64Data) {
        // Basic base64 validation
        try {
            // Check if it's a valid base64 string
            const cleanBase64 = base64Data.replace(/^data:image\/[a-z]+;base64,/, '');
            const decoded = atob(cleanBase64);

            // Store the base64 data
            currentBase64Data = base64Data;

            // Enable button
            elements.base64Btn.disabled = false;

            // Show info
            const dataLength = cleanBase64.length;
            const estimatedSize = Math.round(dataLength * 0.75 / 1024);
            showResult('base64', `Base64 data ready (${estimatedSize} KB estimated)`, false, 'info');
        } catch (error) {
            // Invalid base64
            currentBase64Data = null;
            elements.base64Btn.disabled = true;
            showResult('base64', 'Invalid base64 data. Please check your input.', true);
        }
    } else {
        currentBase64Data = null;
        elements.base64Btn.disabled = true;
        showResult('base64', '', false, 'info');
    }
}

// UI Helper Functions
function showResult(type, message, isError = false, messageType = 'success') {
    const resultElement = elements[type + 'Result'];

    resultElement.className = 'result show';

    if (isError) {
        resultElement.classList.add('error');
    } else if (messageType === 'info') {
        resultElement.classList.add('info');
    } else {
        resultElement.classList.add('success');
    }

    resultElement.innerHTML = message;
}

function showLoading(type, show = true) {
    const loadingElement = elements[type + 'Loading'];
    const btnElement = elements[type + 'Btn'];

    if (show) {
        loadingElement.classList.add('show');
        btnElement.disabled = true;
    } else {
        loadingElement.classList.remove('show');
        btnElement.disabled = false;
    }
}

// API Processing Functions
async function processPreview(event) {
    console.log('DEBUG: processPreview called with event:', event);
    if (event) {
        event.preventDefault();
        event.stopPropagation();
        console.log('DEBUG: Event prevented and stopped propagation');
    }
    await processFile('preview', '/remove-background-preview', 'preview');
}

async function processBase64(event) {
    console.log('DEBUG: processBase64 called with event:', event);
    if (event) {
        event.preventDefault();
        event.stopPropagation();
        console.log('DEBUG: Event prevented and stopped propagation');
    }

    if (!currentBase64Data) {
        showResult('base64', 'Please enter base64 image data first', true);
        return;
    }

    console.log('DEBUG: Starting base64 processing');
    showLoading('base64', true);

    try {
        // Create JSON payload
        const payload = { image: currentBase64Data };
        console.log('DEBUG: Sending request to API');

        const response = await fetch(`${API_BASE}/remove-background-base64`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        console.log('DEBUG: API response received, status:', response.status);

        if (response.ok) {
            const data = await response.json();
            console.log('DEBUG: API response data:', data);

            if (data.success) {
                const imageUrl = `data:${data.mimetype};base64,${data.image}`;
                const imageSize = Math.round(data.image.length * 0.75 / 1024);

                console.log('DEBUG: Showing result to user');
                showResult('base64', `
                    <h3>Background removed successfully!</h3>
                    <div class="image-comparison">
                        <div class="image-box">
                            <div class="image-label">Original</div>
                            <img src="${currentBase64Data}" alt="Original" class="image-preview">
                        </div>
                        <div class="image-box">
                            <div class="image-label">Result</div>
                            <img src="${imageUrl}" alt="Result" class="image-preview">
                        </div>
                    </div>
                    <div class="stats">
                        <p><strong>Image Size:</strong> ${imageSize} KB</p>
                        <p><strong>Base64 Length:</strong> ${data.image.length.toLocaleString()} characters</p>
                    </div>
                    <div class="actions">
                        <button type="button" class="btn btn-secondary" data-action="copy" data-text="${data.image.replace(/'/g, "\\'")}">
                            Copy Base64
                        </button>
                        <button type="button" class="btn btn-primary" data-action="download" data-url="${imageUrl}" data-filename="no-bg-base64.png">
                            Download Image
                        </button>
                    </div>
                `, false);
            } else {
                console.log('DEBUG: API returned error:', data.error);
                showResult('base64', `Error: ${data.error}`, true);
            }
        } else {
            const errorText = await response.text();
            console.log('DEBUG: API error response:', errorText);
            showResult('base64', `Error: ${errorText}`, true);
        }
    } catch (error) {
        console.log('DEBUG: Network error:', error);
        showResult('base64', `Network Error: ${error.message}`, true);
    } finally {
        console.log('DEBUG: Removing loading state');
        showLoading('base64', false);
    }
}

async function processFile(type, endpoint, resultType) {
    const file = currentFiles[type];
    if (!file) {
        showResult(type, 'Please select a file first', true);
        return;
    }

    showLoading(type, true);

    const formData = new FormData();
    formData.append('file', file);

    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            if (resultType === 'preview') {
                const blob = await response.blob();
                const imageUrl = URL.createObjectURL(blob);

                showResult(type, `
                    <h3>Background removed successfully!</h3>
                    <div class="image-comparison">
                        <div class="image-box">
                            <div class="image-label">Original</div>
                            <img src="${URL.createObjectURL(file)}" alt="Original" class="image-preview">
                        </div>
                        <div class="image-box">
                            <div class="image-label">Result</div>
                            <img src="${imageUrl}" alt="Result" class="image-preview">
                        </div>
                    </div>
                    <div class="actions">
                        <button type="button" class="btn btn-primary" data-action="download" data-url="${imageUrl}" data-filename="${file.name}">
                            Download Result
                        </button>
                    </div>
                `, false);
            } else if (resultType === 'base64') {
                const data = await response.json();
                if (data.success) {
                    const imageUrl = `data:${data.mimetype};base64,${data.image}`;
                    const imageSize = Math.round(data.image.length * 0.75 / 1024);

                    showResult(type, `
                        <h3>Converted to base64 successfully!</h3>
                        <div class="image-comparison">
                            <div class="image-box">
                                <div class="image-label">Original</div>
                                <img src="${URL.createObjectURL(file)}" alt="Original" class="image-preview">
                            </div>
                            <div class="image-box">
                                <div class="image-label">Result</div>
                                <img src="${imageUrl}" alt="Result" class="image-preview">
                            </div>
                        </div>
                        <div class="stats">
                            <p><strong>Image Size:</strong> ${imageSize} KB</p>
                            <p><strong>Base64 Length:</strong> ${data.image.length.toLocaleString()} characters</p>
                        </div>
                        <div class="actions">
                            <button type="button" class="btn btn-secondary" onclick="copyToClipboard('${data.image}')">
                                Copy Base64
                            </button>
                            <button type="button" class="btn btn-primary" onclick="downloadImage('${imageUrl}', '${file.name}')">
                                Download Image
                            </button>
                        </div>
                    `, false);
                } else {
                    showResult(type, `Error: ${data.error}`, true);
                }
            }
        } else {
            const errorText = await response.text();
            showResult(type, `Error: ${errorText}`, true);
        }
    } catch (error) {
        showResult(type, `Network Error: ${error.message}`, true);
    } finally {
        showLoading(type, false);
    }
}

// Utility Functions
function downloadImage(imageUrl, originalName) {
    const a = document.createElement('a');
    a.href = imageUrl;
    a.download = `no-bg-${originalName.split('.')[0]}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

async function copyToClipboard(text) {
    try {
        await navigator.clipboard.writeText(text);
        alert('Base64 data copied to clipboard!');
    } catch (err) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        alert('Base64 data copied to clipboard!');
    }
}

// App Info Loading
async function loadAppInfo() {
    try {
        const response = await fetch(`${API_BASE}/`);
        if (response.ok) {
            const data = await response.json();
            if (data.version) {
                elements.appVersion.textContent = `v${data.version}`;
            }
        }
    } catch (error) {
        // Keep default values if API is not available
        console.log('Using default app info');
    }
}

// Initialize Application
function initializeApp() {
    console.log('DEBUG: Initializing app...');
    initializeElements();

    // Load app info
    loadAppInfo();

    // Add comprehensive event prevention for ALL forms
    document.querySelectorAll('form').forEach(form => {
        form.addEventListener('submit', function(e) {
            console.log('DEBUG: Form submit prevented');
            e.preventDefault();
            e.stopPropagation();
            return false;
        });
    });

    // Tab switching event listeners
    document.querySelectorAll('.tab').forEach(tab => {
        tab.addEventListener('click', function(e) {
            console.log('DEBUG: Tab clicked:', e.target.textContent);
            e.preventDefault();
            e.stopPropagation();

            const tabName = e.target.getAttribute('data-tab');
            switchTab(tabName, e.target);
        });
    });

    // Upload area click handlers
    const previewUploadArea = document.getElementById('preview-upload-area');
    console.log('DEBUG: Upload area found:', !!previewUploadArea);
    if (previewUploadArea) {
        // Add multiple event listeners to ensure it works
        previewUploadArea.addEventListener('click', function(e) {
            console.log('DEBUG: Preview upload area clicked!');
            e.preventDefault();
            e.stopPropagation();

            const fileInput = document.getElementById('preview-file');
            console.log('DEBUG: File input found:', !!fileInput);
            if (fileInput) {
                console.log('DEBUG: Triggering file input click...');
                try {
                    fileInput.click();
                    console.log('DEBUG: File input click completed');
                } catch (error) {
                    console.log('DEBUG: Error clicking file input:', error);
                }
            } else {
                console.log('DEBUG: ERROR - File input not found!');
            }
        });

        // Also try onclick as backup
        previewUploadArea.onclick = function(e) {
            console.log('DEBUG: Backup onclick triggered');
            e.preventDefault();
            e.stopPropagation();
            const fileInput = document.getElementById('preview-file');
            if (fileInput) {
                fileInput.click();
            }
        };

        console.log('DEBUG: Upload area event listeners attached');
    } else {
        console.log('DEBUG: ERROR - Upload area not found!');
    }

    // File input handlers
    if (elements.previewFile) {
        elements.previewFile.addEventListener('change', function(e) {
            console.log('DEBUG: Preview file selected, files:', e.target.files);
            e.preventDefault();
            if (e.target.files && e.target.files.length > 0) {
                console.log('DEBUG: Processing file:', e.target.files[0].name);
                handleFile(e.target.files[0], 'preview');
            } else {
                console.log('DEBUG: No files selected');
            }
        });
    }

    // Button event listeners with comprehensive prevention
    if (elements.previewBtn) {
        elements.previewBtn.addEventListener('click', function(e) {
            console.log('DEBUG: Preview button clicked');
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            processPreviewLocal();
        });
    }

    if (elements.base64Btn) {
        elements.base64Btn.addEventListener('click', function(e) {
            console.log('DEBUG: Base64 button clicked');
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            processBase64Local();
        });
    }

    // Base64 input event listeners
    if (elements.base64Input) {
        elements.base64Input.addEventListener('input', handleBase64Input);
        elements.base64Input.addEventListener('focus', function() {
            this.style.borderColor = '#007bff';
        });
        elements.base64Input.addEventListener('blur', function() {
            this.style.borderColor = '#dee2e6';
        });
    }

    // Prevent form submission on Enter key in textarea
    if (elements.base64Input) {
        elements.base64Input.addEventListener('keydown', function(e) {
            if (e.key === 'Enter' && e.ctrlKey) {
                console.log('DEBUG: Ctrl+Enter detected in textarea');
                e.preventDefault();
                e.stopPropagation();
                e.stopImmediatePropagation();
                processBase64Local();
            }
        });
    }

    // Drag and drop event listeners
    if (previewUploadArea) {
        previewUploadArea.addEventListener('dragover', function(e) {
            e.preventDefault();
            e.currentTarget.classList.add('dragover');
        });

        previewUploadArea.addEventListener('dragleave', function(e) {
            e.preventDefault();
            e.currentTarget.classList.remove('dragover');
        });

        previewUploadArea.addEventListener('drop', function(e) {
            console.log('DEBUG: Files dropped on preview area');
            e.preventDefault();
            e.stopPropagation();
            e.currentTarget.classList.remove('dragover');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0], 'preview');
            }
        });
    }

    // Event delegation for action buttons (copy/download)
    document.addEventListener('click', function(e) {
        if (e.target.matches('[data-action="copy"]')) {
            console.log('DEBUG: Copy button clicked');
            e.preventDefault();
            e.stopPropagation();
            const text = e.target.getAttribute('data-text');
            if (text) {
                copyToClipboard(text);
            }
        }

        if (e.target.matches('[data-action="download"]')) {
            console.log('DEBUG: Download button clicked');
            e.preventDefault();
            e.stopPropagation();
            const url = e.target.getAttribute('data-url');
            const filename = e.target.getAttribute('data-filename');
            if (url && filename) {
                downloadImage(url, filename);
            }
        }
    });

    // Comprehensive form submission prevention at document level
    document.addEventListener('submit', function(e) {
        console.log('DEBUG: Document-level submit prevented');
        e.preventDefault();
        e.stopPropagation();
        e.stopImmediatePropagation();
        return false;
    });

    // Prevent any navigation or page reload attempts
    window.addEventListener('beforeunload', function(e) {
        console.log('DEBUG: Beforeunload event detected');
        // Don't show confirmation dialog, just log it
    });

    console.log('Background Remover App initialized successfully');
}

// No more global functions - using event listeners only

// Create local versions for internal calls
async function processPreviewLocal() {
    console.log('DEBUG: processPreviewLocal called');

    if (!currentFiles.preview) {
        showResult('preview', 'Please select a file first', true);
        return;
    }

    showLoading('preview', true);

    const formData = new FormData();
    formData.append('file', currentFiles.preview);

    try {
        const response = await fetch(`${API_BASE}/remove-background-preview`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const blob = await response.blob();
            const imageUrl = URL.createObjectURL(blob);

            showResult('preview', `
                <h3>Background removed successfully!</h3>
                <div class="image-comparison">
                    <div class="image-box">
                        <div class="image-label">Original</div>
                        <img src="${URL.createObjectURL(currentFiles.preview)}" alt="Original" class="image-preview">
                    </div>
                    <div class="image-box">
                        <div class="image-label">Result</div>
                        <img src="${imageUrl}" alt="Result" class="image-preview">
                    </div>
                </div>
                <div class="actions">
                    <button type="button" class="btn btn-primary" onclick="downloadImage('${imageUrl}', '${currentFiles.preview.name}')">
                        Download Result
                    </button>
                </div>
            `, false);
        } else {
            const errorText = await response.text();
            showResult('preview', `Error: ${errorText}`, true);
        }
    } catch (error) {
        showResult('preview', `Network Error: ${error.message}`, true);
    } finally {
        showLoading('preview', false);
    }
}

async function processBase64Local() {
    console.log('DEBUG: processBase64Local called');

    if (!currentBase64Data) {
        showResult('base64', 'Please enter base64 image data first', true);
        return;
    }

    console.log('DEBUG: Starting base64 processing');
    showLoading('base64', true);

    try {
        // Create JSON payload
        const payload = { image: currentBase64Data };
        console.log('DEBUG: Sending request to API');

        const response = await fetch(`${API_BASE}/remove-background-base64`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
        });

        console.log('DEBUG: API response received, status:', response.status);

        if (response.ok) {
            const data = await response.json();
            console.log('DEBUG: API response data:', data);

            if (data.success) {
                const imageUrl = `data:${data.mimetype};base64,${data.image}`;
                const imageSize = Math.round(data.image.length * 0.75 / 1024);

                console.log('DEBUG: Showing result to user');
                showResult('base64', `
                    <h3>Background removed successfully!</h3>
                    <div class="image-comparison">
                        <div class="image-box">
                            <div class="image-label">Original</div>
                            <img src="${currentBase64Data}" alt="Original" class="image-preview">
                        </div>
                        <div class="image-box">
                            <div class="image-label">Result</div>
                            <img src="${imageUrl}" alt="Result" class="image-preview">
                        </div>
                    </div>
                    <div class="stats">
                        <p><strong>Image Size:</strong> ${imageSize} KB</p>
                        <p><strong>Base64 Length:</strong> ${data.image.length.toLocaleString()} characters</p>
                    </div>
                    <div class="actions">
                        <button type="button" class="btn btn-secondary" data-action="copy" data-text="${data.image.replace(/'/g, "\\'")}">
                            Copy Base64
                        </button>
                        <button type="button" class="btn btn-primary" data-action="download" data-url="${imageUrl}" data-filename="no-bg-base64.png">
                            Download Image
                        </button>
                    </div>
                `, false);
            } else {
                console.log('DEBUG: API returned error:', data.error);
                showResult('base64', `Error: ${data.error}`, true);
            }
        } else {
            const errorText = await response.text();
            console.log('DEBUG: API error response:', errorText);
            showResult('base64', `Error: ${errorText}`, true);
        }
    } catch (error) {
        console.log('DEBUG: Network error:', error);
        showResult('base64', `Network Error: ${error.message}`, true);
    } finally {
        console.log('DEBUG: Removing loading state');
        showLoading('base64', false);
    }
}

// Utility functions
function downloadImage(imageUrl, originalName) {
    console.log('DEBUG: Downloading image:', originalName);
    const a = document.createElement('a');
    a.href = imageUrl;
    a.download = `no-bg-${originalName.split('.')[0]}.png`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
}

function copyToClipboard(text) {
    console.log('DEBUG: Copying to clipboard');
    try {
        navigator.clipboard.writeText(text);
        alert('Base64 data copied to clipboard!');
    } catch (err) {
        // Fallback for older browsers
        const textArea = document.createElement('textarea');
        textArea.value = text;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
        alert('Base64 data copied to clipboard!');
    }
}

// Event Listeners
document.addEventListener('DOMContentLoaded', initializeApp);