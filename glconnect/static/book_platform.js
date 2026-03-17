/**
 * Ink Studio JavaScript
 * Handles rich text editing, real-time collaboration, and other interactive features
 */

class BookPlatform {
    constructor() {
        this.editor = null;
        this.websocket = null;
        this.isConnected = false;
        this.activeUsers = new Set();
        this.autoSaveInterval = null;
        this.lastSavedContent = '';
        this.currentBookId = null;
        this.currentChapterId = null;
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.initializeRichTextEditor();
        this.setupAutoSave();
        this.setupWebSocket();
    }

    setupEventListeners() {
        // Auto-save on content change
        document.addEventListener('input', (e) => {
            if (e.target.classList.contains('editor-content')) {
                this.scheduleAutoSave();
            }
        });

        // Handle keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch(e.key) {
                    case 's':
                        e.preventDefault();
                        this.saveContent();
                        break;
                    case 'b':
                        e.preventDefault();
                        this.toggleBold();
                        break;
                    case 'i':
                        e.preventDefault();
                        this.toggleItalic();
                        break;
                }
            }
        });

        // Handle window beforeunload
        window.addEventListener('beforeunload', (e) => {
            if (this.hasUnsavedChanges()) {
                e.preventDefault();
                e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
            }
        });
    }

    initializeRichTextEditor() {
        const editorContainer = document.querySelector('.rich-text-editor');
        if (!editorContainer) return;

        const toolbar = editorContainer.querySelector('.editor-toolbar');
        const content = editorContainer.querySelector('.editor-content');

        if (!toolbar || !content) return;

        // Setup toolbar buttons
        this.setupToolbarButtons(toolbar);

        // Make content editable
        content.contentEditable = true;
        content.addEventListener('input', () => {
            this.updateToolbarState();
            this.scheduleAutoSave();
        });

        // Handle paste events
        content.addEventListener('paste', (e) => {
            e.preventDefault();
            const text = (e.clipboardData || window.clipboardData).getData('text/plain');
            document.execCommand('insertText', false, text);
        });

        this.editor = {
            container: editorContainer,
            toolbar: toolbar,
            content: content
        };
    }

    setupToolbarButtons(toolbar) {
        const buttons = [
            { command: 'bold', icon: 'fas fa-bold', title: 'Bold (Ctrl+B)' },
            { command: 'italic', icon: 'fas fa-italic', title: 'Italic (Ctrl+I)' },
            { command: 'underline', icon: 'fas fa-underline', title: 'Underline' },
            { separator: true },
            { command: 'insertUnorderedList', icon: 'fas fa-list-ul', title: 'Bullet List' },
            { command: 'insertOrderedList', icon: 'fas fa-list-ol', title: 'Numbered List' },
            { separator: true },
            { command: 'formatBlock', value: 'h1', icon: 'fas fa-heading', title: 'Heading 1' },
            { command: 'formatBlock', value: 'h2', icon: 'fas fa-heading', title: 'Heading 2' },
            { command: 'formatBlock', value: 'p', icon: 'fas fa-paragraph', title: 'Paragraph' },
            { separator: true },
            { command: 'justifyLeft', icon: 'fas fa-align-left', title: 'Align Left' },
            { command: 'justifyCenter', icon: 'fas fa-align-center', title: 'Align Center' },
            { command: 'justifyRight', icon: 'fas fa-align-right', title: 'Align Right' },
            { separator: true },
            { command: 'undo', icon: 'fas fa-undo', title: 'Undo' },
            { command: 'redo', icon: 'fas fa-redo', title: 'Redo' }
        ];

        buttons.forEach(button => {
            if (button.separator) {
                const separator = document.createElement('div');
                separator.className = 'toolbar-separator';
                separator.innerHTML = '|';
                toolbar.appendChild(separator);
            } else {
                const btn = document.createElement('button');
                btn.innerHTML = `<i class="${button.icon}"></i>`;
                btn.title = button.title;
                btn.addEventListener('click', (e) => {
                    e.preventDefault();
                    if (button.value) {
                        document.execCommand(button.command, false, button.value);
                    } else {
                        document.execCommand(button.command, false, null);
                    }
                    this.updateToolbarState();
                });
                toolbar.appendChild(btn);
            }
        });

        // Add save button
        const saveBtn = document.createElement('button');
        saveBtn.innerHTML = '<i class="fas fa-save"></i>';
        saveBtn.title = 'Save (Ctrl+S)';
        saveBtn.className = 'save-btn';
        saveBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.saveContent();
        });
        toolbar.appendChild(saveBtn);
    }

    updateToolbarState() {
        if (!this.editor) return;

        const buttons = this.editor.toolbar.querySelectorAll('button');
        buttons.forEach(btn => {
            const command = btn.getAttribute('data-command');
            if (command) {
                const isActive = document.queryCommandState(command);
                btn.classList.toggle('active', isActive);
            }
        });
    }

    setupAutoSave() {
        this.autoSaveInterval = setInterval(() => {
            if (this.hasUnsavedChanges()) {
                this.saveContent(true); // Silent save
            }
        }, 30000); // Auto-save every 30 seconds
    }

    scheduleAutoSave() {
        clearTimeout(this.autoSaveTimeout);
        this.autoSaveTimeout = setTimeout(() => {
            if (this.hasUnsavedChanges()) {
                this.saveContent(true); // Silent save
            }
        }, 2000); // Save 2 seconds after last change
    }

    hasUnsavedChanges() {
        if (!this.editor) return false;
        const currentContent = this.editor.content.innerHTML;
        return currentContent !== this.lastSavedContent;
    }

    async saveContent(silent = false) {
        if (!this.editor) return;

        const content = this.editor.content.innerHTML;
        const title = document.querySelector('input[name="title"]')?.value || 
                     document.querySelector('.chapter-title')?.textContent || '';

        try {
            const response = await fetch(window.location.pathname + '/edit', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: content,
                    title: title
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.lastSavedContent = content;
                if (!silent) {
                    this.showNotification('Content saved successfully', 'success');
                }
                
                // Update word count if provided
                if (result.word_count) {
                    const wordCountElement = document.querySelector('.word-count');
                    if (wordCountElement) {
                        wordCountElement.textContent = result.word_count;
                    }
                }
            } else {
                throw new Error(result.error || 'Failed to save content');
            }
        } catch (error) {
            console.error('Save error:', error);
            if (!silent) {
                this.showNotification('Failed to save content', 'error');
            }
        }
    }

    setupWebSocket() {
        // Use Socket.IO client for proper Flask-SocketIO integration
        if (typeof io === 'undefined') {
            console.warn('Socket.IO client not loaded. WebSocket features disabled.');
            return;
        }
        
        try {
            this.websocket = io({
                transports: ['websocket', 'polling'],
                upgrade: true,
                rememberUpgrade: true
            });
            
            this.websocket.on('connect', () => {
                this.isConnected = true;
                this.updateConnectionStatus(true);
                this.joinBookSession();
            });
            
            this.websocket.on('disconnect', () => {
                this.isConnected = false;
                this.updateConnectionStatus(false);
            });
            
            this.websocket.on('user_joined', (data) => {
                this.handleUserJoined(data);
            });
            
            this.websocket.on('user_left', (data) => {
                this.handleUserLeft(data);
            });
            
            this.websocket.on('content_change', (data) => {
                this.handleContentChange(data);
            });
            
            this.websocket.on('cursor_position', (data) => {
                this.handleCursorPosition(data);
            });
            
            this.websocket.on('comment_added', (data) => {
                this.handleCommentAdded(data);
            });
            
            this.websocket.on('comment_resolved', (data) => {
                this.handleCommentResolved(data);
            });
            
            this.websocket.on('error', (error) => {
                console.error('WebSocket error:', error);
                this.updateConnectionStatus(false);
            });
            
        } catch (error) {
            console.error('Failed to setup WebSocket:', error);
        }
    }

    joinBookSession() {
        if (!this.websocket || !this.isConnected) return;

        const bookId = this.getBookIdFromUrl();
        const chapterId = this.getChapterIdFromUrl();
        
        if (bookId) {
            this.websocket.emit('join_book', {
                book_id: bookId,
                chapter_id: chapterId
            });
        }
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'user_joined':
                this.handleUserJoined(data);
                break;
            case 'user_left':
                this.handleUserLeft(data);
                break;
            case 'content_change':
                this.handleContentChange(data);
                break;
            case 'cursor_position':
                this.handleCursorPosition(data);
                break;
            case 'comment_added':
                this.handleCommentAdded(data);
                break;
            case 'comment_resolved':
                this.handleCommentResolved(data);
                break;
        }
    }

    handleUserJoined(data) {
        this.activeUsers.add(data.user);
        this.updateActiveUsersDisplay();
    }

    handleUserLeft(data) {
        this.activeUsers.delete(data.user);
        this.updateActiveUsersDisplay();
    }

    handleContentChange(data) {
        if (data.user_id === this.getCurrentUserId()) return; // Don't apply our own changes
        
        if (this.editor && data.content !== this.editor.content.innerHTML) {
            // Store current cursor position
            const selection = window.getSelection();
            const range = selection.rangeCount > 0 ? selection.getRangeAt(0) : null;
            
            // Apply the change
            this.editor.content.innerHTML = data.content;
            
            // Restore cursor position
            if (range) {
                selection.removeAllRanges();
                selection.addRange(range);
            }
        }
    }

    handleCursorPosition(data) {
        // Show other users' cursors (simplified implementation)
        // In a full implementation, you'd show visual cursors for each user
    }

    handleCommentAdded(data) {
        this.showNotification(`New comment from ${data.user.name}`, 'info');
        // Refresh comments section
        this.loadComments();
    }

    handleCommentResolved(data) {
        this.showNotification(`Comment resolved by ${data.user.name}`, 'success');
        // Refresh comments section
        this.loadComments();
    }

    updateConnectionStatus(connected) {
        const indicator = document.querySelector('.collaboration-indicator');
        if (indicator) {
            indicator.classList.toggle('offline', !connected);
            indicator.textContent = connected ? 'Connected' : 'Disconnected';
        }
    }

    updateActiveUsersDisplay() {
        const container = document.querySelector('.active-users');
        if (!container) return;

        container.innerHTML = '';
        this.activeUsers.forEach(user => {
            const userElement = document.createElement('div');
            userElement.className = 'active-user';
            userElement.innerHTML = `
                <div class="user-avatar">${user.name.charAt(0).toUpperCase()}</div>
                <span>${user.name}</span>
            `;
            container.appendChild(userElement);
        });
    }

    getBookIdFromUrl() {
        const match = window.location.pathname.match(/\/books\/(\d+)/);
        return match ? parseInt(match[1]) : null;
    }

    getChapterIdFromUrl() {
        const match = window.location.pathname.match(/\/chapters\/(\d+)/);
        return match ? parseInt(match[1]) : null;
    }

    getCurrentUserId() {
        // This would be set from the server-side template
        return window.currentUserId || null;
    }

    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; right: 20px; z-index: 1050; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }

    // Comment system
    async addComment(content, startPosition = null, endPosition = null, selectedText = null) {
        const bookId = this.getBookIdFromUrl();
        const chapterId = this.getChapterIdFromUrl();
        
        if (!bookId || !chapterId) return;

        try {
            const response = await fetch(`/mybook/books/${bookId}/chapters/${chapterId}/comments`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    content: content,
                    start_position: startPosition,
                    end_position: endPosition,
                    selected_text: selectedText
                })
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Comment added successfully', 'success');
                this.loadComments();
            } else {
                throw new Error(result.error || 'Failed to add comment');
            }
        } catch (error) {
            console.error('Comment error:', error);
            this.showNotification('Failed to add comment', 'error');
        }
    }

    async loadComments() {
        const bookId = this.getBookIdFromUrl();
        const chapterId = this.getChapterIdFromUrl();
        
        if (!bookId || !chapterId) return;

        try {
            const response = await fetch(`/mybook/api/books/${bookId}/chapters/${chapterId}/comments`);
            const comments = await response.json();
            
            this.renderComments(comments);
        } catch (error) {
            console.error('Failed to load comments:', error);
        }
    }

    renderComments(comments) {
        const container = document.querySelector('.comments-container');
        if (!container) return;

        container.innerHTML = '';
        comments.forEach(comment => {
            const commentElement = document.createElement('div');
            commentElement.className = `comment-item ${comment.is_resolved ? 'comment-resolved' : ''}`;
            commentElement.innerHTML = `
                <div class="comment-header">
                    <span class="comment-author">${comment.commenter.name}</span>
                    <span class="comment-time">${new Date(comment.created_at).toLocaleString()}</span>
                </div>
                <div class="comment-content">${comment.content}</div>
                ${comment.selected_text ? `<div class="comment-selected-text">"${comment.selected_text}"</div>` : ''}
                <div class="comment-actions">
                    ${!comment.is_resolved ? `<button class="btn btn-sm btn-success" onclick="bookPlatform.resolveComment(${comment.id})">Resolve</button>` : ''}
                </div>
            `;
            container.appendChild(commentElement);
        });
    }

    async resolveComment(commentId) {
        try {
            const response = await fetch(`/mybook/comments/${commentId}/resolve`, {
                method: 'POST'
            });

            const result = await response.json();
            
            if (result.success) {
                this.showNotification('Comment resolved', 'success');
                this.loadComments();
            } else {
                throw new Error(result.error || 'Failed to resolve comment');
            }
        } catch (error) {
            console.error('Resolve comment error:', error);
            this.showNotification('Failed to resolve comment', 'error');
        }
    }

    // Utility methods
    toggleBold() {
        document.execCommand('bold', false, null);
        this.updateToolbarState();
    }

    toggleItalic() {
        document.execCommand('italic', false, null);
        this.updateToolbarState();
    }

    // Cleanup
    destroy() {
        if (this.autoSaveInterval) {
            clearInterval(this.autoSaveInterval);
        }
        
        if (this.autoSaveTimeout) {
            clearTimeout(this.autoSaveTimeout);
        }
        
        if (this.websocket) {
            this.websocket.close();
        }
    }
}

// Initialize Ink Studio when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.bookPlatform = new BookPlatform();
});

// Export for use in other scripts
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BookPlatform;
}
