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
        this._capturedSelectionText = '';
        this._dragState = null;
        this._positionStorageKey = 'inkStudioAiToolbarPosition';
        this.aiFeatures = {
            generateContent: true,
            authorReview: true,
            generateIdeas: true,
            chat: true
        };
        this.authorReviewCategories = {
            'grammar-punctuation': {
                category: 'grammar_punctuation',
                title: 'Grammar & punctuation',
                hint: 'Fixes grammar and punctuation while keeping your voice.',
                icon: 'fa-check-double',
                btnClass: 'ai-action-btn-success',
                needsSelection: true
            },
            'spelling': {
                category: 'spelling',
                title: 'Spelling',
                hint: 'Corrects misspellings and typos only.',
                icon: 'fa-spell-check',
                btnClass: 'ai-action-btn-success',
                needsSelection: true
            },
            'linguistic-errors': {
                category: 'linguistic_errors',
                title: 'Linguistic errors',
                hint: 'Flags wrong word usage, tense shifts, agreement, and similar issues.',
                icon: 'fa-language',
                btnClass: 'ai-action-btn-success',
                needsSelection: true
            },
            'plot-continuity': {
                category: 'plot_continuity',
                title: 'Plot continuity',
                hint: 'Checks timeline, character facts, and story consistency.',
                icon: 'fa-project-diagram',
                btnClass: 'ai-action-btn-info',
                needsSelection: false
            },
            'pacing-tension': {
                category: 'pacing_tension',
                title: 'Pacing & tension',
                hint: 'Reviews scene rhythm, stakes, hooks, and tension.',
                icon: 'fa-heartbeat',
                btnClass: 'ai-action-btn-info',
                needsSelection: false
            },
            'narrative-style': {
                category: 'narrative_style',
                title: 'Narrative style',
                hint: 'Assesses voice, POV, tone, and show vs tell balance.',
                icon: 'fa-feather-alt',
                btnClass: 'ai-action-btn-info',
                needsSelection: false
            }
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
        // Keep editor selection when clicking toolbar buttons (before focus leaves the editor)
        document.addEventListener('mousedown', (e) => {
            const actionBtn = e.target.closest('[data-ai-action]');
            if (!actionBtn) return;
            this._capturedSelectionText = this.getSelectedText();
            e.preventDefault();
        }, true);

        // AI toolbar events (use closest — clicks often land on icons/spans inside the button)
        document.addEventListener('click', (e) => {
            const actionBtn = e.target.closest('[data-ai-action]');
            if (!actionBtn) return;
            e.preventDefault();
            this.handleAIAction(actionBtn.dataset.aiAction);
        });

        // Keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.ctrlKey || e.metaKey) {
                switch (e.key) {
                    case 'g':
                        e.preventDefault();
                        this.generateContent();
                        break;
                    case 'p':
                        e.preventDefault();
                        this.authorReview('grammar-punctuation');
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
            <div class="ai-toolbar-header ai-toolbar-drag-handle" title="Drag to move horizontally or vertically">
                <div class="ai-toolbar-drag-title">
                    <h6><i class="fas fa-grip-vertical ai-drag-grip" aria-hidden="true"></i><i class="fas fa-robot"></i> AI Assistant</h6>
                    <span class="ai-toolbar-drag-hint">Drag header to move</span>
                </div>
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
                            <strong>Developmental</strong> adds or expands prose. <strong>Author editing</strong> polishes or reviews what you wrote, highlight a passage first when you want targeted feedback.
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
                        <h6>Author editing</h6>
                        <p class="ai-section-hint">Copy edits and craft review. Highlight a passage first for grammar, spelling, and linguistic checks.</p>
                        <button type="button" class="ai-action-btn ai-action-btn-success" data-ai-action="grammar-punctuation" title="Fix grammar and punctuation">
                            <span class="ai-action-label"><i class="fas fa-check-double" aria-hidden="true"></i><span>Grammar &amp; punctuation</span></span>
                            <span class="ai-action-desc">Correct grammar and punctuation; keeps your wording and voice.</span>
                        </button>
                        <button type="button" class="ai-action-btn ai-action-btn-success" data-ai-action="spelling" title="Fix spelling and typos">
                            <span class="ai-action-label"><i class="fas fa-spell-check" aria-hidden="true"></i><span>Spelling</span></span>
                            <span class="ai-action-desc">Fix misspellings and typos without rewriting sentences.</span>
                        </button>
                        <button type="button" class="ai-action-btn ai-action-btn-success" data-ai-action="linguistic-errors" title="Find common linguistic mistakes">
                            <span class="ai-action-label"><i class="fas fa-language" aria-hidden="true"></i><span>Common linguistic errors</span></span>
                            <span class="ai-action-desc">Spot wrong words, tense shifts, agreement issues, and awkward phrasing.</span>
                        </button>
                        <button type="button" class="ai-action-btn ai-action-btn-info" data-ai-action="plot-continuity" title="Check plot and story continuity">
                            <span class="ai-action-label"><i class="fas fa-project-diagram" aria-hidden="true"></i><span>Plot continuity</span></span>
                            <span class="ai-action-desc">Flag timeline slips, character inconsistencies, and contradictions.</span>
                        </button>
                        <button type="button" class="ai-action-btn ai-action-btn-info" data-ai-action="pacing-tension" title="Review pacing and tension">
                            <span class="ai-action-label"><i class="fas fa-heartbeat" aria-hidden="true"></i><span>Pacing &amp; tension</span></span>
                            <span class="ai-action-desc">Evaluate scene rhythm, stakes, hooks, and where tension sags or rushes.</span>
                        </button>
                        <button type="button" class="ai-action-btn ai-action-btn-info" data-ai-action="narrative-style" title="Review narrative style">
                            <span class="ai-action-label"><i class="fas fa-feather-alt" aria-hidden="true"></i><span>Narrative style</span></span>
                            <span class="ai-action-desc">Assess POV, voice, tone, and show vs tell balance.</span>
                        </button>
                    </div>
                </div>
                <div class="ai-panel-chat hidden" data-ai-panel="chat" hidden>
                    <p class="ai-chat-intro small text-muted">
                        Ask about grammar, plot, pacing, style, research, or anything else. For in manuscript edits, use the Author editing tools.
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

        // Fixed to viewport so drag works anywhere on the page
        document.body.appendChild(toolbar);

        this.setupToolbarTabs(toolbar);
        this.setupChatPanel(toolbar);
        this.addAIStyles();
        this.setupDraggable(toolbar);
    }

    _viewportHeight() {
        return window.visualViewport?.height ?? window.innerHeight;
    }

    _viewportWidth() {
        return window.visualViewport?.width ?? window.innerWidth;
    }

    /**
     * Drag bounds: full horizontal range; vertical range down to bottom of viewport
     * (only the header strip must stay visible so the panel can be re-grabbed).
     */
    _getToolbarDragBounds(toolbar) {
        const margin = 8;
        const minVisible = 44;
        const rect = toolbar.getBoundingClientRect();
        const width = rect.width || toolbar.offsetWidth || 320;
        const viewportW = this._viewportWidth();
        const viewportH = this._viewportHeight();
        return {
            margin,
            minLeft: margin,
            maxLeft: Math.max(margin, viewportW - width - margin),
            minTop: margin,
            maxTop: Math.max(margin, viewportH - minVisible),
        };
    }

    _applyToolbarPosition(toolbar, left, top) {
        const bounds = this._getToolbarDragBounds(toolbar);
        const x = Math.min(bounds.maxLeft, Math.max(bounds.minLeft, left));
        const y = Math.min(bounds.maxTop, Math.max(bounds.minTop, top));
        toolbar.style.left = `${x}px`;
        toolbar.style.top = `${y}px`;
    }

    _beginToolbarDrag(toolbar, handle, clientX, clientY, dragId, source) {
        if (this._dragState) return;
        const rect = toolbar.getBoundingClientRect();
        this._prepareToolbarForDrag(toolbar);
        toolbar.style.left = `${rect.left}px`;
        toolbar.style.top = `${rect.top}px`;
        toolbar.classList.add('is-dragging');
        document.body.classList.add('ai-toolbar-drag-active');
        this._dragState = {
            dragId,
            source,
            offsetX: clientX - rect.left,
            offsetY: clientY - rect.top,
        };
        try {
            if (source === 'pointer' && handle.setPointerCapture) {
                handle.setPointerCapture(dragId);
            }
        } catch (_) { /* capture optional on some touch browsers */ }
    }

    _updateToolbarDrag(toolbar, clientX, clientY) {
        if (!this._dragState) return;
        this._applyToolbarPosition(
            toolbar,
            clientX - this._dragState.offsetX,
            clientY - this._dragState.offsetY
        );
    }

    _endToolbarDrag(toolbar, handle, dragId) {
        if (!this._dragState || this._dragState.dragId !== dragId) return;
        try {
            if (this._dragState.source === 'pointer' && handle.releasePointerCapture) {
                handle.releasePointerCapture(dragId);
            }
        } catch (_) { /* already released */ }
        toolbar.classList.remove('is-dragging');
        document.body.classList.remove('ai-toolbar-drag-active');
        this._dragState = null;
        this.clampToolbarPosition(toolbar);
        this.saveToolbarPosition(toolbar);
    }

    /**
     * Drag header to reposition; position persists in localStorage.
     * Pointer events for desktop; explicit touch handlers for phones.
     */
    setupDraggable(toolbar) {
        const handle = toolbar.querySelector('.ai-toolbar-drag-handle');
        if (!handle) return;

        this.restoreToolbarPosition(toolbar);

        const moveOpts = { capture: true, passive: false };

        const onPointerMove = (e) => {
            if (!this._dragState || this._dragState.source !== 'pointer' || e.pointerId !== this._dragState.dragId) {
                return;
            }
            e.preventDefault();
            this._updateToolbarDrag(toolbar, e.clientX, e.clientY);
        };

        const onTouchMove = (e) => {
            if (!this._dragState || this._dragState.source !== 'touch') return;
            const touch = Array.from(e.touches).find((t) => t.identifier === this._dragState.dragId);
            if (!touch) return;
            e.preventDefault();
            this._updateToolbarDrag(toolbar, touch.clientX, touch.clientY);
        };

        const cleanupPointerListeners = () => {
            document.removeEventListener('pointermove', onPointerMove, moveOpts);
            document.removeEventListener('pointerup', onPointerEnd, moveOpts);
            document.removeEventListener('pointercancel', onPointerEnd, moveOpts);
        };

        const cleanupTouchListeners = () => {
            document.removeEventListener('touchmove', onTouchMove, moveOpts);
            document.removeEventListener('touchend', onTouchEnd, moveOpts);
            document.removeEventListener('touchcancel', onTouchEnd, moveOpts);
        };

        const onPointerEnd = (e) => {
            if (!this._dragState || this._dragState.source !== 'pointer' || e.pointerId !== this._dragState.dragId) {
                return;
            }
            cleanupPointerListeners();
            this._endToolbarDrag(toolbar, handle, e.pointerId);
        };

        const onTouchEnd = (e) => {
            if (!this._dragState || this._dragState.source !== 'touch') return;
            const ended = Array.from(e.changedTouches).some((t) => t.identifier === this._dragState.dragId);
            if (!ended) return;
            cleanupTouchListeners();
            this._endToolbarDrag(toolbar, handle, this._dragState.dragId);
        };

        handle.addEventListener('pointerdown', (e) => {
            if (this._dragState) return;
            if (e.pointerType === 'mouse' && e.button !== 0) return;
            e.preventDefault();
            this._beginToolbarDrag(toolbar, handle, e.clientX, e.clientY, e.pointerId, 'pointer');
            document.addEventListener('pointermove', onPointerMove, moveOpts);
            document.addEventListener('pointerup', onPointerEnd, moveOpts);
            document.addEventListener('pointercancel', onPointerEnd, moveOpts);
        });

        handle.addEventListener('touchstart', (e) => {
            if (this._dragState || e.touches.length !== 1) return;
            const touch = e.touches[0];
            e.preventDefault();
            this._beginToolbarDrag(toolbar, handle, touch.clientX, touch.clientY, touch.identifier, 'touch');
            document.addEventListener('touchmove', onTouchMove, moveOpts);
            document.addEventListener('touchend', onTouchEnd, moveOpts);
            document.addEventListener('touchcancel', onTouchEnd, moveOpts);
        }, { passive: false });

        window.addEventListener('resize', () => this.clampToolbarPosition(toolbar));
        if (window.visualViewport) {
            window.visualViewport.addEventListener('resize', () => this.clampToolbarPosition(toolbar));
            window.visualViewport.addEventListener('scroll', () => this.clampToolbarPosition(toolbar));
        }
    }

    _prepareToolbarForDrag(toolbar) {
        toolbar.classList.add('is-positioned');
        toolbar.style.right = 'auto';
        toolbar.style.bottom = 'auto';
        toolbar.style.transform = 'none';
    }

    applyDefaultToolbarPosition(toolbar) {
        requestAnimationFrame(() => {
            const margin = 12;
            const width = toolbar.offsetWidth || 320;
            const height = toolbar.offsetHeight || 400;
            const left = Math.max(margin, window.innerWidth - width - margin);
            const top = Math.max(margin, (window.innerHeight - height) / 2);
            this._prepareToolbarForDrag(toolbar);
            toolbar.style.left = `${left}px`;
            toolbar.style.top = `${top}px`;
        });
    }

    restoreToolbarPosition(toolbar) {
        try {
            const raw = localStorage.getItem(this._positionStorageKey);
            if (!raw) {
                this.applyDefaultToolbarPosition(toolbar);
                return;
            }
            const parsed = JSON.parse(raw);
            const left = Number(parsed.left);
            const top = Number(parsed.top);
            if (!Number.isFinite(left) || !Number.isFinite(top)) {
                this.applyDefaultToolbarPosition(toolbar);
                return;
            }
            this._prepareToolbarForDrag(toolbar);
            toolbar.style.left = `${left}px`;
            toolbar.style.top = `${top}px`;
            requestAnimationFrame(() => this.clampToolbarPosition(toolbar));
        } catch (_) {
            this.applyDefaultToolbarPosition(toolbar);
        }
    }

    clampToolbarPosition(toolbar) {
        if (!toolbar.classList.contains('is-positioned')) return;
        const currentLeft = parseFloat(toolbar.style.left) || 0;
        const currentTop = parseFloat(toolbar.style.top) || 0;
        this._applyToolbarPosition(toolbar, currentLeft, currentTop);
    }

    saveToolbarPosition(toolbar) {
        const left = parseFloat(toolbar.style.left);
        const top = parseFloat(toolbar.style.top);
        if (!Number.isFinite(left) || !Number.isFinite(top)) return;
        try {
            localStorage.setItem(this._positionStorageKey, JSON.stringify({ left, top }));
        } catch (_) { /* private mode / quota */ }
    }

    /**
     * Add AI-specific styles
     */
    addAIStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .ai-toolbar {
                position: fixed;
                width: 320px;
                max-width: calc(100vw - 16px);
                background: white;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                box-shadow: 0 4px 12px rgba(0,0,0,0.1);
                z-index: 1050;
                max-height: 85vh;
                display: flex;
                flex-direction: column;
                overflow: hidden;
            }

            .ai-toolbar.is-positioned {
                right: auto;
                bottom: auto;
                transform: none;
            }

            .ai-toolbar.is-dragging {
                box-shadow: 0 12px 32px rgba(0, 0, 0, 0.22);
                opacity: 0.98;
                touch-action: none;
            }

            body.ai-toolbar-drag-active {
                touch-action: none;
                overscroll-behavior: none;
            }

            .ai-toolbar-drag-handle {
                cursor: grab;
                touch-action: none;
                -webkit-touch-callout: none;
                user-select: none;
                -webkit-user-select: none;
            }

            .ai-toolbar-drag-title {
                display: flex;
                flex-direction: column;
                gap: 2px;
                min-width: 0;
            }

            .ai-toolbar-drag-hint {
                display: none;
                font-size: 10px;
                line-height: 1.2;
                color: #64748b !important;
                font-weight: 500;
            }

            @media (pointer: coarse) {
                .ai-toolbar-drag-handle {
                    min-height: 48px;
                    padding-top: 4px;
                    padding-bottom: 4px;
                }

                .ai-toolbar-drag-hint {
                    display: block;
                }
            }

            .ai-toolbar-drag-handle:active,
            .ai-toolbar.is-dragging .ai-toolbar-drag-handle {
                cursor: grabbing;
            }

            .ai-drag-grip {
                margin-right: 6px;
                color: #94a3b8 !important;
                font-size: 12px;
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
                gap: 8px;
            }
            
            .ai-toolbar-header h6 {
                margin: 0;
                color: #2c3e50;
            }

            .ai-toolbar-header .ai-status {
                flex-shrink: 0;
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
            container.innerHTML = '<div class="ai-chat-bubble assistant">Hi, ask me anything. I can help with writing, research, or general questions, not just this chapter.</div>';
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

        if (this.authorReviewCategories[action]) {
            await this.authorReview(action);
            return;
        }

        switch (action) {
            case 'generate-content':
                await this.generateContent();
                break;
            case 'generate-ideas':
                await this.generateIdeas();
                break;
        }
    }

    /**
     * Build manuscript context for plot continuity and craft reviews.
     */
    getAuthorContext() {
        const parts = [];
        const titleInput = document.getElementById('title');
        const summaryInput = document.getElementById('summary');
        const headerHint = document.querySelector('.card-header small.text-muted');

        if (headerHint) {
            const match = headerHint.textContent.match(/Editing "(.+)" in "(.+)"/);
            if (match) {
                parts.push(`Book: ${match[2]}`);
                parts.push(`Section: ${match[1]}`);
            }
        }
        if (titleInput && titleInput.value.trim()) {
            parts.push(`Section title: ${titleInput.value.trim()}`);
        }
        if (summaryInput && summaryInput.value.trim()) {
            parts.push(`Section summary / notes: ${summaryInput.value.trim()}`);
        }
        return parts.join('\n');
    }

    /**
     * Run a category-focused author review.
     */
    async authorReview(actionKey) {
        const config = this.authorReviewCategories[actionKey];
        if (!config) return;

        const selected = (this._capturedSelectionText || this.getSelectedText() || '').trim();
        this._capturedSelectionText = '';

        let text;
        if (config.needsSelection) {
            if (!selected) {
                this.showNotification(
                    `Highlight a passage in your manuscript first, then run ${config.title}.`,
                    'warning'
                );
                return;
            }
            text = selected;
        } else {
            text = selected || this.getCurrentText();
        }

        if (!text || !text.trim()) {
            this.showNotification('No text to review, select a passage or open a chapter', 'warning');
            return;
        }

        this.showAIModal(`Reviewing: ${config.title}…`, 'loading');

        try {
            const payload = {
                text,
                category: config.category,
                context: this.getAuthorContext()
            };
            const response = await fetch('/mybook/ai/author-review', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const result = await this.handleAIResponse(response);
            if (result) {
                this.showAIResult(result, config.title);
            }
        } catch (error) {
            this.showAIResult({ success: false, error: error.message }, 'Error');
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
     * Active CKEditor 5 instance (chapter editor sets window.editor on init).
     */
    getCKEditor() {
        if (window.editor && window.editor.model) {
            return window.editor;
        }
        return null;
    }

    /**
     * Plain text from a CKEditor 5 model selection range.
     */
    getCKEditor5SelectedText(editor) {
        const selection = editor.model.document.selection;
        if (selection.isCollapsed) {
            return '';
        }
        let text = '';
        for (const item of selection.getFirstRange().getItems()) {
            if (item.is('$text') || item.is('$textProxy')) {
                text += item.data;
            }
        }
        return text;
    }

    /**
     * Selected text from any CKEditor 4 instance on the page.
     */
    getCKEditor4SelectedText() {
        if (!window.CKEDITOR || !window.CKEDITOR.instances) {
            return '';
        }
        for (const name of Object.keys(window.CKEDITOR.instances)) {
            const instance = window.CKEDITOR.instances[name];
            if (!instance || typeof instance.getSelection !== 'function') {
                continue;
            }
            const selected = instance.getSelection().getSelectedText();
            if (selected && selected.trim()) {
                return selected;
            }
        }
        return '';
    }

    /**
     * Get current text from editor
     */
    getCurrentText() {
        const ckEditor = this.getCKEditor();
        if (ckEditor && ckEditor.getData) {
            const editable = document.querySelector('.ck-editor__editable');
            if (editable) {
                return editable.innerText || editable.textContent || '';
            }
            return ckEditor.getData();
        }

        if (window.CKEDITOR && window.CKEDITOR.instances) {
            for (const name of Object.keys(window.CKEDITOR.instances)) {
                const instance = window.CKEDITOR.instances[name];
                if (!instance || typeof instance.getData !== 'function') {
                    continue;
                }
                if (instance.focusManager && instance.focusManager.hasFocus) {
                    const body = instance.document && instance.document.getBody();
                    if (body && body.getText) {
                        return body.getText();
                    }
                    return instance.getData();
                }
            }
        }
        
        // Try different editor types
        const editor = document.querySelector('.ck-editor__editable') ||
                      document.querySelector('#editor') ||
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
        const ckEditor = this.getCKEditor();
        if (ckEditor) {
            const selected = this.getCKEditor5SelectedText(ckEditor);
            if (selected) {
                return selected;
            }
        }

        const ck4Selected = this.getCKEditor4SelectedText();
        if (ck4Selected) {
            return ck4Selected;
        }

        const editable = document.querySelector('.ck-editor__editable') ||
            document.querySelector('[contenteditable="true"]');
        const selection = window.getSelection();
        if (selection && selection.rangeCount > 0 && !selection.isCollapsed) {
            if (!editable) {
                return selection.toString();
            }
            const range = selection.getRangeAt(0);
            if (editable.contains(range.commonAncestorContainer)) {
                return selection.toString();
            }
        }

        return selection ? selection.toString() : '';
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
        const canApply = result.success && result.review_mode === 'correct';
        
        const cleanedContent = result.review_mode === 'feedback'
            ? String(rawContent || '').trim()
            : this.cleanAIText(rawContent);
        
        modal.innerHTML = `
            <div class="ai-modal-content">
                <button class="ai-modal-close">&times;</button>
                <h5>${title}</h5>
                <div class="ai-result ${resultClass}">
                    <pre style="white-space: pre-wrap; font-family: inherit;">${cleanedContent}</pre>
                </div>
                ${result.success ? `
                    <div style="margin-top: 16px;">
                        ${canApply ? '<button class="btn btn-primary" id="ai-use-result">Use This</button>' : ''}
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
        const ckEditor = this.getCKEditor();
        if (ckEditor) {
            const selection = ckEditor.model.document.selection;
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
            if (this.lastReplacementPosition.isCKEditor) {
                const ckEditor = this.getCKEditor();
                if (!ckEditor) {
                    throw new Error('Editor not available');
                }
                const model = ckEditor.model;
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
                    textarea.value = ckEditor.getData();
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
        const ckEditor = this.getCKEditor();
        if (ckEditor) {
            const model = ckEditor.model;
            const selection = model.document.selection;
            
            // Insert at current position
            model.change(writer => {
                const insertPosition = selection.getFirstPosition();
                writer.insertText(text, insertPosition);
            });
            
            // Update the hidden textarea
            const textarea = document.getElementById('content');
            if (textarea) {
                textarea.value = ckEditor.getData();
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
        const ckEditor = this.getCKEditor();
        if (ckEditor) {
            const model = ckEditor.model;
            const selection = model.document.selection;
            
            model.change(writer => {
                if (!selection.isCollapsed) {
                    writer.remove(selection.getFirstRange());
                }
                writer.insertText(text, selection.getFirstPosition());
            });
            
            // Update the hidden textarea
            const textarea = document.getElementById('content');
            if (textarea) {
                textarea.value = ckEditor.getData();
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
