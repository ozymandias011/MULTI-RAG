// ============================================================================
// STATE MANAGEMENT
// ============================================================================

let currentUser = null;
let currentSession = null;
let currentFileId = null;
let currentDocumentUrl = null;
let authToken = null;

// ============================================================================
// DOM ELEMENTS
// ============================================================================

const authModal = document.getElementById('authModal');
const loginForm = document.getElementById('loginForm');
const registerForm = document.getElementById('registerForm');
const mainApp = document.getElementById('mainApp');

const uploadBox = document.getElementById('uploadBox');
const fileInput = document.getElementById('fileInput');
const uploadSection = document.getElementById('uploadSection');
const uploadedFile = document.getElementById('uploadedFile');
const fileName = document.getElementById('fileName');
const documentUrl = document.getElementById('documentUrl');
const uploadProgress = document.getElementById('uploadProgress');
const progressFill = document.getElementById('progressFill');
const progressPercent = document.getElementById('progressPercent');

const questionInput = document.getElementById('questionInput');
const sendBtn = document.getElementById('sendBtn');
const messages = document.getElementById('messages');
const welcomeScreen = document.getElementById('welcomeScreen');
const chatContainer = document.getElementById('chatContainer');
const chatInputWrapper = document.getElementById('chatInputWrapper');

const sessionsList = document.getElementById('sessionsList');
const sessionTitle = document.getElementById('sessionTitle');
const usernameDisplay = document.getElementById('usernameDisplay');
const deleteSessionBtn = document.getElementById('deleteSessionBtn');
const themeToggle = document.getElementById('themeToggle');
const editTitleBtn = document.getElementById('editTitleBtn');
const sessionTitleText = document.getElementById('sessionTitleText');
const sessionTitleInput = document.getElementById('sessionTitleInput');
const saveTitleBtn = document.getElementById('saveTitleBtn');
const cancelTitleBtn = document.getElementById('cancelTitleBtn');
const titleActions = document.getElementById('titleActions');
const sidebar = document.getElementById('sidebar');
const sidebarCollapseBtn = document.getElementById('sidebarCollapseBtn');
const floatingToggle = document.getElementById('floatingToggle');

// Home page elements
const featureUploadCard = document.getElementById('featureUpload');
const homeFileInput = document.getElementById('homeFileInput');

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    console.log('[INIT] Application starting...');
    initializeMarked();
    initializeTheme();
    initializeSidebar();
    checkAuth();
    initializeEventListeners();
});

function initializeMarked() {
    // Configure marked.js for markdown rendering
    if (typeof marked !== 'undefined') {
        marked.setOptions({
            breaks: true,
            gfm: true,
            headerIds: false,
            mangle: false,
            sanitize: false,
            highlight: function(code, lang) {
                if (typeof hljs !== 'undefined') {
                    if (lang && hljs.getLanguage(lang)) {
                        try {
                            return hljs.highlight(code, { language: lang }).value;
                        } catch (err) {
                            console.error('Highlight error:', err);
                        }
                    }
                    try {
                        return hljs.highlightAuto(code).value;
                    } catch (err) {
                        console.error('Highlight auto error:', err);
                    }
                }
                return code;
            }
        });
    }
}

function initializeEventListeners() {
    // Auth forms
    loginForm.addEventListener('submit', handleLogin);
    registerForm.addEventListener('submit', handleRegister);
    
    // File upload
    uploadBox.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', handleFileSelect);
    
    // Drag and drop - enhanced
    uploadBox.addEventListener('dragenter', handleDragEnter);
    uploadBox.addEventListener('dragover', handleDragOver);
    uploadBox.addEventListener('dragleave', handleDragLeave);
    uploadBox.addEventListener('drop', handleDrop);
    
    // Global drag events for better UX
    document.addEventListener('dragenter', (e) => {
        if (uploadSection.style.display !== 'none' && e.dataTransfer.types.includes('Files')) {
            uploadBox.classList.add('drag-over');
        }
    });
    
    // Send message
    sendBtn.addEventListener('click', sendMessage);
    questionInput.addEventListener('keydown', handleKeyDown);
    
    // Auto-resize textarea
    questionInput.addEventListener('input', autoResizeTextarea);
    
    // Document URL input
    documentUrl.addEventListener('input', handleDocumentUrlChange);

    // Theme toggle
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }

    // Sidebar toggle - collapse button inside sidebar
    if (sidebarCollapseBtn) {
        sidebarCollapseBtn.addEventListener('click', collapseSidebar);
    }

    // Sidebar toggle - floating button to open sidebar
    if (floatingToggle) {
        floatingToggle.addEventListener('click', expandSidebar);
    }

    // Inline title editing
    if (editTitleBtn) editTitleBtn.addEventListener('click', startEditTitle);
    if (saveTitleBtn) saveTitleBtn.addEventListener('click', saveEditTitle);
    if (cancelTitleBtn) cancelTitleBtn.addEventListener('click', cancelEditTitle);

    // Home page upload card (combined click + drag & drop)
    if (featureUploadCard) {
        featureUploadCard.addEventListener('click', () => homeFileInput.click());
        featureUploadCard.addEventListener('dragenter', handleHomeDragEnter);
        featureUploadCard.addEventListener('dragover', handleHomeDragOver);
        featureUploadCard.addEventListener('dragleave', handleHomeDragLeave);
        featureUploadCard.addEventListener('drop', handleHomeDrop);
    }
    if (homeFileInput) {
        homeFileInput.addEventListener('change', handleHomeFileSelect);
    }
}

