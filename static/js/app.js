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

    // New preview elements
    elements.previewUploadContainer = document.getElementById('preview-upload-container');
    elements.previewNewFileContainer = document.getElementById('preview-new-file-container');
    elements.previewNewFileBtn = document.getElementById('preview-new-file-btn');

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
        appVersion: !!elements.appVersion,
        previewUploadContainer: !!elements.previewUploadContainer,
        previewNewFileContainer: !!elements.previewNewFileContainer,
        previewNewFileBtn: !!elements.previewNewFileBtn
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
    const input = elements.base64Input.value.trim();

    if (input) {
        console.log('DEBUG: Processing input:', input.substring(0, 100) + '...');

        // Check if input is a file path (contains : and \ or /)
        const isFilePath = /^[A-Za-z]:\\.*\.txt$/.test(input) || /^\/.*\.txt$/.test(input);

        if (isFilePath) {
            console.log('DEBUG: Detected file path, reading file content...');
            handleFilePathInput(input);
        } else {
            console.log('DEBUG: Detected base64 data, validating...');
            handleBase64DataInput(input);
        }
    } else {
        currentBase64Data = null;
        elements.base64Btn.disabled = true;
        showResult('base64', '', false, 'info');
    }
}

// Handle file path input - read file content via API
async function handleFilePathInput(filePath) {
    showResult('base64', `
        <div class="validation-info">
            <p>📖 Reading file content...</p>
            <p><strong>File:</strong> ${filePath}</p>
            <div class="loading-spinner">⏳ Please wait...</div>
        </div>
    `, false, 'info');

    try {
        const response = await fetch(`${API_BASE}/read-file`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ file_path: filePath })
        });

        console.log('DEBUG: File read response status:', response.status);

        if (response.ok) {
            const data = await response.json();
            console.log('DEBUG: File read successful, content length:', data.content?.length || 0);

            if (data.success && data.content) {
                // Process the content as base64 data
                handleBase64DataInput(data.content, filePath);
            } else {
                showFileReadError('File read failed', data.error || 'Unknown error');
            }
        } else {
            const errorData = await response.json();
            showFileReadError('File read failed', errorData.error || `HTTP ${response.status}`);
        }
    } catch (error) {
        console.log('DEBUG: Network error reading file:', error);
        showFileReadError('Network error', error.message);
    }
}

// Show file read error
function showFileReadError(title, error) {
    currentBase64Data = null;
    elements.base64Btn.disabled = true;

    const errorMessage = `
        <div class="validation-error">
            <p>❌ ${title}</p>
            <p><strong>Error:</strong> ${error}</p>
            <div class="validation-tips">
                <p><strong>Solutions:</strong></p>
                <ul>
                    <li>Check if the file path is correct</li>
                    <li>Ensure the file exists and is accessible</li>
                    <li>Make sure it's a .txt file</li>
                    <li>Check file permissions</li>
                    <li>Try pasting the base64 data directly instead of file path</li>
                </ul>
            </div>
        </div>
    `;

    showResult('base64', errorMessage, true);
}

// Handle base64 data input - existing validation logic
function handleBase64DataInput(base64Data, originalFilePath = null) {
    console.log('DEBUG: Validating base64 input...');

    // Comprehensive base64 validation
    const validationResult = validateBase64Input(base64Data);

    if (validationResult.isValid) {
        // Store the base64 data
        currentBase64Data = base64Data;

        // Enable button
        elements.base64Btn.disabled = false;

        // Show info
        const dataLength = validationResult.cleanData.length;
        const estimatedSize = Math.round(dataLength * 0.75 / 1024);

        const sourceInfo = originalFilePath ?
            `<p><strong>Source:</strong> File: ${originalFilePath}</p>` :
            `<p><strong>Source:</strong> Direct input</p>`;

        showResult('base64', `
            <div class="validation-success">
                <p>✅ Valid base64 image data</p>
                <p><strong>Type:</strong> ${validationResult.imageType}</p>
                <p><strong>Estimated Size:</strong> ${estimatedSize} KB</p>
                <p><strong>Data Length:</strong> ${dataLength.toLocaleString()} characters</p>
                ${sourceInfo}
            </div>
        `, false, 'success');

        console.log('DEBUG: Base64 validation passed:', validationResult);
    } else {
        // Invalid base64
        currentBase64Data = null;
        elements.base64Btn.disabled = true;

        const errorMessage = `
            <div class="validation-error">
                <p>❌ Invalid base64 data</p>
                <p><strong>Issue:</strong> ${validationResult.error}</p>
                <p><strong>Solution:</strong> ${validationResult.solution}</p>
                <div class="validation-tips">
                    <p><strong>Tips:</strong></p>
                    <ul>
                        <li>Make sure your base64 data starts with "data:image/..."</li>
                        <li>Check that the base64 string is not corrupted</li>
                        <li>Ensure it's a valid image format (PNG, JPG, GIF, etc.)</li>
                        <li>Try encoding the image again using a reliable tool</li>
                        <li>If using file path, ensure the .txt file contains valid base64 data</li>
                    </ul>
                </div>
            </div>
        `;

        showResult('base64', errorMessage, true);
        console.log('DEBUG: Base64 validation failed:', validationResult);
    }
}

