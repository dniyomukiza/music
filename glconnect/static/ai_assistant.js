/**
 * AI Writing Assistant Integration
 * Provides AI-powered writing and editing features for the book platform
 */

class AIWritingAssistant {
    constructor() {
        this.isEnabled = false;
        this.apiKey = null;
        this.currentChapter = null;
        this.aiProvider = 'Gemini'; // Using Google's Gemini AI
        this.chatHistory = [];
        this.chatSending = false;
        this.activeTab = 'writing';
        this.aiFeatures = {
            generateContent: true,
            improveText: true,
            analyzeText: true,
            proofread: true,
            generateIdeas: true,
            suggestImprovements: true,
            chat: true
        };
    }

    /**
     * Initialize AI assistant
     */
    init() {
        this.checkAIStatus();
        this.setupEventListeners();
        this.createAIToolbar();
        console.log('AI Writing Assistant initialized');
    }

    /**
     * Check if AI features are available
     */
    async checkAIStatus() {
        try {
            const response = await fetch('/mybook/ai/status');
            if (response.ok) {
                const data = await response.json();
                this.isEnabled = data.enabled;
                this.apiKey = data.apiKey;
                this.updateAIStatus();
            }
        } catch (error) {
            console.log('AI features not available:', error);
            this.isEnabled = false;
        }
    }