// ============================================================================
// SIDEBAR TOGGLE
// ============================================================================

function collapseSidebar() {
    if (sidebar) {
        sidebar.classList.add('collapsed');
        localStorage.setItem('mulrag-sidebar', 'collapsed');
        updateFloatingToggleVisibility();
    }
}

function expandSidebar() {
    if (sidebar) {
        sidebar.classList.remove('collapsed');
        localStorage.setItem('mulrag-sidebar', 'open');
        updateFloatingToggleVisibility();
    }
}

function toggleSidebar() {
    if (sidebar) {
        sidebar.classList.toggle('collapsed');
        const isCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('mulrag-sidebar', isCollapsed ? 'collapsed' : 'open');
        updateFloatingToggleVisibility();
    }
}

function updateFloatingToggleVisibility() {
    if (floatingToggle && sidebar) {
        if (sidebar.classList.contains('collapsed')) {
            floatingToggle.style.display = 'flex';
        } else {
            floatingToggle.style.display = 'none';
        }
    }
}

function initializeSidebar() {
    const state = localStorage.getItem('mulrag-sidebar');
    if (state === 'collapsed' && sidebar) {
        sidebar.classList.add('collapsed');
    }
    updateFloatingToggleVisibility();
}

// ============================================================================
// THEME TOGGLING
// ============================================================================

function initializeTheme() {
    const saved = localStorage.getItem('mulrag-theme');
    const prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    const theme = saved || (prefersDark ? 'dark' : 'light');
    setTheme(theme);
}

function toggleTheme() {
    const current = document.body.getAttribute('data-theme') === 'dark' ? 'dark' : 'light';
    const next = current === 'dark' ? 'light' : 'dark';
    setTheme(next);
    localStorage.setItem('mulrag-theme', next);
}

function setTheme(theme) {
    if (theme === 'dark') {
        document.body.setAttribute('data-theme', 'dark');
        if (themeToggle) themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    } else {
        document.body.removeAttribute('data-theme');
        if (themeToggle) themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
    }
}

// ============================================================================
// AUTHENTICATION
// ============================================================================

function checkAuth() {
    console.log('[AUTH] Checking authentication...');
    const token = localStorage.getItem('authToken');
    
    if (token) {
        authToken = token;
        verifyToken();
    } else {
        showAuthModal();
    }
}

async function verifyToken() {
    console.log('[AUTH] Verifying token...');
    
    try {
        const response = await fetch('/api/v1/auth/me', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            currentUser = data.user;
            console.log('[AUTH] User authenticated:', currentUser.username);
            showMainApp();
        } else {
            localStorage.removeItem('authToken');
            showAuthModal();
        }
    } catch (error) {
        console.error('[AUTH] Error verifying token:', error);
        localStorage.removeItem('authToken');
        showAuthModal();
    }
}

async function handleLogin(e) {
    e.preventDefault();
    console.log('[AUTH] Login attempt...');
    
    const email = document.getElementById('loginEmail').value;
    const password = document.getElementById('loginPassword').value;
    
    const submitBtn = loginForm.querySelector('button[type="submit"]');
    submitBtn.classList.add('btn-loading');
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/api/v1/auth/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('authToken', authToken);
            console.log('[AUTH] Login successful');
            showToast('Welcome back, ' + currentUser.username + '!', 'success');
            showMainApp();
        } else {
            showToast(data.detail || 'Login failed', 'error');
        }
    } catch (error) {
        console.error('[AUTH] Login error:', error);
        showToast('Login failed. Please try again.', 'error');
    } finally {
        submitBtn.classList.remove('btn-loading');
        submitBtn.disabled = false;
    }
}

