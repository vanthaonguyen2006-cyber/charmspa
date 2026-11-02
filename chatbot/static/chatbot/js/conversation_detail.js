/* Trang chi ti\u1ebft h\u1ed9i tho\u1ea1i (Admin / CSKH): ti\u1ebfp nh\u1eadn, tr\u1ea3 l\u1eddi, ho\u00e0n t\u1ea5t, c\u1eadp nh\u1eadt tin nh\u1eafn m\u1edbi. */
(function () {
    'use strict';
    document.addEventListener('DOMContentLoaded', function () {
        var root = document.getElementById('cvDetail');
        if (!root) return;
        var chat = document.getElementById('cvChat');
        var initialStatus = root.dataset.status;
        var tokenEl = document.querySelector('[name=csrfmiddlewaretoken]');
        var input = document.getElementById('cvInput');
        var sending = false;

        function csrf() { return tokenEl ? tokenEl.value : ''; }
        function esc(s) {
            return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
                return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
            });
        }
        function toast(text) {
            var t = document.createElement('div');
            t.className = 'cv-toast';
            t.textContent = text;
            document.body.appendChild(t);
            setTimeout(function () { t.remove(); }, 4000);
        }
        function scrollDown() { chat.scrollTop = chat.scrollHeight; }
        function has(id) { return !!chat.querySelector('[data-id="' + id + '"]'); }

        function addMessage(m) {
            if (has(m.id)) return;
            var kind = m.sender === 'Nh\u00e2n vi\u00ean' ? 'staff' : (m.sender === 'Chatbot' ? 'bot' : 'cust');
            var d = document.createElement('div');
            d.className = 'cv-msg ' + kind;
            d.dataset.id = m.id;
            d.innerHTML = '<span class="cv-meta">' + esc(m.sender) + ' \u2022 ' + esc(m.time) + '</span>' +
                '<div class="cv-bubble">' + esc(m.content).replace(/\n/g, '<br>') + '</div>';
            var empty = chat.querySelector('.cv-sysline');
            if (empty && empty.textContent.indexOf('Ch\u01b0a c\u00f3 tin nh\u1eafn') === 0) empty.remove();
            chat.appendChild(d);
        }

        function request(url, body) {
            return fetch(url, {
                method: 'POST', credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
                body: JSON.stringify(body || {})
            }).then(function (res) {
                return res.json().catch(function () { return {}; }).then(function (d) {
                    if (!res.ok || d.ok === false) throw new Error(d.error || ('L\u1ed7i m\u00e1y ch\u1ee7 (' + res.status + ')'));
                    return d;
                });
            });
        }

        scrollDown();

        /* Ti\u1ebfp nh\u1eadn */
        var accept = document.getElementById('cvAccept');
        if (accept) accept.addEventListener('click', function () {
            if (accept.disabled) return;
            accept.disabled = true;
            request(root.dataset.acceptUrl).then(function () { window.location.reload(); })
                .catch(function (err) { toast(err.message); accept.disabled = false; });
        });

        /* G\u1eedi ph\u1ea3n h\u1ed3i */
        var form = document.getElementById('cvCompose');
        if (form) {
            input.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
            });
            input.addEventListener('input', function () {
                input.style.height = 'auto';
                input.style.height = Math.min(input.scrollHeight, 120) + 'px';
            });
            form.addEventListener('submit', function (e) {
                e.preventDefault();
                var text = input.value.trim();
                if (!text || sending) return;
                sending = true;
                request(root.dataset.replyUrl, { message: text }).then(function (r) {
                    addMessage({ id: r.id, sender: 'Nh\u00e2n vi\u00ean', time: r.time, content: text });
                    input.value = ''; input.style.height = 'auto';
                    scrollDown();
                    if (initialStatus === 'Ch\u1edd x\u1eed l\u00fd') window.location.reload();
                }).catch(function (err) { toast(err.message); })
                    .then(function () { sending = false; });
            });
        }

        /* H\u1ed9p tho\u1ea1i ho\u00e0n t\u1ea5t */
        var modal = document.getElementById('cvModal');
        var openBtn = document.getElementById('cvOpenComplete');
        function closeModal() { modal.classList.remove('open'); modal.setAttribute('aria-hidden', 'true'); }
        if (openBtn) openBtn.addEventListener('click', function () {
            if (openBtn.disabled) return;
            modal.classList.add('open');
            modal.setAttribute('aria-hidden', 'false');
            document.getElementById('cvNote').focus();
        });
        document.getElementById('cvCancelComplete').addEventListener('click', closeModal);
        modal.addEventListener('click', function (e) { if (e.target === modal) closeModal(); });
        document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeModal(); });

        /* C\u1eadp nh\u1eadt tin nh\u1eafn m\u1edbi c\u1ee7a kh\u00e1ch */
        function poll() {
            fetch(root.dataset.messagesUrl, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } })
                .then(function (res) { return res.ok ? res.json() : null; })
                .then(function (d) {
                    if (!d || !d.ok) return;
                    var atBottom = chat.scrollHeight - chat.scrollTop - chat.clientHeight < 80;
                    d.messages.forEach(addMessage);
                    if (atBottom) scrollDown();
                    if (d.status !== initialStatus && (!input || !input.value.trim())) window.location.reload();
                })
                .catch(function () { /* th\u1eed l\u1ea1i l\u1ea7n sau */ })
                .then(function () { setTimeout(poll, 3000); });
        }
        setTimeout(poll, 3000);

        if (window.lucide) window.lucide.createIcons();
    });
})();
