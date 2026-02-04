
// Caption Extraction Frontend JavaScript

class CaptionExtractor {
    constructor() {
        this.selectedFile = null;
        this.currentJobId = null;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkBackendConnection();
    }

    setupEventListeners() {
        // File upload area
        const uploadArea = document.getElementById('upload-area');
        const fileInput = document.getElementById('file-input');
        const uploadBtn = document.getElementById('upload-btn');
        const removeFileBtn = document.getElementById('remove-file');
        const newUploadBtn = document.getElementById('new-upload-btn');
        const retryBtn = document.getElementById('retry-btn');

        // Click to browse files
        uploadArea.addEventListener('click', () => {
            fileInput.click();
        });

        // File input change
        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.handleFileSelect(e.target.files[0]);
            }
        });

        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('dragover');
        });

        uploadArea.addEventListener('dragleave', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('dragover');
            
            if (e.dataTransfer.files.length > 0) {
                this.handleFileSelect(e.dataTransfer.files[0]);
            }
        });

        // Remove file
        removeFileBtn.addEventListener('click', () => {
            this.clearFileSelection();
        });

        // Upload button
        uploadBtn.addEventListener('click', () => {
            this.uploadFile();
        });

        // New upload button
        newUploadBtn.addEventListener('click', () => {
            this.resetForm();
        });

        // Retry button
        retryBtn.addEventListener('click', () => {
            this.hideError();
            this.resetForm();
        });

        // Download links
        document.getElementById('download-txt').addEventListener('click', (e) => {
            e.preventDefault();
            this.downloadFile('transcript.txt');
        });

        document.getElementById('download-segments').addEventListener('click', (e) => {
            e.preventDefault();
            this.downloadFile('segments.json');
        });

        document.getElementById('download-words').addEventListener('click', (e) => {
            e.preventDefault();
            this.downloadFile('words.json');
        });

        document.getElementById('download-srt').addEventListener('click', (e) => {
            e.preventDefault();
            this.downloadFile('transcript.srt');
        });

        document.getElementById('download-vtt').addEventListener('click', (e) => {
            e.preventDefault();
            this.downloadFile('transcript.vtt');
        });
    }

    async checkBackendConnection() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            
            const statusElement = document.getElementById('connection-status');
            if (response.ok) {
                statusElement.innerHTML = `
                    <div class="w-2 h-2 bg-green-500 rounded-full mr-2"></div>
                    <span class="text-sm text-green-600">Backend connected</span>
                `;
            } else {
                throw new Error('Backend not responding');
            }
        } catch (error) {
            const statusElement = document.getElementById('connection-status');
            statusElement.innerHTML = `
                <div class="w-2 h-2 bg-red-500 rounded-full mr-2"></div>
                <span class="text-sm text-red-600">Backend disconnected</span>
            `;
            console.error('Backend connection failed:', error);
        }
    }

    handleFileSelect(file) {
        // Validate file type
        const allowedTypes = [
            'video/mp4', 'video/avi', 'video/mov', 'video/mkv',
            'audio/wav', 'audio/mp3', 'audio/m4a', 'audio/flac', 'audio/ogg'
        ];

        if (!allowedTypes.includes(file.type)) {
            this.showError('Invalid file type. Please select a video or audio file.');
            return;
        }

        // Validate file size (100MB)
        if (file.size > 100 * 1024 * 1024) {
            this.showError('File too large. Maximum size is 100MB.');
            return;
        }

        this.selectedFile = file;
        this.displayFileInfo(file);
        document.getElementById('upload-btn').disabled = false;
    }

    displayFileInfo(file) {
        const fileInfo = document.getElementById('file-info');
        const fileName = document.getElementById('file-name');
        const fileSize = document.getElementById('file-size');

        fileName.textContent = file.name;
        fileSize.textContent = this.formatFileSize(file.size);
        
        // Animate file info appearance
        fileInfo.classList.remove('hidden');
        fileInfo.classList.add('animate-slide-up');
        document.getElementById('upload-area').classList.add('hidden');
    }

    clearFileSelection() {
        this.selectedFile = null;
        document.getElementById('file-input').value = '';
        document.getElementById('file-info').classList.add('hidden');
        document.getElementById('file-info').classList.remove('animate-slide-up');
        document.getElementById('upload-area').classList.remove('hidden');
        document.getElementById('upload-btn').disabled = true;
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async uploadFile() {
        if (!this.selectedFile) return;

        try {
            this.showProgress();
            this.hideError();
            this.hideResults();

            const formData = new FormData();
            formData.append('file', this.selectedFile);
            formData.append('model', document.getElementById('model-select').value);
            formData.append('compute_type', document.getElementById('compute-type').value);
            formData.append('beam_size', '5');
            formData.append('vad', document.getElementById('vad-filter').checked);
            const instr = document.getElementById('instructions-input');
            if (instr && instr.value && instr.value.trim().length > 0) {
                formData.append('instructions', instr.value.trim());
            }

            const language = document.getElementById('language-select').value;
            if (language) {
                formData.append('language', language);
            }

            // Simulate progress
            this.updateProgress(10, 'Uploading file...');
            
            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            this.updateProgress(50, 'Processing with Whisper...');

            const result = await response.json();

            if (!response.ok) {
                throw new Error(result.details || result.error || 'Upload failed');
            }

            this.updateProgress(100, 'Processing complete!');
            
            // Wait a moment to show completion
            setTimeout(() => {
                this.hideProgress();
                this.showResults(result);
            }, 1000);

        } catch (error) {
            console.error('Upload error:', error);
            this.hideProgress();
            this.showError(error.message || 'Upload failed. Please try again.');
        }
    }

    showProgress() {
        document.getElementById('progress-section').classList.remove('hidden');
        this.updateProgress(0, 'Starting upload...');
    }

    hideProgress() {
        document.getElementById('progress-section').classList.add('hidden');
    }

    updateProgress(percent, text) {
        document.getElementById('progress-fill').style.width = percent + '%';
        document.getElementById('progress-text').textContent = text;
    }

    showResults(result) {
        this.currentJobId = result.job_id;
        
        document.getElementById('job-id').textContent = result.job_id;
        document.getElementById('job-status').textContent = 'Completed Successfully';
        
        // Update download links
        const baseUrl = `/api/download/${result.job_id}`;
        document.getElementById('download-txt').href = `${baseUrl}/transcript.txt`;
        document.getElementById('download-segments').href = `${baseUrl}/segments.json`;
        document.getElementById('download-words').href = `${baseUrl}/words.json`;
        document.getElementById('download-srt').href = `${baseUrl}/transcript.srt`;
        document.getElementById('download-vtt').href = `${baseUrl}/transcript.vtt`;
        
        // Show results with animation
        const resultsSection = document.getElementById('results-section');
        resultsSection.classList.remove('hidden');
        resultsSection.classList.add('animate-fade-in');
        
        // Add success animation to download items
        setTimeout(() => {
            const downloadItems = document.querySelectorAll('.download-item');
            downloadItems.forEach((item, index) => {
                setTimeout(() => {
                    item.classList.add('animate-slide-up');
                }, index * 100);
            });
        }, 300);

        // Handle final video playback + download if available
        try {
            const finalPath = result.final_video || result.combined_video;
            const card = document.getElementById('final-video-card');
            const videoEl = document.getElementById('final-video');
            const dlEl = document.getElementById('download-final');
            if (finalPath && card && videoEl && dlEl) {
                const fname = finalPath.split(/[/\\]/).pop();
                const url = `/media/output/${encodeURIComponent(fname)}`;
                videoEl.src = url;
                dlEl.href = url;
                dlEl.setAttribute('download', fname);
                card.classList.remove('hidden');
            } else if (card) {
                card.classList.add('hidden');
            }
        } catch (e) {
            console.warn('Final video not available:', e);
        }
    }

    hideResults() {
        document.getElementById('results-section').classList.add('hidden');
    }

    showError(message) {
        document.getElementById('error-message').textContent = message;
        document.getElementById('error-section').classList.remove('hidden');
    }

    hideError() {
        document.getElementById('error-section').classList.add('hidden');
    }

    resetForm() {
        this.clearFileSelection();
        this.hideProgress();
        this.hideResults();
        this.hideError();
        this.currentJobId = null;
        
        // Reset form values
        document.getElementById('model-select').value = 'small';
        document.getElementById('language-select').value = '';
        document.getElementById('compute-type').value = 'int8_float16';
        document.getElementById('vad-filter').checked = false;
    }

    async downloadFile(filename) {
        if (!this.currentJobId) return;

        try {
            // Add loading state to download button
            const downloadButton = event.target.closest('a');
            const originalText = downloadButton.innerHTML;
            downloadButton.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Downloading...';
            downloadButton.classList.add('opacity-75', 'pointer-events-none');

            const response = await fetch(`/api/download/${this.currentJobId}/${filename}`);
            
            if (!response.ok) {
                throw new Error('Download failed');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);

            // Reset button state
            downloadButton.innerHTML = originalText;
            downloadButton.classList.remove('opacity-75', 'pointer-events-none');
            
            // Add success feedback
            downloadButton.classList.add('animate-success-bounce');
            setTimeout(() => {
                downloadButton.classList.remove('animate-success-bounce');
            }, 2000);
            
        } catch (error) {
            console.error('Download error:', error);
            this.showError('Download failed. Please try again.');
            
            // Reset button state on error
            const downloadButton = event.target.closest('a');
            downloadButton.innerHTML = originalText;
            downloadButton.classList.remove('opacity-75', 'pointer-events-none');
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CaptionExtractor();
});