async function handleRegister(e) {
    e.preventDefault();
    console.log('[AUTH] Registration attempt...');
    
    const username = document.getElementById('registerUsername').value;
    const email = document.getElementById('registerEmail').value;
    const password = document.getElementById('registerPassword').value;
    
    if (password.length < 6) {
        showToast('Password must be at least 6 characters', 'error');
        return;
    }
    
    const submitBtn = registerForm.querySelector('button[type="submit"]');
    submitBtn.classList.add('btn-loading');
    submitBtn.disabled = true;
    
    try {
        const response = await fetch('/api/v1/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ username, email, password })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            authToken = data.token;
            currentUser = data.user;
            localStorage.setItem('authToken', authToken);
            console.log('[AUTH] Registration successful');
            showToast('Welcome, ' + currentUser.username + '!', 'success');
            showMainApp();
        } else {
            showToast(data.detail || 'Registration failed', 'error');
        }
    } catch (error) {
        console.error('[AUTH] Registration error:', error);
        showToast('Registration failed. Please try again.', 'error');
    } finally {
        submitBtn.classList.remove('btn-loading');
        submitBtn.disabled = false;
    }
}

function logout() {
    console.log('[AUTH] Logging out...');
    localStorage.removeItem('authToken');
    authToken = null;
    currentUser = null;
    currentSession = null;
    showAuthModal();
    showToast('Logged out successfully', 'info');
}

function showAuthModal() {
    authModal.classList.remove('hidden');
    mainApp.style.display = 'none';
}

function closeAuthModal() {
    if (currentUser) {
        authModal.classList.add('hidden');
    }
}

function switchToRegister() {
    loginForm.style.display = 'none';
    registerForm.style.display = 'flex';
    document.getElementById('authModalTitle').textContent = 'Create Account';
}

function switchToLogin() {
    registerForm.style.display = 'none';
    loginForm.style.display = 'flex';
    document.getElementById('authModalTitle').textContent = 'Welcome Back';
}

function showMainApp() {
    authModal.classList.add('hidden');
    mainApp.style.display = 'flex';
    usernameDisplay.textContent = currentUser.username;
    loadSessions();
    // Sidebar slide-in micro-interaction
    document.querySelector('.sidebar').classList.add('active');
}

// ============================================================================
// SESSION MANAGEMENT
// ============================================================================

async function loadSessions() {
    console.log('[SESSION] Loading user sessions...');
    
    try {
        const response = await fetch('/api/v1/sessions/list', {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            renderSessions(data.sessions);
        } else {
            showToast('Failed to load sessions', 'error');
        }
    } catch (error) {
        console.error('[SESSION] Error loading sessions:', error);
        showToast('Failed to load sessions', 'error');
    }
}

function renderSessions(sessions) {
    sessionsList.innerHTML = '';
    
    if (sessions.length === 0) {
        sessionsList.innerHTML = `
            <div class="empty-state">
                <i class="fas fa-comments"></i>
                <p>No sessions yet. Create one to start!</p>
            </div>
        `;
        return;
    }
    
    sessions.forEach(session => {
        const sessionItem = document.createElement('div');
        sessionItem.className = 'session-item';
        if (currentSession && currentSession.id === session.id) {
            sessionItem.classList.add('active');
        }
        
        sessionItem.innerHTML = `
            <div class="session-content" onclick="loadSession('${session.id}')">
                <div class="session-title">${escapeHtml(session.title)}</div>
                <div class="session-meta">
                    <span><i class="fas fa-comment"></i> ${session.message_count}</span>
                    <span>${formatDate(session.updated_at)}</span>
                </div>
            </div>
            <div class="session-menu">
                <button class="session-menu-btn" onclick="event.stopPropagation(); toggleSessionMenu('${session.id}', event)">
                    <i class="fas fa-ellipsis-v"></i>
                </button>
                <div class="session-menu-dropdown" id="menu-${session.id}">
                    <button onclick="event.stopPropagation(); renameSession('${session.id}', '${escapeHtml(session.title).replace(/'/g, "\\'")}')"><i class="fas fa-pen"></i> Rename</button>
                    <button onclick="event.stopPropagation(); deleteSession('${session.id}')"><i class="fas fa-trash"></i> Delete</button>
                    <button onclick="event.stopPropagation(); shareSession('${session.id}')" class="disabled"><i class="fas fa-share"></i> Share</button>
                </div>
            </div>
        `;
        
        sessionsList.appendChild(sessionItem);
    });
}

// Session menu functions
function toggleSessionMenu(sessionId, event) {
    // Close all other menus first
    document.querySelectorAll('.session-menu-dropdown.show').forEach(menu => {
        if (menu.id !== `menu-${sessionId}`) {
            menu.classList.remove('show');
        }
    });
    
    const menu = document.getElementById(`menu-${sessionId}`);
    const btn = event.currentTarget;
    
    if (menu) {
        if (menu.classList.contains('show')) {
            menu.classList.remove('show');
        } else {
            // Position the menu using fixed positioning
            const rect = btn.getBoundingClientRect();
            menu.style.top = `${rect.bottom + 4}px`;
            menu.style.left = `${rect.left - 100}px`; // Offset to align right edge with button
            menu.classList.add('show');
        }
    }
}

// Close menus when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.session-menu')) {
        document.querySelectorAll('.session-menu-dropdown.show').forEach(menu => {
            menu.classList.remove('show');
        });
    }
});