    /**
     * Setup event listeners for AI features
     */
    setupEventListeners() {
        // AI toolbar events
        document.addEventListener('click', (e) => {
            if (e.target.matches('[data-ai-action]')) {
                e.preventDefault();
                this.handleAIAction(e.target.dataset.aiAction);
            }
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'g':
                        e.preventDefault();
                        this.generateContent();
                        break;
                    case 'i':
                        e.preventDefault();
                        this.improveText();
                        break;
                    case 'a':
                        e.preventDefault();
                        this.analyzeText();
                        break;
                    case 'p':
                        e.preventDefault();
                        this.proofread();
                        break;
                }
            }
        });
    }

    /**
     * Create AI toolbar
     */
    createAIToolbar() {
        const toolbar = document.createElement('div');
        toolbar.id = 'ai-toolbar';
        toolbar.className = 'ai-toolbar';
        toolbar.innerHTML = `
            <div class="ai-toolbar-header">
                <h6><i class="fas fa-robot"></i> AI Assistant</h6>
                <div class="ai-status ${this.isEnabled ? 'enabled' : 'disabled'}">
                    ${this.isEnabled ? 'Enabled' : 'Disabled'}
                </div>
            </div>
            <div class="ai-toolbar-tabs" role="tablist">
                <button type="button" class="ai-tab active" data-ai-tab="writing" role="tab" aria-selected="true">Writing</button>
                <button type="button" class="ai-tab" data-ai-tab="chat" role="tab" aria-selected="false">Chat</button>
            </div>
            <div class="ai-toolbar-content">
                <div class="ai-panel-writing" data-ai-panel="writing">
                    <div class="ai-help-text">
                        <small class="text-muted">
                            <i class="fas fa-info-circle"></i>
                            <strong>Developmental</strong> adds or expands prose. <strong>Copy edit</strong> fixes what you already wrote—select text first when noted.
                        </small>
                    </div>
                    <div class="ai-section">
                        <h6>Developmental</h6>
                        <p class="ai-section-hint">Structure, new scenes, and creative expansion.</p>
                        <button type="button" class="ai-action-btn ai-action-btn-primary" data-ai-action="generate-content" title="Write new prose from your prompt">
                            <span class="ai-action-label"><i class="fas fa-magic" aria-hidden="true"></i><span>Generate content</span></span>
                            <span class="ai-action-desc">Draft new paragraphs or scenes from a prompt you enter.</span>
                        </button>
                        <button type="button" class="ai-action-btn ai-action-btn-primary" data-ai-action="generate-ideas" title="Brainstorm story directions">
                            <span class="ai-action-label"><i class="fas fa-lightbulb" aria-hidden="true"></i><span>Story ideas</span></span>
                            <span class="ai-action-desc">Get plot angles, scene ideas, or directions for a theme.</span>
                        </button>
                    </div>
                    <div class="ai-section">
                        <h6>Copyediting &amp; proofreading</h6>
                        <p class="ai-section-hint">Polish existing text. Highlight a passage first when possible.</p>
                        <button type="button" class="ai-action-btn ai-action-btn-success" data-ai-action="improve-text" title="Rewrite selected text for clarity or style">
                            <span class="ai-action-label"><i class="fas fa-edit" aria-hidden="true"></i><span>Improve text</span></span>
                            <span class="ai-action-desc">Rewrite selection for grammar, style, clarity, dialogue, or description.</span>
                        </button>
                        <button type="button" class="ai-action-btn ai-action-btn-success" data-ai-action="proofread" title="Fix spelling and grammar">
                            <span class="ai-action-label"><i class="fas fa-spell-check" aria-hidden="true"></i><span>Proofread</span></span>
                            <span class="ai-action-desc">Correct spelling, punctuation, and grammar (selection or full chapter).</span>
                        </button>
                        <button type="button" class="ai-action-btn ai-action-btn-success" data-ai-action="suggest-improvements" title="List specific edits to consider">
                            <span class="ai-action-label"><i class="fas fa-tools" aria-hidden="true"></i><span>Suggestions</span></span>
                            <span class="ai-action-desc">Get a checklist of targeted edits without auto-rewriting.</span>
                        </button>
                    </div>
                    <div class="ai-section">
                        <h6>Analysis</h6>
                        <p class="ai-section-hint">Understand how the writing reads.</p>
                        <button type="button" class="ai-action-btn ai-action-btn-info" data-ai-action="analyze-text" title="Analyze tone, pacing, and readability">
                            <span class="ai-action-label"><i class="fas fa-chart-line" aria-hidden="true"></i><span>Analyze text</span></span>
                            <span class="ai-action-desc">Report on tone, pacing, readability, and structure (selection or full chapter).</span>
                        </button>
                    </div>
                </div>
                <div class="ai-panel-chat hidden" data-ai-panel="chat" hidden>
                    <p class="ai-chat-intro small text-muted">
                        Ask anything — research, grammar, ideas, or topics unrelated to this book.
                    </p>
                    <div class="ai-chat-messages" id="ai-chat-messages" aria-live="polite"></div>
                    <div class="ai-chat-compose">
                        <textarea id="ai-chat-input" class="form-control form-control-sm" rows="3" placeholder="Type your question…" aria-label="Chat message"></textarea>
                        <div class="ai-chat-actions">
                            <button type="button" class="btn btn-sm btn-outline-secondary" id="ai-chat-clear" title="Clear conversation">Clear</button>
                            <button type="button" class="btn btn-sm btn-primary" id="ai-chat-send">
                                <i class="fas fa-paper-plane"></i> Send
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Add to page
        const editorContainer = document.querySelector('.editor-container') || document.body;
        editorContainer.appendChild(toolbar);

        this.setupToolbarTabs(toolbar);
        this.setupChatPanel(toolbar);

        // Add CSS
        this.addAIStyles();
    }

    /**
     * Add AI-specific styles
     */
    addAIStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .ai-toolbar {
                position: fixed;
                right: 20px;
                top: 50%;
                transform: translateY(-50%);
                width: 320px;
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                z-index: 1000;
                max-height: 85vh;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }

            .ai-toolbar-tabs {
                display: flex;
                gap: 4px;
                padding: 8px 12px 0;
                border-bottom: 1px solid #e2e8f0;
            }

            .ai-tab {
                flex: 1;
                border: none;
                background: #f1f5f9;
                color: #475569;
                font-size: 12px;
                font-weight: 600;
                padding: 8px 10px;
                border-radius: 6px 6px 0 0;
                cursor: pointer;
            }

            .ai-tab.active {
                background: #fff;
                color: #1e293b;
                box-shadow: 0 -1px 0 #fff;
            }

            .ai-toolbar-content {
                flex: 1;
                overflow-y: auto;
                min-height: 0;
            }

            .ai-panel-chat.hidden,
            .ai-panel-writing.hidden {
                display: none !important;
            }

            .ai-chat-intro {
                margin-bottom: 8px;
                line-height: 1.35;
            }

            .ai-chat-messages {
                min-height: 160px;
                max-height: 280px;
                overflow-y: auto;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                padding: 8px;
                margin-bottom: 8px;
                background: #f8fafc;
            }

            .ai-chat-bubble {
                margin-bottom: 10px;
                padding: 8px 10px;
                border-radius: 10px;
                font-size: 12px;
                line-height: 1.45;
                white-space: pre-wrap;
                word-break: break-word;
            }

            .ai-chat-bubble.user {
                background: #e0f2fe;
                color: #0c4a6e;
                margin-left: 12px;
            }

            .ai-chat-bubble.assistant {
                background: #fff;
                border: 1px solid #e2e8f0;
                color: #334155;
                margin-right: 8px;
            }

            .ai-chat-bubble.error {
                background: #fee2e2;
                color: #991b1b;
            }

            .ai-chat-bubble.thinking {
                color: #64748b;
                font-style: italic;
            }

            .ai-chat-compose textarea {
                resize: vertical;
                min-height: 56px;
                font-size: 13px;
            }

            .ai-chat-actions {
                display: flex;
                justify-content: space-between;
                gap: 8px;
                margin-top: 8px;
            }

            .ai-chat-actions .btn-primary {
                flex: 1;
            }
            
            .ai-toolbar-header {
                padding: 12px;
                border-bottom: 1px solid #e2e8f0;
                display: flex;
                justify-content: space-between;
                align-items: center;
            }
            
            .ai-toolbar-header h6 {
                margin: 0;
                color: #2c3e50;
            }
            
            .ai-status {
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            
            .ai-status.enabled {
                background: #d4edda;
                color: #155724;
            }
            
            .ai-status.disabled {
                background: #f8d7da;
                color: #721c24;
            }
            
            .ai-toolbar-content {
                padding: 12px;
                color: #333;
            }

            .ai-help-text {
                margin-bottom: 12px;
                padding: 8px;
                background: #f8f9fa;
                border-radius: 4px;
                border-left: 3px solid #2c3e50;
            }
            
            .ai-help-text small,
            .ai-help-text .text-muted {
                color: #333 !important;
            }
            
            .ai-section {
                margin-bottom: 16px;
            }

            .ai-section-hint {
                font-size: 11px;
                line-height: 1.35;
                color: #64748b !important;
                margin: -4px 0 8px;
            }
            
            .ai-section h6 {
                margin-bottom: 4px;
                color: #2c3e50;
                font-size: 12px;
                text-transform: uppercase;
                font-weight: 600;
                letter-spacing: 0.04em;
            }

            .ai-action-btn {
                display: block;
                width: 100%;
                margin-bottom: 8px;
                padding: 10px 12px;
                text-align: left;
                border-radius: 8px;
                border: 1px solid #cbd5e1;
                background: #fff;
                cursor: pointer;
                transition: background 0.15s ease, border-color 0.15s ease, box-shadow 0.15s ease;
            }

            .ai-action-btn:last-child {
                margin-bottom: 0;
            }

            .ai-action-btn:hover {
                background: #f8fafc;
                box-shadow: 0 1px 4px rgba(15, 23, 42, 0.08);
            }

            .ai-action-btn:focus-visible {
                outline: 2px solid #2563eb;
                outline-offset: 2px;
            }

            .ai-action-label {
                display: flex;
                align-items: center;
                gap: 8px;
                font-size: 13px;
                font-weight: 700;
                color: #0f172a !important;
                margin-bottom: 4px;
            }

            .ai-action-label i {
                width: 1.1rem;
                text-align: center;
                flex-shrink: 0;
            }

            .ai-action-desc {
                display: block;
                font-size: 11px;
                line-height: 1.4;
                color: #475569 !important;
                padding-left: 1.55rem;
            }

            .ai-action-btn-primary {
                border-color: #93c5fd;
            }

            .ai-action-btn-primary .ai-action-label i {
                color: #2563eb;
            }

            .ai-action-btn-success {
                border-color: #86efac;
            }

            .ai-action-btn-success .ai-action-label i {
                color: #16a34a;
            }

            .ai-action-btn-info {
                border-color: #7dd3fc;
            }

            .ai-action-btn-info .ai-action-label i {
                color: #0284c7;
            }
            
            .ai-section button.ai-action-btn {
                width: 100%;
                margin-bottom: 8px;
                font-size: inherit;
            }
            
            /* Ensure all text in AI toolbar is visible */
            .ai-toolbar,
            .ai-toolbar * {
                color: #333;
            }
            
            .ai-toolbar-header h6,
            .ai-section h6,
            .ai-help-text,
            .ai-help-text small {
                color: #2c3e50 !important;
            }
            
            .ai-chat-actions .btn {
                border: 1px solid #ced4da !important;
                background-color: #ffffff;
                border-radius: 6px;
            }

            .ai-chat-actions .btn-primary {
                background-color: #0d6efd;
                border-color: #0d6efd !important;
                color: #fff !important;
            }
            
            /* Modal text visibility */
            .ai-modal-content,
            .ai-modal-content * {
                color: #333;
            }
            
            .ai-modal-content h5 {
                color: #2c3e50 !important;
            }
            
            .ai-modal-content .btn {
                color: white;
            }
            
            .ai-modal-content .btn-secondary {
                background-color: #6c757d;
                color: white;
            }
            
            /* Ensure form controls are visible */
            .ai-modal-content .form-control,
            .ai-modal-content input,
            .ai-modal-content textarea,
            .ai-modal-content select {
                color: #333 !important;
                background-color: white !important;
            }
            
            .ai-modal-content .form-control::placeholder {
                color: #6c757d !important;
            }
            
            /* Ensure all text elements in AI modals are visible */
            .ai-modal-content label {
                color: #333 !important;
            }
            
            /* Global override for any white text on white background in AI components */
            .ai-toolbar .text-white,
            .ai-toolbar .text-light,
            .ai-modal-content .text-white,
            .ai-modal-content .text-light {
                color: #333 !important;
            }
            
            /* Ensure icons are visible but not overriding button colors */
            .ai-toolbar .fas,
            .ai-toolbar .fa,
            .ai-modal-content .fas,
            .ai-modal-content .fa {
                color: inherit;
            }
            
            /* Make sure any inherited text colors work (excluding buttons which have their own colors) */
            .ai-toolbar h6,
            .ai-toolbar p,
            .ai-toolbar span:not(.ai-status),
            .ai-toolbar div:not(.btn):not(button):not(.ai-status) {
                color: #333 !important;
            }
            
            /* Keep status colors as defined */
            .ai-toolbar .ai-status.enabled {
                color: #155724 !important;
            }
            
            .ai-toolbar .ai-status.disabled {
                color: #721c24 !important;
            }
            
            .ai-modal {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0,0,0,0.5);
                z-index: 2000;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .ai-modal-content {
                background: white;
                border-radius: 8px;
                padding: 24px;
                max-width: 600px;
                max-height: 80vh;
                overflow-y: auto;
                position: relative;
                color: #333;
            }
            
            .ai-modal-content h5 {
                color: #2c3e50;
                font-weight: 600;
                margin-bottom: 16px;
            }
            
            .ai-modal-close {
                position: absolute;
                top: 12px;
                right: 12px;
                background: none;
                border: none;
                font-size: 24px;
                cursor: pointer;
                color: #333;
                opacity: 0.7;
            }
            
            .ai-modal-close:hover {
                opacity: 1;
                color: #000;
            }
            
            .ai-loading {
                text-align: center;
                padding: 20px;
                color: #333;
            }
            
            .ai-loading p {
                color: #333;
                margin-top: 12px;
            }
            
            .ai-result {
                margin-top: 16px;
                padding: 16px;
                background: #f8f9fa;
                border-radius: 4px;
                border-left: 4px solid #2c3e50;
                color: #333;
            }
            
            .ai-result pre {
                color: #333;
                margin: 0;
                white-space: pre-wrap;
                font-family: inherit;
            }
            
            .ai-error {
                border-left-color: #e74c3c;
                background: #f8d7da;
                color: #721c24;
            }
            
            .ai-success {
                border-left-color: #27ae60;
                background: #d4edda;
                color: #155724;
            }
        `;
        document.head.appendChild(style);
    }

    setupToolbarTabs(toolbar) {
        const tabs = toolbar.querySelectorAll('[data-ai-tab]');
        tabs.forEach((tab) => {
            tab.addEventListener('click', () => {
                const name = tab.getAttribute('data-ai-tab');
                this.switchAITab(name, toolbar);
            });
        });
    }

    switchAITab(name, toolbar) {
        if (!toolbar) toolbar = document.getElementById('ai-toolbar');
        if (!toolbar) return;
        this.activeTab = name;
        toolbar.querySelectorAll('[data-ai-tab]').forEach((t) => {
            const active = t.getAttribute('data-ai-tab') === name;
            t.classList.toggle('active', active);
            t.setAttribute('aria-selected', active ? 'true' : 'false');
        });
        toolbar.querySelectorAll('[data-ai-panel]').forEach((panel) => {
            const show = panel.getAttribute('data-ai-panel') === name;
            panel.classList.toggle('hidden', !show);
            panel.hidden = !show;
        });
    }

    setupChatPanel(toolbar) {
        const sendBtn = toolbar.querySelector('#ai-chat-send');
        const clearBtn = toolbar.querySelector('#ai-chat-clear');
        const input = toolbar.querySelector('#ai-chat-input');
        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendChatMessage());
        }
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearChat());
        }
        if (input) {
            input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendChatMessage();
                }
            });
        }
        this.renderChatMessages();
    }

    renderChatMessages() {
        const container = document.getElementById('ai-chat-messages');
        if (!container) return;
        if (!this.chatHistory.length) {
            container.innerHTML = '<div class="ai-chat-bubble assistant">Hi — ask me anything. I can help with writing, research, or general questions, not just this chapter.</div>';
            return;
        }
        container.innerHTML = this.chatHistory.map((m) => {
            const role = m.role === 'user' ? 'user' : 'assistant';
            const safe = this.escapeHtml(m.content);
            return `<div class="ai-chat-bubble ${role}">${safe}</div>`;
        }).join('');
        container.scrollTop = container.scrollHeight;
    }

    escapeHtml(text) {
        const d = document.createElement('div');
        d.textContent = text || '';
        return d.innerHTML;
    }

    appendChatBubble(role, content, extraClass = '') {
        const container = document.getElementById('ai-chat-messages');
        if (!container) return;
        if (!this.chatHistory.length && role !== 'user') {
            container.innerHTML = '';
        }
        const div = document.createElement('div');
        div.className = `ai-chat-bubble ${role} ${extraClass}`.trim();
        div.textContent = content;
        container.appendChild(div);
        container.scrollTop = container.scrollHeight;
    }

    clearChat() {
        this.chatHistory = [];
        this.renderChatMessages();
        const input = document.getElementById('ai-chat-input');
        if (input) input.value = '';
    }

    async sendChatMessage() {
        if (!this.isEnabled) {
            this.showNotification('AI features are not enabled', 'error');
            return;
        }
        if (this.chatSending) return;
        const input = document.getElementById('ai-chat-input');
        const message = input ? input.value.trim() : '';
        if (!message) {
            this.showNotification('Enter a message to send', 'warning');
            return;
        }

        this.chatSending = true;
        const sendBtn = document.getElementById('ai-chat-send');
        if (sendBtn) sendBtn.disabled = true;
        if (input) input.value = '';

        this.chatHistory.push({ role: 'user', content: message });
        this.renderChatMessages();
        this.appendChatBubble('assistant', 'Thinking…', 'thinking');

        try {
            const response = await fetch('/mybook/ai/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                credentials: 'same-origin',
                body: JSON.stringify({
                    message,
                    history: this.chatHistory.slice(0, -1),
                }),
            });

            const container = document.getElementById('ai-chat-messages');
            const thinking = container ? container.querySelector('.thinking') : null;
            if (thinking) thinking.remove();

            const result = await this.handleAIResponse(response, 'Chat error');
            if (!result) return;

            if (result.success && result.content) {
                this.chatHistory.push({ role: 'assistant', content: result.content });
                this.renderChatMessages();
            } else {
                this.appendChatBubble('assistant', result.error || 'Could not get a reply.', 'error');
            }
        } catch (error) {
            const container = document.getElementById('ai-chat-messages');
            const thinking = container ? container.querySelector('.thinking') : null;
            if (thinking) thinking.remove();
            this.appendChatBubble('assistant', error.message || 'Request failed.', 'error');
        } finally {
            this.chatSending = false;
            if (sendBtn) sendBtn.disabled = false;
            if (input) input.focus();
        }
    }

    /**
     * Handle AI action
     */
    async handleAIAction(action) {
        if (!this.isEnabled) {
            this.showNotification('AI features are not enabled', 'error');
            return;
        }

        switch (action) {
            case 'generate-content':
                await this.generateContent();
                break;
            case 'improve-text':
                await this.improveText();
                break;
            case 'analyze-text':
                await this.analyzeText();
                break;
            case 'proofread':
                await this.proofread();
                break;
            case 'generate-ideas':
                await this.generateIdeas();
                break;
            case 'suggest-improvements':
                await this.suggestImprovements();
                break;
        }
    }

    /**
     * Generate content
     */
    async generateContent() {
        const prompt = await this.getUserInput('Enter a prompt for content generation:', 'text');
        if (!prompt) return;

        this.showAIModal('Generating Content...', 'loading');
        
        try {
            const response = await fetch('/mybook/ai/generate-content', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });
            
            const result = await response.json();
            this.showAIResult(result, 'Generated Content');
        } catch (error) {
            this.showAIResult({ success: false, error: error.message }, 'Error');
        }
    }

    /**
     * Improve text
     */
    async improveText() {
        const text = this.getSelectedText();
        if (!text) {
            this.showNotification('Please select text to improve', 'warning');
            return;
        }

        const improvementType = await this.getUserInput(
            'Select improvement type:',
            'select',
            ['general', 'grammar', 'style', 'clarity', 'dialogue', 'description']
        );
        
        this.showAIModal('Improving Text...', 'loading');
        
        try {
            const response = await fetch('/mybook/ai/improve-text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text, type: improvementType })
            });
            
            const result = await this.handleAIResponse(response);
            if (result) {
                this.showAIResult(result, 'Improved Text');
            }
        } catch (error) {
            this.showAIResult({ success: false, error: error.message }, 'Error');
        }
    }

    /**
     * Analyze text
     */
    async analyzeText() {
        const text = this.getSelectedText() || this.getCurrentText();
        if (!text) {
            this.showNotification('No text to analyze', 'warning');
            return;
        }

        this.showAIModal('Analyzing Text...', 'loading');
        
        try {
            const response = await fetch('/mybook/ai/analyze-text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            
            // Check if response is HTML (redirect to login)
            const contentType = response.headers.get('content-type');
            if (contentType && contentType.includes('text/html')) {
                this.showAIResult({ 
                    success: false, 
                    error: 'Session expired. Please refresh the page and try again.' 
                }, 'Authentication Error');
                return;
            }
            
            // Check if response is OK
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            this.showAIResult(result, 'Text Analysis');
        } catch (error) {
            this.showAIResult({ success: false, error: error.message }, 'Error');
        }
    }

    /**
     * Proofread text
     */
    async proofread() {
        const text = this.getSelectedText() || this.getCurrentText();
        if (!text) {
            this.showNotification('No text to proofread', 'warning');
            return;
        }

        this.showAIModal('Proofreading...', 'loading');
        
        try {
            const response = await fetch('/mybook/ai/proofread', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            
            const result = await response.json();
            this.showAIResult(result, 'Proofreading Results');
        } catch (error) {
            this.showAIResult({ success: false, error: error.message }, 'Error');
        }
    }

    /**
     * Generate story ideas
     */
    async generateIdeas() {
        const theme = await this.getUserInput('Enter theme for story ideas:', 'text');
        if (!theme) return;

        this.showAIModal('Generating Ideas...', 'loading');
        
        try {
            const response = await fetch('/mybook/ai/generate-ideas', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ theme })
            });
            
            const result = await response.json();
            this.showAIResult(result, 'Story Ideas');
        } catch (error) {
            this.showAIResult({ success: false, error: error.message }, 'Error');
        }
    }

    /**
     * Suggest improvements
     */
    async suggestImprovements() {
        const text = this.getSelectedText() || this.getCurrentText();
        if (!text) {
            this.showNotification('No text to analyze', 'warning');
            return;
        }

        this.showAIModal('Analyzing for Improvements...', 'loading');
        
        try {
            const response = await fetch('/mybook/ai/suggest-improvements', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text })
            });
            
            const result = await response.json();
            this.showAIResult(result, 'Improvement Suggestions');
        } catch (error) {
            this.showAIResult({ success: false, error: error.message }, 'Error');
        }
    }

    /**
     * Check if response is an authentication redirect
     */
    checkAuthentication(response) {
        // Check for 302 redirect (authentication required)
        if (response.status === 302) {
            return {
                isAuthError: true,
                error: 'Session expired. Please refresh the page and try again.'
            };
        }
        
        const contentType = response.headers.get('content-type');
        if (contentType && contentType.includes('text/html')) {
            return {
                isAuthError: true,
                error: 'Session expired. Please refresh the page and try again.'
            };
        }
        return { isAuthError: false };
    }

    /**
     * Handle AI API response
     */
    async handleAIResponse(response, errorTitle = 'Error') {
        const authCheck = this.checkAuthentication(response);
        if (authCheck.isAuthError) {
            this.showAIResult({ 
                success: false, 
                error: authCheck.error 
            }, 'Authentication Error');
            return null;
        }
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        return await response.json();
    }

    /**
     * Get current text from editor
     */
    getCurrentText() {
        // Try CKEditor first
        if (window.editor && window.editor.getData) {
            return window.editor.getData();
        }
        
        // Try different editor types
        const editor = document.querySelector('#editor') || 
                      document.querySelector('.ck-editor__editable') ||
                      document.querySelector('[contenteditable="true"]');
        
        if (editor) {
            return editor.innerText || editor.textContent || '';
        }
        
        return '';
    }

    /**
     * Get selected text from editor
     */
    getSelectedText() {
        // Try CKEditor first
        if (window.editor && window.editor.model && window.editor.model.document) {
            const selection = window.editor.model.document.selection;
            if (selection.getSelectedText) {
                return selection.getSelectedText();
            }
        }
        
        // Fallback to standard selection
        const selection = window.getSelection();
        return selection.toString();
    }

    /**
     * Get user input
     */
    async getUserInput(message, type = 'text', options = null) {
        return new Promise((resolve) => {
            const modal = document.createElement('div');
            modal.className = 'ai-modal';
            modal.innerHTML = `
                <div class="ai-modal-content">
                    <button class="ai-modal-close">&times;</button>
                    <h5>${message}</h5>
                    ${this.createInputField(type, options)}
                    <div style="margin-top: 16px;">
                        <button class="btn btn-primary" id="ai-confirm">Confirm</button>
                        <button class="btn btn-secondary" id="ai-cancel">Cancel</button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(modal);
            
            const confirmBtn = modal.querySelector('#ai-confirm');
            const cancelBtn = modal.querySelector('#ai-cancel');
            const closeBtn = modal.querySelector('.ai-modal-close');
            const input = modal.querySelector('input, textarea, select');
            
            const cleanup = () => {
                document.body.removeChild(modal);
            };
            
            confirmBtn.onclick = () => {
                const value = input ? input.value : '';
                cleanup();
                resolve(value);
            };
            
            cancelBtn.onclick = () => {
                cleanup();
                resolve(null);
            };
            
            closeBtn.onclick = () => {
                cleanup();
                resolve(null);
            };
            
            if (input) {
                input.focus();
                input.onkeydown = (e) => {
                    if (e.key === 'Enter' && type !== 'textarea') {
                        confirmBtn.click();
                    } else if (e.key === 'Escape') {
                        cancelBtn.click();
                    }
                };
            }
        });
    }

    /**
     * Create input field
     */
    createInputField(type, options) {
        switch (type) {
            case 'textarea':
                return '<textarea class="form-control" rows="4" placeholder="Enter text..."></textarea>';
            case 'number':
                return `<input type="number" class="form-control" value="${options || ''}" placeholder="Enter number...">`;
            case 'select':
                if (Array.isArray(options)) {
                    const optionsHtml = options.map(opt => 
                        `<option value="${opt}">${opt}</option>`
                    ).join('');
                    return `<select class="form-control">${optionsHtml}</select>`;
                }
                return '<select class="form-control"></select>';
            default:
                return '<input type="text" class="form-control" placeholder="Enter text...">';
        }
    }

    /**
     * Show AI modal
     */
    showAIModal(title, type = 'loading') {
        const modal = document.createElement('div');
        modal.className = 'ai-modal';
        
        let content = '';
        if (type === 'loading') {
            content = `
                <div class="ai-loading">
                    <div class="spinner-border text-primary" role="status">
                        <span class="visually-hidden">Loading...</span>
                    </div>
                    <p>${title}</p>
                </div>
            `;
        }
        
        modal.innerHTML = `
            <div class="ai-modal-content">
                <button class="ai-modal-close">&times;</button>
                ${content}
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const closeBtn = modal.querySelector('.ai-modal-close');
        closeBtn.onclick = () => {
            document.body.removeChild(modal);
        };
        
        return modal;
    }

    /**
     * Show AI result
     */
    showAIResult(result, title) {
        // Close any existing modals
        const existingModals = document.querySelectorAll('.ai-modal');
        existingModals.forEach(modal => modal.remove());
        
        const modal = document.createElement('div');
        modal.className = 'ai-modal';
        
        const resultClass = result.success ? 'ai-success' : 'ai-error';
        const rawContent = result.success ? 
            (result.content || result.ai_analysis || JSON.stringify(result, null, 2)) : 
            result.error;
        
        // Clean the content for display (remove asterisks and formatting symbols)
        const cleanedContent = this.cleanAIText(rawContent);
        
        modal.innerHTML = `
            <div class="ai-modal-content">
                <button class="ai-modal-close">&times;</button>
                <h5>${title}</h5>
                <div class="ai-result ${resultClass}">
                    <pre style="white-space: pre-wrap; font-family: inherit;">${cleanedContent}</pre>
                </div>
                ${result.success ? `
                    <div style="margin-top: 16px;">
                        <button class="btn btn-primary" id="ai-use-result">Use This</button>
                        <button class="btn btn-secondary" id="ai-copy-result">Copy</button>
                    </div>
                ` : ''}
            </div>
        `;
        
        document.body.appendChild(modal);
        
        const closeBtn = modal.querySelector('.ai-modal-close');
        const useBtn = modal.querySelector('#ai-use-result');
        const copyBtn = modal.querySelector('#ai-copy-result');
        
        closeBtn.onclick = () => {
            document.body.removeChild(modal);
        };
        
        if (useBtn) {
            useBtn.onclick = () => {
                // Store the original text for undo functionality
                const selectedText = this.getSelectedText();
                if (selectedText && selectedText.trim()) {
                    // Store original text for undo
                    this.lastReplacedText = selectedText;
                    this.lastReplacementPosition = this.getSelectionRange();
                    
                    // Replace selected text with cleaned content
                    this.replaceSelectedText(cleanedContent);
                    
                    // Show undo option
                    this.showUndoOption();
                } else {
                    this.insertText(cleanedContent);
                }
                document.body.removeChild(modal);
            };
        }
        
        if (copyBtn) {
            copyBtn.onclick = () => {
                navigator.clipboard.writeText(cleanedContent);
                this.showNotification('Copied to clipboard', 'success');
            };
        }
    }

    /**
     * Clean AI text by removing asterisks and formatting symbols
     */
    cleanAIText(text) {
        if (!text) return text;
        
        return text
            // Remove markdown bold (**text**)
            .replace(/\*\*(.*?)\*\*/g, '$1')
            // Remove markdown italic (*text*)
            .replace(/\*(.*?)\*/g, '$1')
            // Remove markdown headers (# Header)
            .replace(/^#+\s*/gm, '')
            // Remove bullet points (- item)
            .replace(/^[-•]\s*/gm, '')
            // Remove numbered lists (1. item)
            .replace(/^\d+\.\s*/gm, '')
            // Remove extra whitespace
            .replace(/\n\s*\n/g, '\n\n')
            .trim();
    }

    /**
     * Get current selection range for undo functionality
     */
    getSelectionRange() {
        if (window.editor && window.editor.model) {
            const selection = window.editor.model.document.selection;
            return {
                start: selection.getFirstPosition(),
                end: selection.getLastPosition(),
                isCKEditor: true
            };
        }
        
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            return {
                startContainer: range.startContainer,
                startOffset: range.startOffset,
                endContainer: range.endContainer,
                endOffset: range.endOffset,
                isCKEditor: false
            };
        }
        
        return null;
    }

    /**
     * Show undo option after text replacement
     */
    showUndoOption() {
        // Remove any existing undo notification
        const existingUndo = document.querySelector('.ai-undo-notification');
        if (existingUndo) {
            existingUndo.remove();
        }
        
        const undoNotification = document.createElement('div');
        undoNotification.className = 'ai-undo-notification';
        undoNotification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: #27ae60;
            color: white;
            padding: 12px 16px;
            border-radius: 4px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.2);
            z-index: 3000;
            font-size: 14px;
            cursor: pointer;
            transition: opacity 0.3s ease;
        `;
        
        undoNotification.innerHTML = `
            <div style="display: flex; align-items: center; gap: 8px;">
                <span>✓ Text replaced</span>
                <button style="background: rgba(255,255,255,0.2); border: none; color: white; padding: 4px 8px; border-radius: 3px; cursor: pointer;">
                    Undo
                </button>
                <button style="background: rgba(255,255,255,0.2); border: none; color: white; padding: 4px 8px; border-radius: 3px; cursor: pointer; margin-left: 4px;">
                    ×
                </button>
            </div>
        `;
        
        document.body.appendChild(undoNotification);
        
        // Add click handlers
        const undoBtn = undoNotification.querySelector('button');
        const closeBtn = undoNotification.querySelectorAll('button')[1];
        
        undoBtn.onclick = () => {
            this.undoLastReplacement();
            undoNotification.remove();
        };
        
        closeBtn.onclick = () => {
            undoNotification.remove();
        };
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (undoNotification.parentNode) {
                undoNotification.remove();
            }
        }, 5000);
    }

    /**
     * Undo the last text replacement
     */
    undoLastReplacement() {
        if (!this.lastReplacedText || !this.lastReplacementPosition) {
            this.showNotification('Nothing to undo', 'warning');
            return;
        }
        
        try {
            if (this.lastReplacementPosition.isCKEditor && window.editor) {
                const model = window.editor.model;
                const position = this.lastReplacementPosition.start;
                
                model.change(writer => {
                    // Find the range of the replaced text
                    const range = writer.createRange(position, position);
                    // Replace with original text
                    writer.insertText(this.lastReplacedText, position);
                });
                
                // Update the hidden textarea
                const textarea = document.getElementById('content');
                if (textarea) {
                    textarea.value = window.editor.getData();
                }
            } else {
                // Fallback for non-CKEditor
                const selection = window.getSelection();
                if (selection.rangeCount > 0) {
                    const range = selection.getRangeAt(0);
                    range.deleteContents();
                    range.insertNode(document.createTextNode(this.lastReplacedText));
                }
            }
            
            this.showNotification('Text restored', 'success');
            
            // Clear undo data
            this.lastReplacedText = null;
            this.lastReplacementPosition = null;
            
        } catch (error) {
            console.error('Error undoing replacement:', error);
            this.showNotification('Failed to undo', 'error');
        }
    }

    /**
     * Insert text into editor
     */
    insertText(text) {
        // Try CKEditor first
        if (window.editor && window.editor.model) {
            const model = window.editor.model;
            const selection = model.document.selection;
            
            // Insert at current position
            model.change(writer => {
                const insertPosition = selection.getFirstPosition();
                writer.insertText(text, insertPosition);
            });
            
            // Update the hidden textarea
            const textarea = document.getElementById('content');
            if (textarea) {
                textarea.value = window.editor.getData();
            }
            
            return;
        }
        
        // Fallback to standard editor
        const editor = document.querySelector('#editor') || 
                      document.querySelector('.ck-editor__editable') ||
                      document.querySelector('[contenteditable="true"]');
        
        if (editor) {
            const selection = window.getSelection();
            if (selection.rangeCount > 0) {
                const range = selection.getRangeAt(0);
                range.deleteContents();
                range.insertNode(document.createTextNode(text));
                range.collapse(false);
                selection.removeAllRanges();
                selection.addRange(range);
            } else {
                editor.innerHTML += text;
            }
            
            // Trigger change event
            editor.dispatchEvent(new Event('input', { bubbles: true }));
        }
    }

    /**
     * Replace selected text in editor
     */
    replaceSelectedText(text) {
        // Try CKEditor first
        if (window.editor && window.editor.model) {
            const model = window.editor.model;
            const selection = model.document.selection;
            
            model.change(writer => {
                // Delete selected content
                if (selection.getSelectedText()) {
                    writer.delete(selection.getFirstRange());
                }
                // Insert new text
                const insertPosition = selection.getFirstPosition();
                writer.insertText(text, insertPosition);
            });
            
            // Update the hidden textarea
            const textarea = document.getElementById('content');
            if (textarea) {
                textarea.value = window.editor.getData();
            }
            
            return;
        }
        
        // Fallback to standard editor
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            const range = selection.getRangeAt(0);
            range.deleteContents();
            range.insertNode(document.createTextNode(text));
            range.collapse(false);
            selection.removeAllRanges();
            selection.addRange(range);
        }
    }

    /**
     * Update AI status
     */
    updateAIStatus() {
        const statusElement = document.querySelector('.ai-status');
        if (statusElement) {
            statusElement.textContent = this.isEnabled ? 'Enabled' : 'Disabled';
            statusElement.className = `ai-status ${this.isEnabled ? 'enabled' : 'disabled'}`;
        }
    }

    /**
     * Show notification
     */
    showNotification(message, type = 'info') {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        notification.style.cssText = 'top: 20px; left: 50%; transform: translateX(-50%); z-index: 9999; min-width: 300px;';
        notification.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            if (notification.parentNode) {
                notification.parentNode.removeChild(notification);
            }
        }, 5000);
    }
}

// Initialize AI assistant when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (window.location.pathname.includes('/mybook/')) {
        window.aiAssistant = new AIWritingAssistant();
        window.aiAssistant.init();
    }
});
