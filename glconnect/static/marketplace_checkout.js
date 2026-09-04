/**
 * Marketplace book-detail modal: format selection, order summary, Stripe checkout.
 * Requires Bootstrap 5 and window.INK_MARKETPLACE_CONFIG from the template.
 */
(function () {
    'use strict';

    var config = window.INK_MARKETPLACE_CONFIG || {};
    var bookDetailsPurchaseState = null;
    var checkoutInFlight = false;

    function escapeHtml(text) {
        if (text === null || text === undefined) return '';
        var d = document.createElement('div');
        d.textContent = String(text);
        return d.innerHTML;
    }

    function money(n) {
        return '$' + Number(n || 0).toFixed(2);
    }

    function computeFormatTotal(opts, formats) {
        var fmts = (formats || []).filter(function (f) {
            return f === 'digital' || f === 'audiobook' || f === 'print';
        });
        if (!fmts.length) return 0;
        var total = 0;
        var hasDigital = fmts.indexOf('digital') >= 0;
        var hasAudio = fmts.indexOf('audiobook') >= 0;
        if (hasDigital && hasAudio) {
            total += (Number(opts.digital || 0) + Number(opts.audiobook || 0)) * 0.8;
        } else {
            if (hasDigital) total += Number(opts.digital || 0);
            if (hasAudio) total += Number(opts.audiobook || 0);
        }
        if (fmts.indexOf('print') >= 0) {
            total += Number(opts.print_price || 0) + Number(opts.print_shipping || 0);
        }
        return total;
    }

    function defaultFormats(opts) {
        if (Number(opts.digital || 0) > 0) return ['digital'];
        if (Number(opts.audiobook || 0) > 0) return ['audiobook'];
        if (opts.print) return ['print'];
        return [];
    }

    function buildOrderLines(opts, formats) {
        var lines = [];
        var fmts = formats.slice();
        var hasDigital = fmts.indexOf('digital') >= 0;
        var hasAudio = fmts.indexOf('audiobook') >= 0;
        if (hasDigital && hasAudio) {
            var bundleBase = Number(opts.digital || 0) + Number(opts.audiobook || 0);
            var bundlePrice = bundleBase * 0.8;
            lines.push({ label: 'Ebook + AI-narrated audiobook bundle', amount: bundlePrice, note: 'Save 20%' });
        } else {
            if (hasDigital) lines.push({ label: 'Ebook', amount: Number(opts.digital || 0) });
            if (hasAudio) lines.push({ label: 'AI-narrated audiobook', amount: Number(opts.audiobook || 0) });
        }
        if (fmts.indexOf('print') >= 0) {
            lines.push({ label: 'Print edition', amount: Number(opts.print_price || 0) });
            if (Number(opts.print_shipping || 0) > 0) {
                lines.push({ label: 'Shipping (US)', amount: Number(opts.print_shipping || 0) });
            }
        }
        return lines;
    }

    function getSelectedFormatsFromPicker() {
        var out = [];
        document.querySelectorAll('#bookDetailsFormatPicker .book-format-pick:checked').forEach(function (cb) {
            if (!cb.disabled) out.push(cb.value);
        });
        return out;
    }

    function setCheckoutStatus(message, tone) {
        var el = document.getElementById('bookDetailsCheckoutStatus');
        if (!el) return;
        if (!message) {
            el.className = 'ink-mp-checkout-status d-none';
            el.textContent = '';
            return;
        }
        var cls = 'ink-mp-checkout-status alert alert-' + (tone || 'info') + ' small mb-0';
        el.className = cls;
        el.textContent = message;
    }

    function setCheckoutLoading(loading) {
        checkoutInFlight = !!loading;
        var btn = document.getElementById('bookDetailsCheckoutBtn');
        if (!btn) return;
        var label = btn.querySelector('.ink-mp-checkout-btn-label');
        var spin = btn.querySelector('.ink-mp-checkout-btn-loading');
        btn.disabled = loading || !(bookDetailsPurchaseState && bookDetailsPurchaseState.selectedFormats.length);
        if (label) label.classList.toggle('d-none', loading);
        if (spin) spin.classList.toggle('d-none', !loading);
    }

    function syncBookDetailsCheckoutUi() {
        var state = bookDetailsPurchaseState;
        var checkoutBtn = document.getElementById('bookDetailsCheckoutBtn');
        var summaryWrap = document.getElementById('bookDetailsOrderSummary');
        var linesEl = document.getElementById('bookDetailsOrderLines');
        var totalEl = document.getElementById('bookDetailsCheckoutTotal');
        var hint = document.getElementById('bookDetailsFormatHint');
        if (!state || !checkoutBtn) return;

        var selected = getSelectedFormatsFromPicker();
        state.selectedFormats = selected;
        var total = computeFormatTotal(state.opts, selected);
        var hasPaidSelection = selected.length > 0 && total > 0;

        if (summaryWrap) summaryWrap.classList.toggle('d-none', !hasPaidSelection);
        if (totalEl) totalEl.textContent = money(total);
        checkoutBtn.classList.toggle('d-none', !state.hasPaidFormats);

        var waiverWrap = document.getElementById('bookDetailsDigitalWaiver');
        var waiverCheck = document.getElementById('bookDetailsDigitalWaiverCheck');
        var needsDigitalWaiver = hasPaidSelection && selected.some(function (f) {
            return f === 'digital' || f === 'audiobook';
        });
        if (waiverWrap) {
            waiverWrap.classList.toggle('d-none', !needsDigitalWaiver);
            if (!needsDigitalWaiver && waiverCheck) waiverCheck.checked = false;
        }
        var waiverOk = !needsDigitalWaiver || (waiverCheck && waiverCheck.checked);

        if (!checkoutInFlight) {
            checkoutBtn.disabled = !hasPaidSelection || !waiverOk;
        }

        if (linesEl && hasPaidSelection) {
            var lines = buildOrderLines(state.opts, selected);
            linesEl.innerHTML = lines.map(function (line) {
                var note = line.note ? ' <span class="ink-mp-order-note">' + escapeHtml(line.note) + '</span>' : '';
                return '<div class="ink-mp-order-line"><span>' + escapeHtml(line.label) + note + '</span><span>' + money(line.amount) + '</span></div>';
            }).join('');
        }

        if (hint) {
            if (!state.hasPaidFormats) {
                hint.textContent = '';
            } else if (!selected.length) {
                hint.textContent = 'Select at least one format to continue.';
            } else if (selected.indexOf('print') >= 0) {
                hint.textContent = 'Print ships to a US address (collected on Stripe). Author fulfills within about ' + (state.opts.print_handling_days || 7) + ' business days.';
            } else if (selected.indexOf('digital') >= 0 && selected.indexOf('audiobook') >= 0) {
                hint.textContent = 'Bundle applied: ebook + audiobook save 20%. Digital formats unlock in My Library after payment.';
            } else {
                hint.textContent = 'Digital formats unlock in My Library after payment.';
            }
        }
    }

    function buildFormatPickerHtml(b, opts, flags) {
        var html = '<div class="mt-4 pt-3 border-top ink-mp-format-section">';
        html += '<p class="small text-muted mb-2"><strong>Choose format</strong></p>';
        html += '<div id="bookDetailsFormatPicker" class="ink-mp-format-grid">';

        if (flags.hasPaidDigital) {
            var digitalChecked = flags.defaultFormats.indexOf('digital') >= 0 ? ' checked' : '';
            var typeLabel = b.digital_file_type ? ' (' + escapeHtml(b.digital_file_type) + ')' : '';
            html += formatCard('bdfDigital', 'digital', digitalChecked,
                'Ebook' + typeLabel,
                money(opts.digital),
                'Download & read in My Library');
        }
        if (flags.hasPaidAudio) {
            var audioChecked = flags.defaultFormats.indexOf('audiobook') >= 0 && flags.defaultFormats.indexOf('digital') < 0 ? ' checked' : '';
            html += formatCard('bdfAudiobook', 'audiobook', audioChecked,
                'AI-narrated audiobook',
                money(opts.audiobook),
                'Stream or download after purchase');
        }
        if (flags.hasPaidPrint) {
            var printChecked = flags.defaultFormats.indexOf('print') >= 0 ? ' checked' : '';
            var shipNote = ' + ' + money(opts.print_shipping) + ' shipping';
            var days = b.print_handling_days ? ', ~' + Number(b.print_handling_days) + ' day handling' : '';
            html += formatCard('bdfPrint', 'print', printChecked,
                'Print edition',
                money(opts.print_price) + shipNote,
                'Author ships to your US address' + days);
        }

        html += '</div>';

        if (flags.hasPaidDigital && flags.hasPaidAudio) {
            var bundlePrice = (Number(opts.digital) + Number(opts.audiobook)) * 0.8;
            html += '<button type="button" class="btn btn-sm btn-outline-warning mt-2 ink-mp-bundle-btn" id="bookDetailsBundleBtn">';
            html += '<i class="fas fa-tags me-1" aria-hidden="true"></i>Bundle ebook + audiobook — Save 20% (' + money(bundlePrice) + ')';
            html += '</button>';
        }

        html += '<p class="small text-muted mt-2 mb-0" id="bookDetailsFormatHint"></p>';
        html += '<p class="small text-muted mb-0"><i class="fas fa-info-circle me-1"></i>All sales are final. Digital delivery is instant; print orders ship to a US address only.</p>';
        html += '</div>';
        return html;
    }

    function formatCard(id, value, checked, title, price, subtitle) {
        return '<label class="ink-mp-format-card" for="' + id + '">' +
            '<input class="form-check-input book-format-pick" type="checkbox" id="' + id + '" value="' + value + '"' + checked + '>' +
            '<span class="ink-mp-format-card-body">' +
            '<span class="ink-mp-format-title">' + title + '</span>' +
            '<span class="ink-mp-format-price">' + price + '</span>' +
            '<span class="ink-mp-format-sub">' + escapeHtml(subtitle) + '</span>' +
            '</span></label>';
    }

    function bindFormatPickerEvents() {
        document.querySelectorAll('#bookDetailsFormatPicker .book-format-pick').forEach(function (cb) {
            cb.addEventListener('change', syncBookDetailsCheckoutUi);
        });
        var bundleBtn = document.getElementById('bookDetailsBundleBtn');
        if (bundleBtn) {
            bundleBtn.addEventListener('click', function () {
                ['bdfDigital', 'bdfAudiobook'].forEach(function (id) {
                    var el = document.getElementById(id);
                    if (el) el.checked = true;
                });
                var printEl = document.getElementById('bdfPrint');
                if (printEl) printEl.checked = false;
                syncBookDetailsCheckoutUi();
            });
        }
    }

    function buyWithStripeLink(bookId, total, selectedFormats) {
        if (checkoutInFlight) return;
        setCheckoutStatus('', '');
        setCheckoutLoading(true);

        var requestBody = { combo_formats: selectedFormats.slice() };
        if (selectedFormats.length === 1) {
            requestBody.purchase_type = selectedFormats[0];
        } else if (selectedFormats.length === 2 &&
            selectedFormats.indexOf('digital') >= 0 &&
            selectedFormats.indexOf('audiobook') >= 0) {
            requestBody.purchase_type = 'bundle';
        } else {
            requestBody.purchase_type = 'combo:' + selectedFormats.slice().sort().join(',');
        }
        requestBody.custom_amount = total;
        var waiverCheck = document.getElementById('bookDetailsDigitalWaiverCheck');
        var needsDigitalWaiver = selectedFormats.some(function (f) {
            return f === 'digital' || f === 'audiobook';
        });
        if (needsDigitalWaiver) {
            if (!waiverCheck || !waiverCheck.checked) {
                setCheckoutLoading(false);
                setCheckoutStatus(
                    'Please confirm immediate digital delivery and the withdrawal waiver for ebook/audiobook items.',
                    'warning'
                );
                return;
            }
            requestBody.digital_delivery_waiver = true;
        }

        fetch('/mybook/books/' + bookId + '/purchase', {
            method: 'POST',
            credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body: JSON.stringify(requestBody),
        })
            .then(function (response) {
                var ct = response.headers.get('content-type') || '';
                if (!ct.includes('application/json')) {
                    return response.text().then(function (text) {
                        throw new Error('Unexpected server response. Please try again.');
                    });
                }
                return response.json().then(function (data) {
                    if (!response.ok) {
                        var code = data.error_code || data.operator_error_code;
                        var detail = data.error || data.message || 'Checkout could not start.';
                        throw new Error(code ? ('[' + code + '] ' + detail) : detail);
                    }
                    return data;
                });
            })
            .then(function (data) {
                if (!data.success) {
                    throw new Error(data.error || 'Checkout could not start.');
                }
                var url = data.stripe_checkout_url || data.stripe_payment_link;
                if (url) {
                    window.location.href = url;
                    return;
                }
                throw new Error('Checkout link not available. Please try again.');
            })
            .catch(function (err) {
                console.error('Checkout error:', err);
                setCheckoutLoading(false);
                var msg = (err && err.message) ? err.message : 'We could not start checkout. Please try again.';
                if (/Server error|traceback|psycopg2|database/i.test(msg)) {
                    msg = 'We could not start checkout. Please try again or contact support.';
                }
                setCheckoutStatus(msg, 'danger');
            });
    }

    function viewBook(bookId) {
        var modalEl = document.getElementById('bookDetailsModal');
        if (!modalEl) return;
        var modal = bootstrap.Modal.getOrCreateInstance(modalEl);
        var titleEl = document.getElementById('bookDetailsTitle');
        var bodyEl = document.getElementById('bookDetailsBody');
        var actionsEl = document.getElementById('bookDetailsActions');
        if (!bodyEl || !actionsEl) return;

        checkoutInFlight = false;
        bookDetailsPurchaseState = null;
        setCheckoutStatus('', '');
        setCheckoutLoading(false);

        if (titleEl) titleEl.textContent = 'Loading…';
        actionsEl.innerHTML = '';
        var checkoutBtn = document.getElementById('bookDetailsCheckoutBtn');
        if (checkoutBtn) {
            checkoutBtn.classList.add('d-none');
            checkoutBtn.disabled = true;
            checkoutBtn.onclick = null;
        }
        var summaryWrap = document.getElementById('bookDetailsOrderSummary');
        if (summaryWrap) summaryWrap.classList.add('d-none');

        bodyEl.innerHTML = '<div class="text-center py-4">' +
            '<div class="spinner-border text-primary" role="status"><span class="visually-hidden">Loading</span></div>' +
            '<p class="mt-3 text-muted mb-0">Loading book details…</p></div>';
        modal.show();

        fetch('/mybook/api/marketplace/books/' + encodeURIComponent(bookId), {
            credentials: 'same-origin',
            headers: { 'Accept': 'application/json' },
        })
            .then(function (r) {
                return r.json().then(function (data) {
                    if (!r.ok) throw new Error((data && data.error) || 'Could not load this book.');
                    return data;
                });
            })
            .then(function (data) {
                if (!data.success || !data.book) throw new Error('Invalid response');
                var b = data.book;
                if (titleEl) titleEl.textContent = b.title;

                var coverBlock = b.cover_url
                    ? '<div class="col-md-4 text-center mb-3 mb-md-0"><img src="' + escapeHtml(b.cover_url) + '" class="img-fluid rounded shadow ink-mp-detail-cover" alt=""></div>'
                    : '<div class="col-md-4 text-center mb-3 mb-md-0"><div class="book-cover-placeholder rounded d-flex align-items-center justify-content-center bg-light ink-mp-detail-cover-ph"><i class="fas fa-book fa-4x text-muted"></i></div></div>';

                var descHtml = (b.description || '').trim();
                var priceDigital = b.price != null ? Number(b.price) : null;
                var priceAudio = b.audiobook_price != null ? Number(b.audiobook_price) : null;
                var fmtDigital = b.formats && b.formats.digital;
                var fmtAudio = b.formats && b.formats.audiobook;
                var fmtPrint = b.formats && b.formats.print;
                var pricePrint = b.print_price != null ? Number(b.print_price) : null;
                var pricePrintShip = b.print_shipping_price != null ? Number(b.print_shipping_price) : 0;

                var purchaseOpts = {
                    digital: (fmtDigital && priceDigital != null && priceDigital > 0) ? priceDigital : 0,
                    audiobook: (fmtAudio && priceAudio != null && priceAudio > 0) ? priceAudio : 0,
                    print: !!(fmtPrint && pricePrint != null && pricePrint > 0),
                    print_price: (fmtPrint && pricePrint != null && pricePrint > 0) ? pricePrint : 0,
                    print_shipping: pricePrintShip || 0,
                    print_handling_days: Number(b.print_handling_days || 7),
                };
                var hasPaidDigital = fmtDigital && priceDigital != null && priceDigital > 0;
                var hasPaidAudio = fmtAudio && priceAudio != null && priceAudio > 0;
                var hasPaidPrint = purchaseOpts.print;
                var hasPaidFormats = hasPaidDigital || hasPaidAudio || hasPaidPrint;
                var hasFreeDigital = fmtDigital && priceDigital === 0;
                var defaultFmts = defaultFormats(purchaseOpts);

                var investBadge = '';
                if (b.investment && (b.investment.active || b.investment.funded)) {
                    investBadge = '<span class="badge bg-success ms-1">Community funded</span>';
                }

                var pickerHtml = '';
                if (hasPaidFormats) {
                    pickerHtml = buildFormatPickerHtml(b, purchaseOpts, {
                        hasPaidDigital: hasPaidDigital,
                        hasPaidAudio: hasPaidAudio,
                        hasPaidPrint: hasPaidPrint,
                        defaultFormats: defaultFmts,
                    });
                } else {
                    var formatLines = [];
                    if (fmtDigital) formatLines.push('<li>Ebook' + (priceDigital === 0 ? ' — Free' : '') + '</li>');
                    if (fmtAudio) formatLines.push('<li>AI-narrated audiobook' + (priceAudio === 0 ? ' — Free' : '') + '</li>');
                    if (fmtPrint && pricePrint > 0) formatLines.push('<li>Print — ' + money(pricePrint) + '</li>');
                    if (!formatLines.length) formatLines.push('<li class="text-muted">See listing for availability.</li>');
                    pickerHtml = '<div class="mt-4 pt-3 border-top"><p class="small text-muted mb-1"><strong>Formats</strong></p><ul class="small mb-0">' + formatLines.join('') + '</ul></div>';
                }

                bodyEl.innerHTML =
                    '<div class="row">' + coverBlock +
                    '<div class="col-md-8">' +
                    '<p class="text-muted mb-2"><i class="fas fa-user-edit me-1"></i>by <strong>' + escapeHtml(b.author.name) + '</strong>' +
                    (b.author.marketplace_book_count > 1 ? ' <span class="small">(' + b.author.marketplace_book_count + ' titles)</span>' : '') +
                    '</p>' +
                    (b.publisher_name ? '<p class="small text-muted mb-2"><i class="fas fa-building me-1"></i>Publisher: <strong>' + escapeHtml(b.publisher_name) + '</strong></p>' : '') +
                    (b.isbn_display || b.isbn ? '<p class="small text-muted mb-2"><i class="fas fa-barcode me-1"></i>ISBN: <strong>' + escapeHtml(b.isbn_display || b.isbn) + '</strong></p>' : '') +
                    '<div class="d-flex flex-wrap gap-1 mb-3">' +
                    (b.genre ? '<span class="badge bg-primary">' + escapeHtml(b.genre) + '</span>' : '') +
                    (fmtDigital ? '<span class="badge bg-success-subtle text-success border">Ebook</span>' : '') +
                    (fmtAudio ? '<span class="badge bg-info-subtle text-info border">AI-narrated audiobook</span>' : '') +
                    (fmtPrint ? '<span class="badge bg-warning-subtle text-warning border">Print</span>' : '') +
                    '<span class="badge bg-secondary">' + escapeHtml(b.language_label || b.language || '') + '</span>' +
                    (b.word_count ? '<span class="badge bg-light border text-muted">' + b.word_count.toLocaleString() + ' words</span>' : '') +
                    investBadge +
                    '</div>' +
                    '<div class="book-description ink-project-description text-muted small">' + (descHtml || '<em>No description yet.</em>') + '</div>' +
                    pickerHtml +
                    '</div></div>';

                actionsEl.innerHTML = '';
                bookDetailsPurchaseState = hasPaidFormats ? {
                    bookId: b.id,
                    opts: purchaseOpts,
                    hasPaidFormats: true,
                    selectedFormats: defaultFmts.slice(),
                } : null;

                bindFormatPickerEvents();
                syncBookDetailsCheckoutUi();

                if (checkoutBtn && hasPaidFormats) {
                    checkoutBtn.onclick = function () {
                        var selected = (bookDetailsPurchaseState && bookDetailsPurchaseState.selectedFormats) || [];
                        if (!selected.length) {
                            setCheckoutStatus('Select at least one format to continue.', 'warning');
                            return;
                        }
                        var total = computeFormatTotal(purchaseOpts, selected);
                        buyWithStripeLink(b.id, total, selected);
                    };
                }

                if (hasFreeDigital) {
                    var dlBtn = document.createElement('button');
                    dlBtn.type = 'button';
                    dlBtn.className = 'btn btn-outline-primary btn-sm';
                    dlBtn.innerHTML = '<i class="fas fa-download me-1"></i>Free ebook';
                    dlBtn.addEventListener('click', function () {
                        window.open('/mybook/books/' + b.id + '/download', '_blank');
                    });
                    actionsEl.appendChild(dlBtn);
                }
                if (fmtAudio && b.audiobook_preview_url) {
                    var pbtn = document.createElement('button');
                    pbtn.type = 'button';
                    pbtn.className = 'btn btn-outline-info btn-sm';
                    pbtn.innerHTML = '<i class="fas fa-play me-1"></i>Preview 30s';
                    pbtn.addEventListener('click', function () {
                        window.open(b.audiobook_preview_url, '_blank');
                    });
                    actionsEl.appendChild(pbtn);
                }
            })
            .catch(function (err) {
                console.error(err);
                if (titleEl) titleEl.textContent = 'Book unavailable';
                bodyEl.innerHTML = '<div class="alert alert-warning mb-0"><i class="fas fa-exclamation-triangle me-2"></i>' +
                    escapeHtml(err.message || 'Something went wrong.') + '</div>';
            });
    }

    window.viewBook = viewBook;

    document.addEventListener('DOMContentLoaded', function () {
        var waiverCheck = document.getElementById('bookDetailsDigitalWaiverCheck');
        if (waiverCheck) {
            waiverCheck.addEventListener('change', syncBookDetailsCheckoutUi);
        }
        try {
            var params = new URLSearchParams(window.location.search);
            var ob = params.get('open_book');
            if (ob && /^\d+$/.test(ob)) {
                setTimeout(function () { viewBook(parseInt(ob, 10)); }, 250);
            }
        } catch (e) { /* ignore */ }
    });
})();