async function renameSession(sessionId, currentTitle) {
    const newTitle = prompt('Enter new session name:', currentTitle);
    if (newTitle && newTitle.trim() && newTitle !== currentTitle) {
        try {
            const response = await fetch(`/api/v1/sessions/${sessionId}/update`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${authToken}`
                },
                body: JSON.stringify({ title: newTitle.trim() })
            });
            const data = await response.json();
            if (response.ok) {
                showToast('Session renamed', 'success');
                loadSessions();
                // Update current session title if it's the active one
                if (currentSession && currentSession.id === sessionId) {
                    currentSession.title = newTitle.trim();
                    sessionTitleText.textContent = newTitle.trim();
                }
            } else {
                showToast(data.detail || 'Failed to rename session', 'error');
            }
        } catch (e) {
            console.error('Rename error:', e);
            showToast('Failed to rename session', 'error');
        }
    }
    // Close the menu
    document.querySelectorAll('.session-menu-dropdown.show').forEach(menu => menu.classList.remove('show'));
}

async function deleteSession(sessionId) {
    if (!confirm('Are you sure you want to delete this session?')) {
        return;
    }
    
    try {
        const response = await fetch(`/api/v1/sessions/${sessionId}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            showToast('Session deleted', 'success');
            loadSessions();
            // If deleted session is the current one, go to home
            if (currentSession && currentSession.id === sessionId) {
                goToHome();
            }
        } else {
            const data = await response.json();
            showToast(data.detail || 'Failed to delete session', 'error');
        }
    } catch (e) {
        console.error('Delete error:', e);
        showToast('Failed to delete session', 'error');
    }
    // Close the menu
    document.querySelectorAll('.session-menu-dropdown.show').forEach(menu => menu.classList.remove('show'));
}

function shareSession(sessionId) {
    showToast('Share feature coming soon!', 'info');
    document.querySelectorAll('.session-menu-dropdown.show').forEach(menu => menu.classList.remove('show'));
}

async function loadSession(sessionId) {
    console.log('[SESSION] Loading session:', sessionId);
    
    try {
        const response = await fetch(`/api/v1/sessions/${sessionId}/messages`, {
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentSession = data.session;
            sessionTitleText.textContent = data.session.title;
            deleteSessionBtn.style.display = 'block';
            editTitleBtn.style.display = 'inline-flex'; // Show edit button when session is loaded
            
            // Hide welcome screen and upload section
            welcomeScreen.style.display = 'none';
            uploadSection.style.display = 'none';
            chatInputWrapper.style.display = 'block';
            
            // Clear and render messages
            messages.innerHTML = '';
            data.messages.forEach(msg => {
                addMessage(msg.content, msg.type, msg.processing_time);
            });
            
            // Update sidebar
            loadSessions();
            
            console.log('[SESSION] Session loaded successfully');
        } else {
            showToast('Failed to load session', 'error');
        }
    } catch (error) {
        console.error('[SESSION] Error loading session:', error);
        showToast('Failed to load session', 'error');
    }
}

function newChat() {
    console.log('[SESSION] Starting new chat...');
    
    currentSession = null;
    currentFileId = null;
    currentDocumentUrl = null;
    
    sessionTitleText.textContent = 'New Chat Session';
    deleteSessionBtn.style.display = 'none';
    editTitleBtn.style.display = 'none'; // Hide edit button for new chat
    
    messages.innerHTML = '';
    welcomeScreen.style.display = 'none';
    uploadSection.style.display = 'block';
    chatInputWrapper.style.display = 'none';
    
    // Reset upload form
    uploadBox.style.display = 'block';
    uploadedFile.style.display = 'none';
    fileInput.value = '';
    documentUrl.value = '';
    
    // Update sidebar
    document.querySelectorAll('.session-item').forEach(item => {
        item.classList.remove('active');
    });
}

async function createSessionWithDocument() {
    console.log('[SESSION] Creating new session with document...');
    
    const urlValue = documentUrl.value.trim();
    
    // Validate we have something
    if (!currentFileId && !urlValue) {
        showToast('Please upload a PDF or provide a document URL', 'error');
        return;
    }
    
    // Validate URL format if URL is provided (and no file uploaded)
    if (urlValue && !currentFileId) {
        // Check if it's a valid URL
        if (!urlValue.startsWith('http://') && !urlValue.startsWith('https://')) {
            showToast('URL must start with http:// or https://', 'error');
            return;
        }
        
        // Optional: Check if it ends with .pdf
        if (!urlValue.toLowerCase().endsWith('.pdf')) {
            if (!confirm('This URL does not end with .pdf. Continue anyway?')) {
                return;
            }
        }
    }
    
    const title = 'New Session';
    
    const submitBtn = document.getElementById('startSessionBtn');
    submitBtn.classList.add('btn-loading');
    submitBtn.disabled = true;
    
    try {
        const requestBody = {
            title: title,
            document_id: currentFileId || null,
            document_url: (!currentFileId && urlValue) ? urlValue : null
        };
        
        console.log('[SESSION] Request body:', requestBody);
        
        const response = await fetch('/api/v1/sessions/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify(requestBody)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentSession = data.session;
            sessionTitle.textContent = data.session.title;
            deleteSessionBtn.style.display = 'block';
            
            uploadSection.style.display = 'none';
            chatInputWrapper.style.display = 'block';
            
            loadSessions();
            showToast('Session created! Start asking questions.', 'success');
            
            console.log('[SESSION] Session created:', currentSession.id);
        } else {
            showToast(data.detail || 'Failed to create session', 'error');
        }
    } catch (error) {
        console.error('[SESSION] Error creating session:', error);
        showToast('Failed to create session', 'error');
    } finally {
        submitBtn.classList.remove('btn-loading');
        submitBtn.disabled = false;
    }
}

async function deleteCurrentSession() {
    if (!currentSession) return;
    
    if (!confirm('Are you sure you want to delete this session? This cannot be undone.')) {
        return;
    }
    
    console.log('[SESSION] Deleting session:', currentSession.id);
    
    try {
        const response = await fetch(`/api/v1/sessions/${currentSession.id}`, {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (response.ok) {
            showToast('Session deleted', 'success');
            currentSession = null;
            sessionTitle.textContent = 'AI-Powered Document Q&A';
            deleteSessionBtn.style.display = 'none';
            messages.innerHTML = '';
            welcomeScreen.style.display = 'flex';
            chatInputWrapper.style.display = 'none';
            loadSessions();
        } else {
            showToast('Failed to delete session', 'error');
        }
    } catch (error) {
        console.error('[SESSION] Error deleting session:', error);
        showToast('Failed to delete session', 'error');
    }
}

// ============================================================================
// FILE UPLOAD
// ============================================================================

let dragCounter = 0;

function handleDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleDragEnter(e) {
    e.preventDefault();
    e.stopPropagation();
    dragCounter++;
    uploadBox.classList.add('drag-over');
}

function handleDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    dragCounter--;
    if (dragCounter === 0) {
        uploadBox.classList.remove('drag-over');
    }
}

function handleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    dragCounter = 0;
    uploadBox.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleFile(files[0]);
    }
}

function handleFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        handleFile(file);
    }
}

