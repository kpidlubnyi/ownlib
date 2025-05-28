class OwnLibAPI {
    constructor(baseUrl = '/api') {
        this.baseUrl = baseUrl;
        this.token = localStorage.getItem('access_token');
        this.activeRequests = new Map();
    }

    setToken(token) {
        this.token = token;
        localStorage.setItem('access_token', token);
    }

    clearToken() {
        this.token = null;
        localStorage.removeItem('access_token');
    }

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const requestKey = `${options.method || 'GET'}:${url}`;
        
        if ((options.method === 'GET' || !options.method) && endpoint === '/users/me') {
            if (this.activeRequests.has(requestKey)) {
                console.log(`🔄 Returning existing getCurrentUser request`);
                return this.activeRequests.get(requestKey);
            }
        }

        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        if (this.token) {
            config.headers.Authorization = `Bearer ${this.token}`;
        }

        const requestPromise = this._executeRequest(url, config);
        
        if ((options.method === 'GET' || !options.method) && endpoint === '/users/me') {
            this.activeRequests.set(requestKey, requestPromise);
            
            requestPromise.finally(() => {
                this.activeRequests.delete(requestKey);
            });
        }

        return requestPromise;
    }

    async _executeRequest(url, config) {
        try {
            console.log('Making request to:', url);
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('API Error Response:', {
                    status: response.status,
                    statusText: response.statusText,
                    url: url,
                    body: errorText
                });
                
                let errorData;
                try {
                    errorData = JSON.parse(errorText);
                } catch (e) {
                    errorData = { detail: errorText };
                }
                
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            if (response.status === 204) {
                return {};
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    }

    async get(endpoint, params = {}) {
        const queryString = new URLSearchParams(params).toString();
        const url = queryString ? `${endpoint}?${queryString}` : endpoint;
        return this.request(url, { method: 'GET' });
    }

    async post(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async put(endpoint, data = {}) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    async uploadFile(endpoint, formData) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const formKeys = Array.from(formData.keys()).join('_');
        const requestKey = `POST:${url}:${formKeys}`;
        
        if (this.activeRequests.has(requestKey)) {
            console.log(`🔄 Upload already in progress for: ${endpoint}`);
            throw new Error('The download is already in progress. Please wait a moment.');
        }
        
        const config = {
            method: 'POST',
            body: formData
        };

        if (this.token) {
            config.headers = {
                'Authorization': `Bearer ${this.token}`
            };
        }

        const uploadPromise = fetch(url, config).then(async response => {
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }
            return response.json();
        });
        
        this.activeRequests.set(requestKey, uploadPromise);
        
        uploadPromise.finally(() => {
            this.activeRequests.delete(requestKey);
            console.log(`🧹 Upload completed: ${endpoint}`);
        });

        return uploadPromise;
    }

    async register(userData) {
        return this.post('/auth/register', userData);
    }

    async login(email, password) {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);
        
        console.log('Attempting login with:', email);
        
        const response = await fetch(`${this.baseUrl}/auth/login`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error('Login error:', errorData);
            throw new Error(errorData.detail || 'Помилка входу');
        }

        const data = await response.json();
        this.setToken(data.access_token);
        console.log('Login successful');
        return data;
    }

    async getCurrentUser() {
        return this.get('/users/me');
    }

    async getBooks(params = {}) {
        return this.get('/books/', params);
    }

    async getBook(bookId) {
        return this.get(`/books/${bookId}`);
    }

    async searchBooks(query, languages = null, page = 1) {
        const params = { query, page };
        if (languages) params.languages = languages;
        return this.get('/books/search', params);
    }

    async getUserBooks(status = null) {
        const params = status ? { status } : {};
        return this.get('/books/user-books/', params);
    }

    async addBookToCollection(bookId, userBookData) {
        return this.post(`/books/user-books/${bookId}`, userBookData);
    }

    async removeBookFromCollection(bookId) {
        return this.delete(`/books/user-books/${bookId}`);
    }

    async importGutenbergBook(gutenbergId) {
        return this.get(`/books/gutenberg/${gutenbergId}`);
    }

    async uploadBookFile(file, title = null, author = null, language = null) {
        const formData = new FormData();
        formData.append('file', file);
        if (title) formData.append('title', title);
        if (author) formData.append('author', author);
        if (language) formData.append('language', language);
        
        return this.uploadFile('/files/upload-book', formData);
    }

    async deleteBookFile(userBookId) {
        return this.delete(`/files/books/${userBookId}`);
    }

    async getReadingStats() {
        return this.get('/stats/reading');
    }

    async getReadingHistory(days = 30) {
        return this.get('/stats/reading/history', { days });
    }

    async getReadingProgress(userBookId) {
        return this.get(`/stats/reading/progress/${userBookId}`);
    }

    async updateBookmark(userBookId, position) {
        return this.put(`/reading/bookmark/${userBookId}`, { position });
    }

    async importLibrary(file) {
        const formData = new FormData();
        formData.append('file', file);
        
        return this.uploadFile('/import-export/import-library', formData);
    }

    async requestPasswordReset(email) {
        return this.post('/auth/forgot-password', { email });
    }

    async resetPassword(email, newPassword) {
        return this.post('/auth/reset-password', { 
            email, 
            new_password: newPassword 
        });
    }

    static validateLanguageCode(language) {
        if (!language) return null;
        
        language = language.trim().toLowerCase();
        
        if (!/^[a-z]{2}$/.test(language)) {
            throw new Error('The language code must consist of two lowercase Latin letters (for example: en, uk, pl, ru)');
        }
        
        return language;
    }

    clearActiveRequests() {
        this.activeRequests.clear();
        console.log('🧹 Cleared all active requests');
    }
}