// Simplified base64 validation function - accepts any content from file
function validateBase64Input(base64Data) {
    console.log('DEBUG: Starting simplified base64 validation...');

    // Check if input is empty
    if (!base64Data || base64Data.trim().length === 0) {
        return {
            isValid: false,
            error: 'Empty input',
            solution: 'Please paste base64 image data or file path',
            imageType: null,
            cleanData: null
        };
    }

    // If it's a file path, return valid (we'll read the file content via API)
    const isFilePath = /^[A-Za-z]:\\.*\.txt$/i.test(base64Data);
    if (isFilePath) {
        return {
            isValid: true,
            error: null,
            solution: null,
            imageType: 'txt',
            cleanData: base64Data,
            decodedSize: base64Data.length
        };
    }

    // For direct base64 data, only check if it's not empty
    if (base64Data.length > 0) {
        return {
            isValid: true,
            error: null,
            solution: null,
            imageType: 'base64',
            cleanData: base64Data,
            decodedSize: base64Data.length
        };
    }

    return {
        isValid: false,
        error: 'Invalid or empty input',
        solution: 'Please paste valid base64 data or a file path to a .txt file',
        imageType: null,
        cleanData: null
    };
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
        // Start progress animation
        animateProgress(type);
    } else {
        loadingElement.classList.remove('show');
        btnElement.disabled = false;
        // Reset progress bar
        resetProgress(type);
    }
}

// Progress bar animation
function animateProgress(type) {
    const progressFill = document.querySelector(`#${type}-loading .progress-fill`);
    if (!progressFill) return;

    let progress = 0;
    const interval = setInterval(() => {
        progress += Math.random() * 15; // Random increment for natural effect
        if (progress >= 90) {
            progress = 90; // Stop at 90% until complete
            clearInterval(interval);
        }
        progressFill.style.width = progress + '%';
    }, 300);
}

function resetProgress(type) {
    const progressFill = document.querySelector(`#${type}-loading .progress-fill`);
    if (progressFill) {
        progressFill.style.width = '0%';
    }
}

function completeProgress(type) {
    const progressFill = document.querySelector(`#${type}-loading .progress-fill`);
    if (progressFill) {
        progressFill.style.width = '100%';
        setTimeout(() => {
            resetProgress(type);
        }, 500);
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
                // Complete progress before showing result
                completeProgress('base64');

                showResult('base64', `
                    <h3>Background removed successfully!</h3>
                    <div class="image-box" style="text-align: center; margin: 20px 0;">
                        <div class="image-label" style="margin-bottom: 15px; font-weight: 600; color: #495057;">Result</div>
                        <img src="${imageUrl}" alt="Result" class="image-preview" style="max-width: 100%; max-height: 400px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                    </div>
                    <div class="stats">
                        <p><strong>Image Size:</strong> ${imageSize} KB</p>
                        <p><strong>Base64 Length:</strong> ${data.image.length.toLocaleString()} characters</p>
                    </div>
                    <div class="actions" style="text-align: center; margin-top: 20px;">
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

    // Upload area click handlers - simplified since we now have a browse button
    const previewUploadArea = document.getElementById('preview-upload-area');
    console.log('DEBUG: Upload area found:', !!previewUploadArea);
    if (previewUploadArea) {
        // Only handle drag and drop, let the browse button handle file selection
        console.log('DEBUG: Upload area drag & drop handlers attached');
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

    // Process other file button event listener
    if (elements.previewNewFileBtn) {
        elements.previewNewFileBtn.addEventListener('click', function(e) {
            console.log('DEBUG: Process other file button clicked');
            e.preventDefault();
            e.stopPropagation();
            e.stopImmediatePropagation();
            showPreviewUpload();
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

// Preview UI State Management Functions
function showPreviewResult() {
    console.log('DEBUG: Showing preview result, hiding upload area');

    // Hide upload container
    if (elements.previewUploadContainer) {
        elements.previewUploadContainer.style.display = 'none';
    }

    // Show "Process other file" button
    if (elements.previewNewFileContainer) {
        elements.previewNewFileContainer.style.display = 'block';
    }
}

function showPreviewUpload() {
    console.log('DEBUG: Showing preview upload, hiding result');

    // Show upload container
    if (elements.previewUploadContainer) {
        elements.previewUploadContainer.style.display = 'block';
    }

    // Hide "Process other file" button
    if (elements.previewNewFileContainer) {
        elements.previewNewFileContainer.style.display = 'none';
    }

    // Clear result
    if (elements.previewResult) {
        elements.previewResult.className = 'result';
        elements.previewResult.innerHTML = '';
    }

    // Reset file input
    if (elements.previewFile) {
        elements.previewFile.value = '';
    }

    // Reset button state
    if (elements.previewBtn) {
        elements.previewBtn.disabled = true;
    }

    // Clear current file
    currentFiles.preview = null;
}

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

            // Complete progress before showing result
            completeProgress('preview');

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

            // Show result and hide upload area
            showPreviewResult();
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
                // Complete progress before showing result
                completeProgress('base64');

                showResult('base64', `
                    <h3>Background removed successfully!</h3>
                    <div class="image-box" style="text-align: center; margin: 20px 0;">
                        <div class="image-label" style="margin-bottom: 15px; font-weight: 600; color: #495057;">Result</div>
                        <img src="${imageUrl}" alt="Result" class="image-preview" style="max-width: 100%; max-height: 400px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.15);">
                    </div>
                    <div class="stats">
                        <p><strong>Image Size:</strong> ${imageSize} KB</p>
                        <p><strong>Base64 Length:</strong> ${data.image.length.toLocaleString()} characters</p>
                    </div>
                    <div class="actions" style="text-align: center; margin-top: 20px;">
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