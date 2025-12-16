document.addEventListener('DOMContentLoaded', function() {
    const fileDropArea = document.getElementById('fileDropArea');
    const fileInput = document.getElementById('id_attachments');
    const fileList = document.getElementById('fileList');
    const uploadProgress = document.getElementById('uploadProgress');
    const supportForm = document.getElementById('supportForm');
    const submitBtn = document.getElementById('submitBtn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoading = submitBtn.querySelector('.btn-loading');

    let currentFile = null;
    const MAX_FILE_SIZE = 25 * 1024 * 1024; // 25MB

    function formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    function getFileIcon(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const iconMap = {
            'jpg': 'fas fa-file-image',
            'jpeg': 'fas fa-file-image',
            'png': 'fas fa-file-image',
            'gif': 'fas fa-file-image',
            'bmp': 'fas fa-file-image',
            'pdf': 'fas fa-file-pdf',
            'doc': 'fas fa-file-word',
            'docx': 'fas fa-file-word',
            'txt': 'fas fa-file-alt',
            'mp4': 'fas fa-file-video',
            'avi': 'fas fa-file-video',
            'mov': 'fas fa-file-video',
            'webm': 'fas fa-file-video',
            'zip': 'fas fa-file-archive',
            'rar': 'fas fa-file-archive'
        };
        return iconMap[ext] || 'fas fa-file';
    }

    function getFileType(filename) {
        const ext = filename.split('.').pop().toLowerCase();
        const typeMap = {
            'jpg': 'Изображение',
            'jpeg': 'Изображение',
            'png': 'Изображение',
            'gif': 'Изображение',
            'bmp': 'Изображение',
            'pdf': 'PDF',
            'doc': 'Документ',
            'docx': 'Документ',
            'txt': 'Текст',
            'mp4': 'Видео',
            'avi': 'Видео',
            'mov': 'Видео',
            'webm': 'Видео',
            'zip': 'Архив',
            'rar': 'Архив'
        };
        return typeMap[ext] || 'Файл';
    }

    function updateProgressBar(fileSize) {
        const progress = (fileSize / MAX_FILE_SIZE) * 100;
        uploadProgress.style.width = Math.min(progress, 100) + '%';
        
        if (progress > 80) {
            uploadProgress.style.background = '#dc3545';
        } else if (progress > 60) {
            uploadProgress.style.background = '#ffc107';
        } else {
            uploadProgress.style.background = 'linear-gradient(90deg, #0052cc, #0066cc)';
        }
    }

    function addFileToList(file) {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <div class="file-info">
                <div class="file-icon">
                    <i class="${getFileIcon(file.name)}"></i>
                </div>
                <div style="flex: 1;">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">
                        ${formatFileSize(file.size)}
                        <span class="file-type-badge">${getFileType(file.name)}</span>
                    </div>
                </div>
            </div>
            <button type="button" class="file-remove" onclick="removeFile()">
                <i class="fas fa-times"></i> Удалить
            </button>
        `;
        fileList.innerHTML = '';
        fileList.appendChild(fileItem);
    }

    window.removeFile = function() {
        currentFile = null;
        fileInput.value = '';
        fileList.innerHTML = '';
        uploadProgress.style.width = '0%';
    };

    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, preventDefaults, false);
    });

    function preventDefaults(e) {
        e.preventDefault();
        e.stopPropagation();
    }

    ['dragenter', 'dragover'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, () => {
            fileDropArea.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        fileDropArea.addEventListener(eventName, () => {
            fileDropArea.classList.remove('dragover');
        }, false);
    });

    fileDropArea.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        handleFiles(files);
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    function handleFiles(files) {
        if (files.length === 0) return;

        const file = files[0];

        if (file.size > MAX_FILE_SIZE) {
            alert(`Файл "${file.name}" слишком большой. Максимальный размер 25MB.`);
            return;
        }

        currentFile = file;
        addFileToList(file);
        updateProgressBar(file.size);
    }

    supportForm.addEventListener('submit', function(e) {
        const subject = document.getElementById('id_subject').value.trim();
        const description = document.getElementById('id_description').value.trim();

        if (!subject) {
            e.preventDefault();
            alert('Пожалуйста, укажите тему обращения.');
            return;
        }

        if (!description) {
            e.preventDefault();
            alert('Пожалуйста, опишите вашу проблему.');
            return;
        }

        btnText.style.display = 'none';
        btnLoading.style.display = 'inline-block';
        submitBtn.disabled = true;
    });

    if (typeof AOS !== 'undefined') {
        AOS.init({
            duration: 800,
            once: true,
            offset: 100
        });
    }

    console.log('Страница поддержки инициализирована');
});