class OwnLibUI {
    constructor() {
        this.api = new OwnLibAPI();
        this.currentUser = null;
        this.isInitialized = false;
    }

    async init() {
        if (this.isInitialized) {
            console.log('OwnLibUI is already initialised');
            return;
        }
        
        console.log('🔧 OwnLibUI is initialised...');
        
        try {
            await this.checkAuth();
            this.setupEventListeners();
            
            if (this.currentUser) {
                await this.loadDashboard();
            }
            
            this.isInitialized = true;
            console.log('✅ OwnLibUI is ready');
        } catch (error) {
            console.error('❌ OwnLibUI initialisation error:', error);
        }
    }

    async checkAuth() {
        try {
            if (this.api.token) {
                this.currentUser = await this.api.getCurrentUser();
                this.updateAuthUI(true);
            } else {
                this.updateAuthUI(false);
            }
        } catch (error) {
            console.error('Auth check failed:', error);
            this.api.clearToken();
            this.updateAuthUI(false);
        }
    }

    updateAuthUI(isAuthenticated) {
        const authElements = document.querySelectorAll('[data-auth-required]');
        const guestElements = document.querySelectorAll('[data-guest-only]');

        authElements.forEach(el => {
            el.style.display = isAuthenticated ? 'block' : 'none';
        });

        guestElements.forEach(el => {
            el.style.display = isAuthenticated ? 'none' : 'block';
        });

        if (isAuthenticated && this.currentUser) {
            const userNameElements = document.querySelectorAll('[data-user-name]');
            userNameElements.forEach(el => {
                el.textContent = this.currentUser.username;
            });
        }
    }

    setupEventListeners() {
        console.log('🔧 OwnLibUI setupEventListeners для не-index сторінок');
        
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.removeEventListener('click', this.handleLogout);
            logoutBtn.addEventListener('click', this.handleLogout.bind(this));
            console.log('🔧 OwnLibUI: logout listener added');
        }

        const uploadForm = document.getElementById('upload-book-form');
        if (uploadForm) {
            uploadForm.removeEventListener('submit', this.handleFileUpload);
            uploadForm.addEventListener('submit', this.handleFileUpload.bind(this));
            console.log('🔧 OwnLibUI: upload form listener додано');
        }