async function handleFile(file) {
    console.log('[UPLOAD] Starting file upload:', file.name);
    
    if (!file.name.endsWith('.pdf')) {
        showToast('Please upload a PDF file', 'error');
        return;
    }
    
    if (file.size >100 * 1024 * 1024) {
        showToast('File size must be less than 50MB', 'error');
        return;
    }
    
    // Show progress
    document.querySelector('.upload-content').style.display = 'none';
    uploadProgress.style.display = 'block';
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const xhr = new XMLHttpRequest();
        
        // Progress tracking
        xhr.upload.addEventListener('progress', (e) => {
            if (e.lengthComputable) {
                const percentComplete = (e.loaded / e.total) * 100;
                progressFill.style.width = percentComplete + '%';
                progressPercent.textContent = Math.round(percentComplete) + '%';
            }
        });
        
        // Load complete
        xhr.addEventListener('load', () => {
            if (xhr.status === 200) {
                const result = JSON.parse(xhr.responseText);
                currentFileId = result.file_id;
                currentDocumentUrl = null;
                documentUrl.value = '';
                
                fileName.textContent = result.filename;
                uploadBox.style.display = 'none';
                uploadedFile.style.display = 'flex';
                uploadProgress.style.display = 'none';
                document.querySelector('.upload-content').style.display = 'block';
                
                showToast('PDF uploaded successfully!', 'success');
                console.log('[UPLOAD] Upload complete:', result.file_id);
            } else {
                throw new Error('Upload failed');
            }
        });
        
        // Error handling
        xhr.addEventListener('error', () => {
            throw new Error('Upload failed');
        });
        
        xhr.open('POST', '/api/v1/upload-pdf');
        xhr.setRequestHeader('Authorization', `Bearer ${authToken}`);
        xhr.send(formData);
        
    } catch (error) {
        console.error('[UPLOAD] Error:', error);
        showToast('Failed to upload PDF. Please try again.', 'error');
        uploadProgress.style.display = 'none';
        document.querySelector('.upload-content').style.display = 'block';
    }
}

