// ===== FILE UPLOAD FUNCTIONALITY =====

import { generateId, formatFileSize, getFileIcon, validateFile } from './utils.js';

// Upload state
let uploadedFiles = [];
let isDragging = false;

// DOM elements
let fileInput, fileUploadBtn, fileUploadArea, uploadedFilesContainer, dragOverlay;

/**
 * Initialize file upload functionality
 */
export function initUpload() {
  // Get DOM elements
  fileInput = document.getElementById('file-input');
  fileUploadBtn = document.getElementById('file-upload-btn');
  fileUploadArea = document.getElementById('file-upload-area');
  uploadedFilesContainer = document.getElementById('uploaded-files');
  dragOverlay = document.getElementById('drag-overlay');

  // Set up event listeners
  setupEventListeners();
}

/**
 * Set up event listeners for file upload
 */
function setupEventListeners() {
  // File upload button click
  fileUploadBtn.addEventListener('click', () => {
    fileInput.click();
  });

  // File input change
  fileInput.addEventListener('change', handleFileSelect);

  // Drag and drop events
  document.addEventListener('dragover', handleDragOver);
  document.addEventListener('dragenter', handleDragEnter);
  document.addEventListener('dragleave', handleDragLeave);
  document.addEventListener('drop', handleDrop);

  // Prevent default drag behaviors
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    document.addEventListener(eventName, preventDefaults, false);
  });
}

/**
 * Prevent default drag behaviors
 */
function preventDefaults(e) {
  e.preventDefault();
  e.stopPropagation();
}

/**
 * Handle drag over
 */
function handleDragOver(e) {
  e.dataTransfer.dropEffect = 'copy';
}

/**
 * Handle drag enter
 */
function handleDragEnter(e) {
  if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
    if (!isDragging) {
      isDragging = true;
      showDragOverlay();
    }
  }
}

/**
 * Handle drag leave
 */
function handleDragLeave(e) {
  // Only hide overlay if leaving the document
  if (e.clientX === 0 && e.clientY === 0) {
    isDragging = false;
    hideDragOverlay();
  }
}

/**
 * Handle file drop
 */
function handleDrop(e) {
  isDragging = false;
  hideDragOverlay();
  
  const files = Array.from(e.dataTransfer.files);
  handleFiles(files);
}

/**
 * Handle file selection from input
 */
function handleFileSelect(e) {
  const files = Array.from(e.target.files);
  handleFiles(files);
  
  // Clear the input so the same file can be selected again
  e.target.value = '';
}

/**
 * Handle multiple files
 */
function handleFiles(files) {
  files.forEach(file => {
    const validation = validateFile(file, {
      maxSize: 10 * 1024 * 1024, // 10MB
      allowedTypes: ['image/*', 'text/*', 'application/pdf']
    });
    
    if (validation.valid) {
      addFile(file);
    } else {
      showFileError(file.name, validation.errors);
    }
  });
}

/**
 * Add a file to the upload list
 */
function addFile(file) {
  const fileData = {
    id: generateId(),
    file: file,
    name: file.name,
    size: file.size,
    type: file.type,
    uploaded: false
  };
  
  uploadedFiles.push(fileData);
  renderUploadedFiles();
  showFileUploadArea();
  // Dispatch sidebar update event
  window.dispatchEvent(new Event('aria-upload-changed'));
}

/**
 * Remove a file from the upload list
 */
function removeFile(fileId) {
  uploadedFiles = uploadedFiles.filter(f => f.id !== fileId);
  renderUploadedFiles();
  
  if (uploadedFiles.length === 0) {
    hideFileUploadArea();
  }
  // Dispatch sidebar update event
  window.dispatchEvent(new Event('aria-upload-changed'));
}

/**
 * Render uploaded files
 */
function renderUploadedFiles() {
  uploadedFilesContainer.innerHTML = '';
  
  uploadedFiles.forEach(fileData => {
    const fileElement = createFileElement(fileData);
    // Add fade-in animation
    fileElement.classList.add('fade-in');
    uploadedFilesContainer.appendChild(fileElement);
  });
  // Dispatch sidebar update event
  window.dispatchEvent(new Event('aria-upload-changed'));
}

/**
 * Create a file element
 */
