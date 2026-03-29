
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
            this.downloadFile('transcript.txt', e);
        });

        document.getElementById('download-segments').addEventListener('click', (e) => {
            e.preventDefault();
            this.downloadFile('segments.json', e);
        });

        document.getElementById('download-words').addEventListener('click', (e) => {
            e.preventDefault();
            this.downloadFile('words.json', e);
        });

        document.getElementById('download-srt').addEventListener('click', (e) => {
            e.preventDefault();
            this.downloadFile('transcript.srt', e);
        });

        document.getElementById('download-vtt').addEventListener('click', (e) => {
            e.preventDefault();
            this.downloadFile('transcript.vtt', e);
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

        // Validate file size (500MB)
        if (file.size > 500 * 1024 * 1024) {
            this.showError('File too large. Maximum size is 500MB.');
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

            this.updateProgress(10, 'Uploading file to server...');
            this.startProgressSimulation();

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData,
                signal: AbortSignal.timeout(600000),
            });

            this.stopProgressSimulation();
            this.updateProgress(95, 'Receiving results...');

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
            this.stopProgressSimulation();
            this.hideProgress();
            this.showError(error.message || 'Upload failed. Please try again.');
        }
    }

    showProgress() {
        document.getElementById('progress-section').classList.remove('hidden');
        this.updateProgress(0, 'Starting upload...');
    }

    hideProgress() {
        this.stopProgressSimulation();
        document.getElementById('progress-section').classList.add('hidden');
    }

    startProgressSimulation() {
        const phases = [
            { at: 15, text: 'Transcribing audio with Whisper...' },
            { at: 30, text: 'Analyzing transcript segments...' },
            { at: 45, text: 'Selecting best clips via GPT-4o...' },
            { at: 55, text: 'Extracting video segments with FFmpeg...' },
            { at: 65, text: 'Generating candidate compilations...' },
            { at: 75, text: 'Encoding candidate videos...' },
            { at: 85, text: 'Finalizing output...' },
        ];

        let phaseIndex = 0;
        let currentPercent = 10;

        this._progressInterval = setInterval(() => {
            if (phaseIndex < phases.length && currentPercent >= phases[phaseIndex].at - 1) {
                this.updateProgress(phases[phaseIndex].at, phases[phaseIndex].text);
                currentPercent = phases[phaseIndex].at;
                phaseIndex++;
            } else if (currentPercent < 90) {
                currentPercent += 0.5;
                document.getElementById('progress-fill').style.width = currentPercent + '%';
            }
        }, 2000);
    }

    stopProgressSimulation() {
        if (this._progressInterval) {
            clearInterval(this._progressInterval);
            this._progressInterval = null;
        }
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

        let totalFiles = 5; // transcript files

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
                totalFiles += 1;
            } else if (card) {
                card.classList.add('hidden');
            }
        } catch (e) {
            console.warn('Final video not available:', e);
        }

        // Handle candidate videos
        try {
            const candidatesSection = document.getElementById('candidates-section');
            const candidatesList = document.getElementById('candidates-list');
            if (result.candidates && result.candidates.length > 0 && candidatesSection && candidatesList) {
                candidatesList.innerHTML = '';
                this.renderCandidates(result.candidates, candidatesList);
                candidatesSection.classList.remove('hidden');
                totalFiles += result.candidates.length;
            } else if (candidatesSection) {
                candidatesSection.classList.add('hidden');
            }
        } catch (e) {
            console.warn('Candidate videos not available:', e);
        }

        // Update file count display
        const fileCountEl = document.getElementById('file-count');
        if (fileCountEl) {
            fileCountEl.textContent = `${totalFiles} available`;
        }

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
    }

    escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    renderCandidates(candidates, container) {
        const LABELS = {
            'all_clips':     { label: 'ALL CLIPS',      desc: 'All top-ranked clips in score order' },
            'high_score':    { label: 'HIGH SCORE',      desc: 'Only clips scoring above 0.85' },
            'short_clips':   { label: 'SHORT CLIPS',     desc: 'Clips under 35s for quick consumption' },
            'best_hooks':    { label: 'BEST HOOKS',      desc: 'Clips with strongest opening hooks' },
            'chronological': { label: 'CHRONOLOGICAL',   desc: 'Clips in original timeline order' },
            'segments':      { label: 'SEGMENTS',        desc: 'Individual transcript segments' },
            'no_promo':      { label: 'NO PROMO',        desc: 'Promotional content filtered out' },
        };

        candidates.forEach((absPath, index) => {
            const fname = absPath.split(/[/\\]/).pop();
            const url = `/media/candidates/${encodeURIComponent(fname)}`;

            let info = { label: `CANDIDATE ${index + 1}`, desc: fname };
            for (const [key, val] of Object.entries(LABELS)) {
                if (fname.includes(key)) {
                    info = val;
                    break;
                }
            }

            const card = document.createElement('div');
            card.className = 'candidate-card';
            card.style.animationDelay = `${index * 100}ms`;
            const safeLabel = this.escapeHtml(info.label);
            const safeDesc = this.escapeHtml(info.desc);
            const safeFname = this.escapeHtml(fname);
            card.innerHTML = `
                <p class="candidate-label">
                    <span class="text-terminal-amber">[${index + 1}]</span> ${safeLabel}
                </p>
                <p class="candidate-desc">&gt; ${safeDesc}</p>
                <div class="video-frame">
                    <video class="w-full bg-black" controls preload="metadata">
                        <source src="${url}" type="video/mp4">
                    </video>
                </div>
                <div class="candidate-actions">
                    <a href="${url}" download="${safeFname}" class="download-link">
                        [*] Download
                    </a>
                </div>
            `;
            container.appendChild(card);
        });
    }

    hideResults() {
        document.getElementById('results-section').classList.add('hidden');
        const candidatesSection = document.getElementById('candidates-section');
        if (candidatesSection) {
            candidatesSection.classList.add('hidden');
        }
        const candidatesList = document.getElementById('candidates-list');
        if (candidatesList) {
            candidatesList.querySelectorAll('video').forEach(v => { v.pause(); v.removeAttribute('src'); v.load(); });
            candidatesList.innerHTML = '';
        }
        const finalCard = document.getElementById('final-video-card');
        if (finalCard) {
            finalCard.classList.add('hidden');
        }
        const finalVideo = document.getElementById('final-video');
        if (finalVideo) {
            finalVideo.removeAttribute('src');
            finalVideo.load();
        }
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

    async downloadFile(filename, e) {
        if (!this.currentJobId) return;

        const downloadButton = e && e.target ? e.target.closest('a') : null;
        let originalText = '';

        try {
            if (downloadButton) {
                originalText = downloadButton.innerHTML;
                downloadButton.innerHTML = 'Downloading...';
                downloadButton.classList.add('opacity-75', 'pointer-events-none');
            }

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

            if (downloadButton) {
                downloadButton.innerHTML = originalText;
                downloadButton.classList.remove('opacity-75', 'pointer-events-none');
                downloadButton.classList.add('animate-success-bounce');
                setTimeout(() => {
                    downloadButton.classList.remove('animate-success-bounce');
                }, 2000);
            }

        } catch (error) {
            console.error('Download error:', error);
            this.showError('Download failed. Please try again.');
            if (downloadButton && originalText) {
                downloadButton.innerHTML = originalText;
                downloadButton.classList.remove('opacity-75', 'pointer-events-none');
            }
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new CaptionExtractor();
});