function removeFile() {
    currentFileId = null;
    fileInput.value = '';
    uploadBox.style.display = 'block';
    uploadedFile.style.display = 'none';
    fileName.textContent = '';
}

function handleDocumentUrlChange(e) {
    const url = e.target.value.trim();
    if (url) {
        currentDocumentUrl = url;
        currentFileId = null;
    } else {
        currentDocumentUrl = null;
    }
}

// ============================================================================
// HOME PAGE UPLOAD & FEATURE CARDS
// ============================================================================

let homeDragCounter = 0;

function handleHomeDragEnter(e) {
    e.preventDefault();
    e.stopPropagation();
    homeDragCounter++;
    featureUploadCard.classList.add('drag-over');
}

function handleHomeDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
}

function handleHomeDragLeave(e) {
    e.preventDefault();
    e.stopPropagation();
    homeDragCounter--;
    if (homeDragCounter === 0) {
        featureUploadCard.classList.remove('drag-over');
    }
}

function handleHomeDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    homeDragCounter = 0;
    featureUploadCard.classList.remove('drag-over');
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
        handleHomeFile(files[0]);
    }
}

function handleHomeFileSelect(e) {
    const file = e.target.files[0];
    if (file) {
        handleHomeFile(file);
    }
}

async function handleHomeFile(file) {
    console.log('[HOME UPLOAD] Starting file upload:', file.name);
    
    if (!file.name.endsWith('.pdf')) {
        showToast('Please upload a PDF file', 'error');
        return;
    }
    
    if (file.size > 100 * 1024 * 1024) {
        showToast('File size must be less than 100MB', 'error');
        return;
    }
    
    // Show loading state
    showToast('Uploading PDF...', 'info');
    
    try {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch('/api/v1/upload-pdf', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });
        
        if (response.ok) {
            const result = await response.json();
            currentFileId = result.file_id;
            currentDocumentUrl = null;
            
            showToast('PDF uploaded! Creating session...', 'success');
            
            // Automatically create session
            await createSessionFromHome(file.name);
        } else {
            throw new Error('Upload failed');
        }
    } catch (error) {
        console.error('[HOME UPLOAD] Error:', error);
        showToast('Failed to upload PDF. Please try again.', 'error');
    }
}

async function createSessionFromHome(filename) {
    console.log('[SESSION] Creating session from home page...');
    
    try {
        const response = await fetch('/api/v1/sessions/create', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({
                title: 'New Session',
                document_id: currentFileId,
                document_url: null
            })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            currentSession = data.session;
            sessionTitleText.textContent = data.session.title;
            deleteSessionBtn.style.display = 'block';
            
            // Switch to chat view
            welcomeScreen.style.display = 'none';
            uploadSection.style.display = 'none';
            chatInputWrapper.style.display = 'block';
            
            loadSessions();
            showToast('Session created! Start asking questions.', 'success');
            
            // Focus on input
            questionInput.focus();
            
            console.log('[SESSION] Session created from home:', currentSession.id);
        } else {
            showToast(data.detail || 'Failed to create session', 'error');
        }
    } catch (error) {
        console.error('[SESSION] Error creating session:', error);
        showToast('Failed to create session', 'error');
    }
}

function showRecentSessions() {
    // Expand sidebar if collapsed
    if (sidebar && sidebar.classList.contains('collapsed')) {
        expandSidebar();
    }
    
    // Scroll to sessions list and highlight it briefly
    if (sessionsList) {
        sessionsList.scrollIntoView({ behavior: 'smooth', block: 'start' });
        sessionsList.classList.add('highlight-sessions');
        setTimeout(() => {
            sessionsList.classList.remove('highlight-sessions');
        }, 2000);
    }
    
    // If there are sessions, load the first one
    const firstSession = sessionsList.querySelector('.session-item');
    if (firstSession) {
        firstSession.click();
    } else {
        showToast('No previous sessions found. Upload a PDF to start!', 'info');
    }
}