        const searchForm = document.getElementById('search-form');
        if (searchForm) {
            searchForm.removeEventListener('submit', this.handleBookSearch);
            searchForm.addEventListener('submit', this.handleBookSearch.bind(this));
            console.log('🔧 OwnLibUI: search form listener додано');
        }
    }

    handleLogout() {
        console.log('🚪 OwnLibUI handleLogout called');
        this.api.clearToken();
        this.currentUser = null;
        this.updateAuthUI(false);
        this.showMessage('You are logged out', 'info');
        this.clearDashboard();
        
        setTimeout(() => {
            window.location.href = '/static/index.html';
        }, 1000);
    }

    async handleFileUpload(event) {
        event.preventDefault();
        console.log('📤 OwnLibUI handleFileUpload called');
        
        const formData = new FormData(event.target);
        const file = formData.get('file');
        const title = formData.get('title');
        const author = formData.get('author');
        const language = formData.get('language');

        if (!file) {
            this.showMessage('Select a file to upload', 'error');
            return;
        }

        try {
            let validatedLanguage = null;
            if (language) {
                validatedLanguage = OwnLibAPI.validateLanguageCode(language);
            }

            this.showMessage('Uploading a file...', 'info');
            const result = await this.api.uploadBookFile(file, title, author, validatedLanguage);
            this.showMessage('The file was successfully uploaded!', 'success');
            event.target.reset();
            await this.loadUserBooks();
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    async handleBookSearch(event) {
        event.preventDefault();
        console.log('🔍 OwnLibUI handleBookSearch called');
        
        const formData = new FormData(event.target);
        const query = formData.get('query');

        if (!query) {
            this.showMessage('Enter a search query', 'error');
            return;
        }

        try {
            const results = await this.api.searchBooks(query);
            this.displaySearchResults(results);
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    async loadDashboard() {
        if (!this.currentUser) return;
        
        try {
            await this.loadUserBooks();
            await this.loadStats();
        } catch (error) {
            console.error('Error loading dashboard:', error);
        }
    }

    async loadUserBooks() {
        try {
            const books = await this.api.getUserBooks();
            this.displayUserBooks(books);
        } catch (error) {
            console.error('Error loading user books:', error);
        }
    }

    async loadStats() {
        try {
            const stats = await this.api.getReadingStats();
            this.displayStats(stats);
        } catch (error) {
            console.error('Error loading stats:', error);
        }
    }

    displayUserBooks(books) {
        const container = document.getElementById('user-books');
        if (!container) return;

        if (books.length === 0) {
            container.innerHTML = '<p class="text-center">You don\'t have any books in your collection yet</p>';
            return;
        }

        const booksHTML = books.map(userBook => `
            <div class="book-card" data-book-id="${userBook.book.id}">
                <div class="book-cover">
                    ${userBook.book.cover_url ? 
                        `<img src="${userBook.book.cover_url}" alt="${userBook.book.title}" class="book-cover">` :
                        `<div class="book-cover-placeholder">${userBook.book.title.charAt(0)}</div>`
                    }
                </div>
                <div class="book-info">
                    <h3 class="book-title">${userBook.book.title}</h3>
                    <p class="book-author">${userBook.book.author || 'Unknown author'}</p>
                    ${userBook.book.language ? `<p class="book-language">Language: ${userBook.book.language.toUpperCase()}</p>` : ''}
                    <div class="book-status ${userBook.status.toLowerCase().replace(' ', '-')}">${userBook.status}</div>
                    <div class="book-actions">
                        ${this.createBookActionButtons(userBook)}
                    </div>
                    ${userBook.bookmark_position > 0 ? 
                        `<div class="book-progress">
                            <div class="progress-bar">
                                <div class="progress-fill" style="width: ${(userBook.bookmark_position / 300) * 100}%"></div>
                            </div>
                            <small>Page ${userBook.bookmark_position}</small>
                        </div>` : ''
                    }
                </div>
            </div>
        `).join('');

        container.innerHTML = `<div class="book-grid">${booksHTML}</div>`;
    }

    createBookActionButtons(userBook) {
        let buttons = `
            <button class="btn btn-secondary btn-sm" onclick="app.showBookDetails(${userBook.book.id})">
                👁️ Details
            </button>
            <button class="btn btn-danger btn-sm" onclick="app.removeBook(${userBook.book.id})">
                🗑️ Delete
            </button>
        `;

        if (userBook.is_local && userBook.file_path) {
            buttons = `
                <button class="btn btn-primary btn-sm" onclick="app.downloadLocalBook('${userBook.file_path}', '${userBook.book.title}')">
                    📥 Download
                </button>
            ` + buttons;
        }
        else if (userBook.book.gutenberg_id) {
            buttons = `
                <button class="btn btn-primary btn-sm" onclick="app.openGutenbergBook(${userBook.book.gutenberg_id})">
                    🌐 Read online
                </button>
            ` + buttons;
        }

        return buttons;
    }

    displaySearchResults(results) {
        const container = document.getElementById('search-results');
        if (!container) return;

        if (results.results.length === 0) {
            container.innerHTML = '<p class="text-center">Nothing found</p>';
            return;
        }

        const resultsHTML = results.results.map(book => `
            <div class="book-card">
                <div class="book-cover">
                    ${book.formats['image/jpeg'] ? 
                        `<img src="${book.formats['image/jpeg']}" alt="${book.title}" class="book-cover">` :
                        `<div class="book-cover-placeholder">${book.title.charAt(0)}</div>`
                    }
                </div>
                <div class="book-info">
                    <h3 class="book-title">${book.title}</h3>
                    <p class="book-author">${book.authors.map(a => a.name).join(', ') || 'Unknown author'}</p>
                    <p class="book-language">${book.languages.join(', ').toUpperCase()}</p>
                    <div class="book-actions">
                        <button class="btn btn-primary btn-sm" onclick="app.importBook(${book.id})">
                            ➕ Add to collention
                        </button>
                        <button class="btn btn-secondary btn-sm" onclick="window.open('https://www.gutenberg.org/ebooks/${book.id}', '_blank')">
                            🌐 Read on Gutenberg
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        container.innerHTML = `
            <div class="search-meta">
                <p>Found ${results.count} results</p>
            </div>
            <div class="book-grid">${resultsHTML}</div>
        `;
    }

    displayStats(stats) {
        const container = document.getElementById('stats-container');
        if (!container) return;

        container.innerHTML = `
            <div class="stats-grid">
                <div class="stats-card">
                    <div class="stats-value">${stats.total_reading_time}</div>
                    <div class="stats-label">Minutes of reading</div>
                </div>
                <div class="stats-card">
                    <div class="stats-value">${stats.total_pages_read}</div>
                    <div class="stats-label">Pages read</div>
                </div>
                <div class="stats-card">
                    <div class="stats-value">${stats.completed_books}</div>
                    <div class="stats-label">Completed books</div>
                </div>
                <div class="stats-card">
                    <div class="stats-value">${stats.reading_now}</div>
                    <div class="stats-label">Reading now</div>
                </div>
                <div class="stats-card">
                    <div class="stats-value">${stats.want_to_read}</div>
                    <div class="stats-label"> Want to read</div>
                </div>
            </div>
        `;
    }

    clearDashboard() {
        const containers = ['user-books', 'stats-container', 'search-results'];
        containers.forEach(id => {
            const container = document.getElementById(id);
            if (container) container.innerHTML = '';
        });
    }

    downloadLocalBook(filePath, bookTitle) {
        const link = document.createElement('a');
        link.href = `/uploads/${filePath}`;
        link.download = bookTitle;
        link.target = '_blank';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        this.showMessage('Downloading started', 'info');
    }

    openGutenbergBook(gutenbergId) {
        window.open(`https://www.gutenberg.org/ebooks/${gutenbergId}`, '_blank');
    }

    async importBook(gutenbergId) {
        try {
            this.showMessage('Book importing...', 'info');
            const book = await this.api.importGutenbergBook(gutenbergId);
            
            await this.api.addBookToCollection(book.id, {
                book_id: book.id,
                status: 'Want to read',
                is_local: false
            });
            
            this.showMessage('Book successfully added to the collection!', 'success');
            await this.loadUserBooks();
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    async removeBook(bookId) {
        if (!confirm('Are you sure you want to remove this book from the collection?')) {
            return;
        }

        try {
            await this.api.removeBookFromCollection(bookId);
            this.showMessage('Book removed from the collection', 'success');
            await this.loadUserBooks();
        } catch (error) {
            this.showMessage(error.message, 'error');
        }
    }

    async _executeRequest(url, config) {
        try {
            console.log('Making request to:', url);
            const response = await fetch(url, config);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error('API Error Response:', {
                    status: response.status,
                    statusText: response.statusText,
                    url: url,
                    body: errorText
                });
                
                let errorData;
                try {
                    errorData = JSON.parse(errorText);
                } catch (e) {
                    errorData = { detail: errorText };
                }
                
                if (response.status === 503 && errorData.detail && 
                    errorData.detail.includes('free database hosting in Paris')) {
                    throw new Error('🇫🇷 ' + errorData.detail);
                }
                
                throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            if (response.status === 204) {
                return {};
            }
            
            return await response.json();
        } catch (error) {
            console.error('API Request Error:', error);
            throw error;
        }
    }

    showBookDetails(bookId) {
        window.location.href = `/static/book-detail.html?id=${bookId}`;
    }

    showMessage(message, type = 'info') {
        let container = document.getElementById('messages-container');
        if (!container) {
            container = document.createElement('div');
            container.id = 'messages-container';
            container.className = 'messages-container';
            document.body.appendChild(container);
        }

        const messageEl = document.createElement('div');
        messageEl.className = `alert alert-${type}`;
        messageEl.textContent = message;

        container.appendChild(messageEl);

        setTimeout(() => {
            messageEl.remove();
        }, 5000);
    }
}

let app;

function isIndexPage() {
    const path = window.location.pathname;
    return path === '/' || 
           path === '/static/' || 
           path.endsWith('index.html') ||
           path === '/static/index.html';
}

document.addEventListener('DOMContentLoaded', () => {
    console.log('🔍 Checking page:', window.location.pathname);
    
    if (isIndexPage()) {
        console.log('📋 Index page - OwnLibUI isn\'t initializating');
        return;
    }
    
    if (app) {
        console.log('⚠️ OwnLibUI is initializated');
        return;
    }
    
    console.log('🚀 Initialise OwnLibUI for the page:', window.location.pathname);
    app = new OwnLibUI();
    app.init();
    window.app = app;
});

function openBookDetail(bookId) {
    window.location.href = `/static/book-detail.html?id=${bookId}`;
}

window.OwnLibAPI = OwnLibAPI;
window.OwnLibUI = OwnLibUI;