function createFileElement(fileData) {
  const fileDiv = document.createElement('div');
  fileDiv.className = 'file-item';
  fileDiv.setAttribute('data-file-id', fileData.id);
  
  // File icon
  const iconDiv = document.createElement('div');
  iconDiv.className = 'file-icon';
  iconDiv.innerHTML = getFileIcon(fileData.name);
  
  // File name
  const nameSpan = document.createElement('span');
  nameSpan.className = 'file-name';
  nameSpan.textContent = fileData.name;
  nameSpan.title = fileData.name;
  
  // File size
  const sizeSpan = document.createElement('span');
  sizeSpan.className = 'file-size';
  sizeSpan.textContent = formatFileSize(fileData.size);
  
  // Remove button
  const removeBtn = document.createElement('button');
  removeBtn.className = 'file-remove';
  removeBtn.setAttribute('aria-label', `Remove ${fileData.name}`);
  removeBtn.innerHTML = `
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <line x1="18" y1="6" x2="6" y2="18"></line>
      <line x1="6" y1="6" x2="18" y2="18"></line>
    </svg>
  `;
  
  removeBtn.addEventListener('click', () => {
    removeFile(fileData.id);
  });
  
  // Assemble file element
  fileDiv.appendChild(iconDiv);
  fileDiv.appendChild(nameSpan);
  fileDiv.appendChild(sizeSpan);
  fileDiv.appendChild(removeBtn);
  
  return fileDiv;
}

/**
 * Show file upload area
 */
function showFileUploadArea() {
  fileUploadArea.style.display = 'block';
}

/**
 * Hide file upload area
 */
function hideFileUploadArea() {
  fileUploadArea.style.display = 'none';
}

/**
 * Show drag overlay
 */
function showDragOverlay() {
  dragOverlay.style.display = 'flex';
  dragOverlay.classList.add('pulse-drag');
}

/**
 * Hide drag overlay
 */
function hideDragOverlay() {
  dragOverlay.style.display = 'none';
  dragOverlay.classList.remove('pulse-drag');
}

/**
 * Show file error
 */
function showFileError(fileName, errors) {
  // Create a temporary error message
  const errorDiv = document.createElement('div');
  errorDiv.className = 'file-error notification notification-error fade-in';
  errorDiv.style.cssText = `
    position: fixed;
    top: 24px;
    right: 24px;
    background-color: rgba(239, 68, 68, 0.95);
    color: white;
    padding: 1rem 1.5rem;
    border-radius: 1rem;
    box-shadow: 0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1);
    z-index: 1080;
    max-width: 340px;
    font-size: 1rem;
    font-weight: 500;
    animation: slideInRight 0.3s ease-out;
  `;
  
  errorDiv.innerHTML = `
    <strong>Oops! Couldn't upload <span style="color:#fff">${fileName}</span></strong><br>
    <span style="font-size:0.95em;">${errors.join('<br>')}</span>
    <br><span style="font-size:0.9em;opacity:0.8;">Try a different file or format.</span>
  `;
  
  document.body.appendChild(errorDiv);
  
  // Remove after 5 seconds
  setTimeout(() => {
    if (errorDiv.parentNode) {
      errorDiv.parentNode.removeChild(errorDiv);
    }
  }, 5000);
}

/**
 * Get uploaded files for sending with message
 */
export function getUploadedFiles() {
  return uploadedFiles.map(fileData => ({
    id: fileData.id,
    name: fileData.name,
    size: fileData.size,
    type: fileData.type,
    file: fileData.file
  }));
}

/**
 * Clear uploaded files
 */
export function clearUploadedFiles() {
  uploadedFiles = [];
  renderUploadedFiles();
  hideFileUploadArea();
  // Dispatch sidebar update event
  window.dispatchEvent(new Event('aria-upload-changed'));
}

/**
 * Upload files to server (mock implementation)
 */
export async function uploadFiles() {
  const filesToUpload = uploadedFiles.filter(f => !f.uploaded);
  
  if (filesToUpload.length === 0) {
    return [];
  }
  
  // Mock upload process
  const uploadPromises = filesToUpload.map(async (fileData) => {
    // Simulate upload progress
    await new Promise(resolve => setTimeout(resolve, 500 + Math.random() * 1000));
    
    // Mark as uploaded
    fileData.uploaded = true;
    
    // Return file info for backend
    return {
      id: fileData.id,
      name: fileData.name,
      size: fileData.size,
      type: fileData.type,
      url: `uploads/${fileData.id}-${fileData.name}` // Mock URL
    };
  });
  
  try {
    const uploadedFileInfos = await Promise.all(uploadPromises);
    return uploadedFileInfos;
  } catch (error) {
    console.error('Upload failed:', error);
    throw error;
  }
}

/**
 * Check if there are files ready to upload
 */
export function hasFilesToUpload() {
  return uploadedFiles.length > 0;
}

/**
 * Get file count
 */
export function getFileCount() {
  return uploadedFiles.length;
}