function goToHome() {
    console.log('[NAV] Going to home page...');
    
    // Reset session state
    currentSession = null;
    currentFileId = null;
    currentDocumentUrl = null;
    
    // Update UI
    sessionTitleText.textContent = 'AI-Powered Document Q&A';
    deleteSessionBtn.style.display = 'none';
    editTitleBtn.style.display = 'none'; // Hide edit button on home
    
    // Clear messages
    messages.innerHTML = '';
    
    // Show welcome screen, hide chat elements
    welcomeScreen.style.display = 'flex';
    uploadSection.style.display = 'none';
    chatInputWrapper.style.display = 'none';
    
    // Deselect any active session in sidebar
    document.querySelectorAll('.session-item').forEach(item => {
        item.classList.remove('active');
    });
    
    // Reset home file input
    if (homeFileInput) {
        homeFileInput.value = '';
    }
}

// ============================================================================
// MESSAGING
// ============================================================================

async function sendMessage() {
    const question = questionInput.value.trim();
    
    if (!question) {
        showToast('Please enter a question', 'error');
        return;
    }
    
    if (!currentSession) {
        showToast('Please create a session first', 'error');
        return;
    }
    
    console.log('[CHAT] Sending message:', question);
    
    // Add user message
    addMessage(question, 'user');
    questionInput.value = '';
    autoResizeTextarea();
    
    // Show typing indicator
    const typingId = addTypingIndicator();
    
    // Disable send button
    sendBtn.disabled = true;
    
    try {
        const formData = new FormData();
        formData.append('question', question);
        formData.append('session_id', currentSession.id);
        
        const response = await fetch('/api/v1/chat', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`
            },
            body: formData
        });
        
        const data = await response.json();
        
        removeTypingIndicator(typingId);
        
        if (response.ok) {
            addMessage(data.answer, 'bot', data.processing_time);
            
            // Check if session was auto-named (first question)
            const sessionTitle = response.headers.get('X-Session-Title');
            if (sessionTitle) {
                console.log('[CHAT] Session auto-named to:', sessionTitle);
                // Update the session title in the UI
                if (currentSession) {
                    currentSession.title = sessionTitle;
                    document.getElementById('sessionTitle').textContent = sessionTitle;
                }
                // Reload sessions list to show the new title
                loadSessions();
            } else {
                loadSessions(); // Update session list normally
            }
            
            console.log('[CHAT] Response received in', data.processing_time);
        } else {
            showToast(data.detail || 'Failed to get answer', 'error');
        }
    } catch (error) {
        console.error('[CHAT] Error:', error);
        removeTypingIndicator(typingId);
        showToast('Failed to get answer. Please try again.', 'error');
    } finally {
        sendBtn.disabled = false;
    }
}

function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
}

function autoResizeTextarea() {
    questionInput.style.height = 'auto';
    questionInput.style.height = questionInput.scrollHeight + 'px';
}

// ============================================================================
// UI FUNCTIONS - ENHANCED WITH MARKDOWN RENDERING
// ============================================================================

function addMessage(text, type, processingTime = null) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${type}-message`;
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = type === 'user' 
        ? '<i class="fas fa-user"></i>' 
        : '<i class="fas fa-robot"></i>';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    const messageText = document.createElement('div');
    messageText.className = 'message-text';
    
    // ENHANCED: Render markdown for bot messages
    if (type === 'bot' && typeof marked !== 'undefined') {
        try {
            // Parse markdown
            let htmlContent = marked.parse(text);
            
            // Wrap code blocks with copy button
            htmlContent = wrapCodeBlocks(htmlContent);
            
            messageText.innerHTML = htmlContent;
            
            // Apply syntax highlighting to any remaining code blocks
            if (typeof hljs !== 'undefined') {
                messageText.querySelectorAll('pre code').forEach((block) => {
                    hljs.highlightElement(block);
                });
            }
        } catch (error) {
            console.error('Markdown parsing error:', error);
            messageText.textContent = text;
        }
    } else {
        // Plain text for user messages or if marked is not available
        messageText.textContent = text;
    }
    
    const meta = document.createElement('div');
    meta.className = 'message-meta';
    
    const time = document.createElement('span');
    time.className = 'message-time';
    time.innerHTML = `<i class="fas fa-clock"></i> ${formatTime(new Date())}`;
    meta.appendChild(time);
    
    if (processingTime) {
        const processingSpan = document.createElement('span');
        processingSpan.innerHTML = `<i class="fas fa-bolt"></i> ${processingTime}`;
        meta.appendChild(processingSpan);
    }
    
    content.appendChild(messageText);
    content.appendChild(meta);
    
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    
    messages.appendChild(messageDiv);
    
    // Smooth scroll to bottom
    chatContainer.scrollTo({
        top: chatContainer.scrollHeight,
        behavior: 'smooth'
    });
}

// Inline title edit handlers
function startEditTitle() {
    if (!currentSession) {
        showToast('Open a session to rename', 'error');
        return;
    }
    sessionTitleInput.value = currentSession.title || '';
    sessionTitleText.style.display = 'none';
    sessionTitleInput.style.display = 'inline-block';
    titleActions.style.display = 'inline-block';
    editTitleBtn.style.display = 'none';
    sessionTitleInput.focus();
}

async function saveEditTitle() {
    const newTitle = sessionTitleInput.value.trim();
    if (!newTitle) {
        showToast('Title cannot be empty', 'error');
        return;
    }
    try {
        const response = await fetch(`/api/v1/sessions/${currentSession.id}/update`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${authToken}`
            },
            body: JSON.stringify({ title: newTitle })
        });
        const data = await response.json();
        if (response.ok) {
            currentSession.title = newTitle;
            sessionTitleText.textContent = newTitle;
            showToast('Session renamed', 'success');
            cancelEditTitle();
            loadSessions();
        } else {
            showToast(data.detail || 'Failed to rename session', 'error');
        }
    } catch (e) {
        console.error('Rename error:', e);
        showToast('Failed to rename session', 'error');
    }
}

function cancelEditTitle() {
    sessionTitleText.style.display = 'inline';
    sessionTitleInput.style.display = 'none';
    titleActions.style.display = 'none';
    editTitleBtn.style.display = 'inline-flex';
}

// NEW: Function to wrap code blocks with copy button and language label
function wrapCodeBlocks(html) {
    const parser = new DOMParser();
    const doc = parser.parseFromString(html, 'text/html');
    
    doc.querySelectorAll('pre').forEach((pre) => {
        const code = pre.querySelector('code');
        if (code) {
            const wrapper = document.createElement('div');
            wrapper.className = 'code-block-wrapper';
            
            // Detect language
            let language = 'text';
            const classes = code.className.split(' ');
            for (const cls of classes) {
                if (cls.startsWith('language-')) {
                    language = cls.replace('language-', '');
                    break;
                } else if (cls.startsWith('hljs')) {
                    // Skip hljs classes
                    continue;
                } else if (cls) {
                    language = cls;
                    break;
                }
            }
            
            // Add language label
            if (language !== 'text') {
                const langLabel = document.createElement('span');
                langLabel.className = 'code-language';
                langLabel.textContent = language;
                wrapper.appendChild(langLabel);
            }
            
            // Add copy button
            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-code-btn';
            copyBtn.innerHTML = '<i class="fas fa-copy"></i> Copy';
            copyBtn.onclick = () => copyCodeToClipboard(code.textContent, copyBtn);
            wrapper.appendChild(copyBtn);
            
            // Wrap pre element
            pre.parentNode.insertBefore(wrapper, pre);
            wrapper.appendChild(pre);
        }
    });
    
    return doc.body.innerHTML;
}

// NEW: Function to copy code to clipboard
function copyCodeToClipboard(text, button) {
    navigator.clipboard.writeText(text).then(() => {
        const originalHTML = button.innerHTML;
        button.innerHTML = '<i class="fas fa-check"></i> Copied!';
        button.classList.add('copied');
        
        setTimeout(() => {
            button.innerHTML = originalHTML;
            button.classList.remove('copied');
        }, 2000);
    }).catch(err => {
        console.error('Failed to copy:', err);
        showToast('Failed to copy code', 'error');
    });
}

function addTypingIndicator() {
    const id = 'typing-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.id = id;
    messageDiv.className = 'message bot-message';
    
    const avatar = document.createElement('div');
    avatar.className = 'message-avatar';
    avatar.innerHTML = '<i class="fas fa-robot"></i>';
    
    const content = document.createElement('div');
    content.className = 'message-content';
    
    const typingIndicator = document.createElement('div');
    typingIndicator.className = 'typing-indicator';
    typingIndicator.innerHTML = `
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
        <span class="typing-dot"></span>
    `;
    
    content.appendChild(typingIndicator);
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(content);
    
    messages.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    return id;
}

function removeTypingIndicator(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    
    const icon = type === 'success' ? 'check-circle' : 
                 type === 'error' ? 'exclamation-circle' : 
                 'info-circle';
    
    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas fa-${icon}"></i>
        </div>
        <div class="toast-message">${escapeHtml(message)}</div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'slideOutRight 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================================================
// UTILITY FUNCTIONS
// ============================================================================

function formatTime(date) {
    return date.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit' 
    });
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}