/* ==========================================================================
   Widget chatbot t\u01b0 v\u1ea5n (kh\u00e1ch h\u00e0ng): ch\u1ea1y theo k\u1ecbch b\u1ea3n \u0111\u00e3 thi\u1ebft k\u1ebf \u1edf trang Qu\u1ea3n l\u00fd k\u1ecbch b\u1ea3n.
   - N\u00fat l\u1ef1a ch\u1ecdn l\u1ea5y t\u1eeb s\u01a1 \u0111\u1ed3 k\u1ecbch b\u1ea3n (m\u00e1y ch\u1ee7 quy\u1ebft \u0111\u1ecbnh b\u01b0\u1edbc ti\u1ebfp theo).
   - "Y\u00eau c\u1ea7u t\u01b0 v\u1ea5n": kh\u00e1ch v\u00e3ng lai \u0111i\u1ec1n form, kh\u00e1ch \u0111\u00e3 \u0111\u0103ng nh\u1eadp \u0111\u01b0\u1ee3c l\u1ea5y th\u00f4ng tin t\u1eeb t\u00e0i kho\u1ea3n.
   - Sau khi g\u1eedi: ch\u1edd nh\u00e2n vi\u00ean ti\u1ebfp nh\u1eadn -> m\u1edf \u00f4 nh\u1eafn tin -> k\u1ebft th\u00fac khi nh\u00e2n vi\u00ean ho\u00e0n t\u1ea5t.
   ========================================================================== */
(function () {
    'use strict';

    var cfg = window.CG_CONFIG || {};
    var root = document.getElementById('cgWidget');
    if (!root) return;

    var NEEDS = ['Ch\u1ecdn li\u1ec7u tr\u00ecnh', 'H\u1ed7 tr\u1ee3 \u0111\u1eb7t l\u1ecbch', 'Ch\u0103m s\u00f3c sau li\u1ec7u tr\u00ecnh', 'Kh\u00e1c'];
    var TITLE = 'Charm Grand \u2013 Tr\u1ee3 l\u00fd t\u01b0 v\u1ea5n';
    var ICON_CHAT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/></svg>';
    var ICON_SEND = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M2.5 11.2 20.8 3.4a.8.8 0 0 1 1.1.9l-3.2 15.4a.8.8 0 0 1-1.2.5l-4.6-3-2.4 2.9a.5.5 0 0 1-.9-.3v-3.9l8-7-9.7 6-4.2-1.5a.8.8 0 0 1 0-1.5z"/></svg>';

    var sid = '';
    var me = null;               // th\u00f4ng tin t\u00e0i kho\u1ea3n kh\u00e1ch (n\u1ebfu \u0111\u00e3 \u0111\u0103ng nh\u1eadp)
    var mode = 'bot';            // bot | waiting | live | done
    var isOpen = false, booted = false;
    var stack = [];              // c\u00e1c b\u01b0\u1edbc \u0111\u00e3 hi\u1ec3n th\u1ecb (\u0111\u1ec3 "Quay l\u1ea1i")
    var path = [];               // \u0111\u01b0\u1eddng \u0111i kh\u00e1ch \u0111\u00e3 ch\u1ecdn
    var lastService = '';
    var seen = {};               // id tin nh\u1eafn nh\u00e2n vi\u00ean \u0111\u00e3 hi\u1ec3n th\u1ecb
    var staffName = '';
    var unread = 0;
    var pollTimer = null;
    var el = {};

    /* ---------------- Ti\u1ec7n \u00edch ---------------- */
    function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }
    function nl2br(s) { return esc(s).replace(/\n/g, '<br>'); }
    function money(n) { return Number(n || 0).toLocaleString('vi-VN'); }
    function safeUrl(u) { return /^(https?:\/\/|\/)/.test(u || '') ? u : ''; }
    function nowTime() {
        var d = new Date();
        return ('0' + d.getHours()).slice(-2) + ':' + ('0' + d.getMinutes()).slice(-2);
    }
    function newSid() {
        var chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789', out = 'P', i;
        var buf = new Uint8Array(9);
        if (window.crypto && window.crypto.getRandomValues) window.crypto.getRandomValues(buf);
        else for (i = 0; i < 9; i++) buf[i] = Math.floor(Math.random() * 256);
        for (i = 0; i < 9; i++) out += chars.charAt(buf[i] % chars.length);
        return out;
    }
    function csrf() {
        var m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
        return m ? decodeURIComponent(m[1]) : '';
    }
    function parse(res) {
        return res.json().catch(function () { return {}; }).then(function (d) {
            if (!res.ok || d.ok === false) throw new Error(d.error || ('L\u1ed7i m\u00e1y ch\u1ee7 (' + res.status + ')'));
            return d;
        });
    }
    function post(url, body) {
        return fetch(url, {
            method: 'POST', credentials: 'same-origin',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
            body: JSON.stringify(body)
        }).then(parse);
    }
    function get(url) {
        return fetch(url, { credentials: 'same-origin', headers: { 'Accept': 'application/json' } }).then(parse);
    }
    function store(key, val) { try { window.localStorage.setItem(key, val); } catch (e) { /* b\u1ecf qua */ } }
    function load(key) { try { return window.localStorage.getItem(key) || ''; } catch (e) { return ''; } }
    function node(tag, cls, html) {
        var n = document.createElement(tag);
        if (cls) n.className = cls;
        if (html != null) n.innerHTML = html;
        return n;
    }

    /* ---------------- D\u1ef1ng giao di\u1ec7n ---------------- */
    function build() {
        root.innerHTML =
            '<button type="button" class="cg-launcher" id="cgLauncher" aria-label="M\u1edf chatbot t\u01b0 v\u1ea5n">' + ICON_CHAT +
            '<span>Charm Grand t\u01b0 v\u1ea5n</span><i class="cg-badge" id="cgBadge" hidden>0</i></button>' +
            '<section class="cg-window" id="cgWindow" hidden role="dialog" aria-label="Chatbot t\u01b0 v\u1ea5n">' +
            '<header class="cg-head"><div><strong id="cgTitle">' + esc(TITLE) + '</strong>' +
            '<small id="cgStatus">\u25cf S\u1eb5n s\u00e0ng h\u1ed7 tr\u1ee3 b\u1ea1n</small></div><div>' +
            '<button type="button" id="cgMin" aria-label="Thu nh\u1ecf">&minus;</button>' +
            '<button type="button" id="cgClose" aria-label="\u0110\u00f3ng">&times;</button></div></header>' +
            '<div class="cg-trail" id="cgTrail"></div>' +
            '<div class="cg-body" id="cgBody"></div>' +
            '<footer class="cg-foot">' +
            '<form class="cg-compose" id="cgCompose" hidden autocomplete="off">' +
            '<input id="cgInput" type="text" maxlength="1000" placeholder="Nh\u1eadp tin nh\u1eafn...">' +
            '<button type="submit" aria-label="G\u1eedi">' + ICON_SEND + '</button></form>' +
            '<div class="cg-waitnote" id="cgWait" hidden>\u00d4 nh\u1eafn tin s\u1ebd m\u1edf khi nh\u00e2n vi\u00ean ti\u1ebfp nh\u1eadn y\u00eau c\u1ea7u c\u1ee7a b\u1ea1n.</div>' +
            '<div class="cg-links"><a id="cgHistory" href="' + esc(cfg.history || '#') + '">L\u1ecbch s\u1eed h\u1ed9i tho\u1ea1i</a>' +
            '<button type="button" id="cgAsk">Y\u00eau c\u1ea7u t\u01b0 v\u1ea5n</button></div></footer></section>';
        ['Launcher', 'Badge', 'Window', 'Title', 'Status', 'Min', 'Close', 'Trail', 'Body', 'Compose', 'Input', 'Wait', 'Ask']
            .forEach(function (k) { el[k] = document.getElementById('cg' + k); });

        el.Launcher.addEventListener('click', openWindow);
        el.Min.addEventListener('click', closeWindow);
        el.Close.addEventListener('click', closeWindow);
        el.Ask.addEventListener('click', function () {
            openConsult({ title: 'Y\u00eau c\u1ea7u t\u01b0 v\u1ea5n', options: [{ text: 'G\u1eedi y\u00eau c\u1ea7u' }] });
        });
        el.Compose.addEventListener('submit', function (e) { e.preventDefault(); sendMessage(); });
    }

    function scrollDown() { el.Body.scrollTop = el.Body.scrollHeight; }
    function setHeader(title, status) {
        el.Title.textContent = title;
        el.Status.textContent = status;
    }
    function setTrail() { el.Trail.textContent = path.length ? path.join(' \u2192 ') : ''; }

    function bubble(kind, html, meta) {
        var m = node('div', 'cg-msg ' + kind);
        if (meta) m.appendChild(node('span', 'cg-meta', esc(meta)));
        m.appendChild(node('div', 'cg-bubble', html));
        el.Body.appendChild(m);
        scrollDown();
        return m;
    }
    function botSays(html) { return bubble('bot', html, 'Chatbot \u2022 ' + nowTime()); }
    function sys(text) { return bubble('sys', esc(text)); }

    function chip(text, cls, onClick) {
        var b = node('button', 'cg-chip' + (cls ? ' ' + cls : ''));
        b.type = 'button';
        b.textContent = text;
        b.addEventListener('click', function () { onClick(b); });
        return b;
    }
    function lock(box, picked) {
        Array.prototype.forEach.call(box.querySelectorAll('button'), function (b) {
            b.disabled = true;
            if (b === picked) b.classList.add('picked');
        });
    }

    /* ---------------- M\u1edf / \u0111\u00f3ng ---------------- */
    function openWindow() {
        isOpen = true;
        el.Window.hidden = false;
        el.Launcher.hidden = true;
        unread = 0; updateBadge();
        if (!booted) boot(); else scrollDown();
        if (el.Compose.hidden === false) el.Input.focus();
        schedulePoll(300);
    }
    function closeWindow() {
        isOpen = false;
        el.Window.hidden = true;
        el.Launcher.hidden = false;
    }
    function updateBadge() {
        el.Badge.hidden = unread <= 0;
        el.Badge.textContent = unread > 9 ? '9+' : String(unread);
    }

    /* ---------------- Kh\u1edfi \u0111\u1ed9ng ---------------- */
    function boot() {
        booted = true;
        get(cfg.me).then(function (m) { me = m && m.authenticated ? m : null; })
            .catch(function () { me = null; })
            .then(function () { return get(cfg.state + '?session_id=' + encodeURIComponent(sid)); })
            .then(function (st) {
                if (st.exists && st.has_request) restore(st); else startFlow(false);
            })
            .catch(function () { startFlow(false); });
    }

    function greeting() {
        var who = me && me.fullname ? me.fullname : 'qu\u00fd kh\u00e1ch';
        botSays('Xin ch\u00e0o ' + esc(who) + '! Charm Grand r\u1ea5t vui \u0111\u01b0\u1ee3c h\u1ed7 tr\u1ee3 b\u1ea1n.');
    }

    function startFlow(silent) {
        if (!silent) greeting();
        post(cfg.flow, { session_id: sid }).then(function (r) {
            if (r.node) showNode(r.node);
            else fallbackMenu();
        }).catch(function () {
            sys('Kh\u00f4ng th\u1ec3 k\u1ebft n\u1ed1i v\u1edbi h\u1ec7 th\u1ed1ng t\u01b0 v\u1ea5n l\u00fac n\u00e0y, vui l\u00f2ng th\u1eed l\u1ea1i sau.');
            var box = node('div', 'cg-chips');
            box.appendChild(chip('Th\u1eed l\u1ea1i', 'ghost', function (b) { lock(box, b); startFlow(true); }));
            el.Body.appendChild(box);
            scrollDown();
        });
    }

    function fallbackMenu() {
        botSays('B\u1ea1n c\u1ea7n Charm Grand h\u1ed7 tr\u1ee3 \u0111i\u1ec1u g\u00ec \u1ea1?');
        var box = node('div', 'cg-chips');
        box.appendChild(chip('Y\u00eau c\u1ea7u t\u01b0 v\u1ea5n', 'ask', function (b) {
            lock(box, b);
            openConsult({ title: 'Y\u00eau c\u1ea7u t\u01b0 v\u1ea5n', options: [{ text: 'G\u1eedi y\u00eau c\u1ea7u' }] });
        }));
        el.Body.appendChild(box);
        scrollDown();
    }

    /* ---------------- Hi\u1ec3n th\u1ecb m\u1ed9t b\u01b0\u1edbc c\u1ee7a k\u1ecbch b\u1ea3n ---------------- */
    function showNode(n, isBack) {
        if (!isBack) stack.push(n);
        setTrail();

        if (n.handoff) { openConsult(n); return; }

        var html;
        if (n.type === 'hinh_anh') {
            var url = safeUrl(n.image_url);
            html = (url ? '<img src="' + esc(url) + '" alt="">' : '<div class="cg-card-ph">Ch\u01b0a c\u00f3 \u1ea3nh</div>') + nl2br(n.content);
        } else if (n.type === 'dich_vu') {
            lastService = n.title || lastService;
            html = '<div class="cg-card-title">' + esc(n.title) + '</div>' +
                '<div class="cg-card-meta">' + esc(n.duration || 0) + ' ph\u00fat \u00b7 ' + money(n.price) + ' \u0111</div>' + nl2br(n.content);
        } else {
            html = nl2br(n.content || n.title);
        }
        botSays(html);

        var box = node('div', 'cg-chips');
        (n.options || []).forEach(function (o) {
            box.appendChild(chip(o.text || 'Ti\u1ebfp t\u1ee5c', '', function (b) { choose(n, o, box, b); }));
        });
        if (!(n.options || []).length) {
            box.appendChild(chip('Y\u00eau c\u1ea7u t\u01b0 v\u1ea5n', 'ask', function (b) {
                lock(box, b);
                openConsult({ title: 'Y\u00eau c\u1ea7u t\u01b0 v\u1ea5n', options: [{ text: 'G\u1eedi y\u00eau c\u1ea7u' }] });
            }));
        }
        if (stack.length > 1) {
            box.appendChild(chip('\u2190 Quay l\u1ea1i', 'ghost', function (b) { lock(box, b); goBack(); }));
        }
        el.Body.appendChild(box);
        scrollDown();
    }

    function choose(n, opt, box, btn) {
        lock(box, btn);
        bubble('me', esc(opt.text), 'B\u1ea1n \u2022 ' + nowTime());
        path.push(opt.text);
        setTrail();
        post(cfg.flow, { session_id: sid, node_id: n.id, option_id: opt.id }).then(function (r) {
            if (r.node) { showNode(r.node); return; }
            botSays('C\u1ea3m \u01a1n b\u1ea1n. B\u1ea1n c\u00f3 th\u1ec3 quay l\u1ea1i ho\u1eb7c g\u1eedi y\u00eau c\u1ea7u \u0111\u1ec3 nh\u00e2n vi\u00ean t\u01b0 v\u1ea5n tr\u1ef1c ti\u1ebfp.');
            var b2 = node('div', 'cg-chips');
            b2.appendChild(chip('Y\u00eau c\u1ea7u t\u01b0 v\u1ea5n', 'ask', function (b) {
                lock(b2, b);
                openConsult({ title: 'Y\u00eau c\u1ea7u t\u01b0 v\u1ea5n', options: [{ text: 'G\u1eedi y\u00eau c\u1ea7u' }] });
            }));
            if (stack.length > 1) b2.appendChild(chip('\u2190 Quay l\u1ea1i', 'ghost', function (b) { lock(b2, b); goBack(); }));
            el.Body.appendChild(b2);
            scrollDown();
        }).catch(function (err) {
            sys('Kh\u00f4ng th\u1ec3 t\u1ea3i b\u01b0\u1edbc ti\u1ebfp theo: ' + err.message);
            path.pop(); setTrail();
        });
    }

    function goBack() {
        if (stack.length < 2) return;
        stack.pop();
        path.pop();
        var prev = stack[stack.length - 1];
        setTrail();
        showNode(prev, true);
    }

    /* ---------------- Y\u00eau c\u1ea7u t\u01b0 v\u1ea5n ---------------- */
    function needOptions() {
        var list = [];
        if (lastService) list.push(lastService);
        NEEDS.forEach(function (x) { if (list.indexOf(x) === -1) list.push(x); });
        return list.map(function (x) { return '<option value="' + esc(x) + '">' + esc(x) + '</option>'; }).join('');
    }
    function roField(label, value) {
        return '<div class="cg-field"><label>' + label + '</label><div class="cg-ro' + (value ? '' : ' empty') + '">' +
            (value ? esc(value) : 'Ch\u01b0a c\u1eadp nh\u1eadt') + '</div></div>';
    }

    function openConsult(n) {
        if (mode === 'waiting') { sys('Y\u00eau c\u1ea7u c\u1ee7a b\u1ea1n \u0111ang ch\u1edd nh\u00e2n vi\u00ean ti\u1ebfp nh\u1eadn.'); return; }
        if (mode === 'live') { sys('B\u1ea1n \u0111ang \u0111\u01b0\u1ee3c nh\u00e2n vi\u00ean h\u1ed7 tr\u1ee3 tr\u1ef1c ti\u1ebfp.'); return; }
        if (mode === 'done') { return; }

        var submitText = (n.options && n.options[0] && n.options[0].text) || 'G\u1eedi y\u00eau c\u1ea7u';
        var form = node('form', 'cg-form');
        form.setAttribute('novalidate', 'novalidate');
        var html = '<h4>' + esc(n.title || 'Y\u00eau c\u1ea7u t\u01b0 v\u1ea5n') + '</h4>';
        if (me) {
            html += '<p class="cg-hint">Th\u00f4ng tin c\u1ee7a b\u1ea1n \u0111\u01b0\u1ee3c l\u1ea5y t\u1eeb t\u00e0i kho\u1ea3n. Ch\u1ecdn nhu c\u1ea7u \u0111\u1ec3 nh\u00e2n vi\u00ean h\u1ed7 tr\u1ee3 nhanh h\u01a1n.</p>' +
                roField('H\u1ecd v\u00e0 t\u00ean', me.fullname) + roField('S\u1ed1 \u0111i\u1ec7n tho\u1ea1i', me.phone) + roField('Email', me.email);
        } else {
            html += '<p class="cg-hint">Vui l\u00f2ng \u0111\u1ec3 l\u1ea1i th\u00f4ng tin \u0111\u1ec3 nh\u00e2n vi\u00ean li\u00ean h\u1ec7 v\u00e0 t\u01b0 v\u1ea5n ri\u00eang cho b\u1ea1n.</p>' +
                '<div class="cg-field"><label>H\u1ecd v\u00e0 t\u00ean *</label><input name="fullname" maxlength="100" autocomplete="name"></div>' +
                '<div class="cg-field"><label>S\u1ed1 \u0111i\u1ec7n tho\u1ea1i *</label><input name="phone" maxlength="20" inputmode="tel" autocomplete="tel"></div>' +
                '<div class="cg-field"><label>Email (kh\u00f4ng b\u1eaft bu\u1ed9c)</label><input name="email" maxlength="100" autocomplete="email"></div>';
        }
        html += '<div class="cg-field"><label>Nhu c\u1ea7u t\u01b0 v\u1ea5n</label><select name="topic">' + needOptions() + '</select></div>' +
            '<p class="cg-hint">B\u1ea1n ch\u1ec9 c\u00f3 th\u1ec3 nh\u1eafn tin tr\u1ef1c ti\u1ebfp sau khi nh\u00e2n vi\u00ean ti\u1ebfp nh\u1eadn y\u00eau c\u1ea7u. Th\u00f4ng tin ch\u1ec9 d\u00f9ng \u0111\u1ec3 h\u1ed7 tr\u1ee3 t\u01b0 v\u1ea5n.</p>' +
            '<p class="cg-error" role="alert"></p>' +
            '<button class="cg-submit" type="submit">' + esc(submitText) + '</button>';
        form.innerHTML = html;
        el.Body.appendChild(form);
        scrollDown();
        var first = form.querySelector('input');
        if (first && isOpen) first.focus();

        form.addEventListener('submit', function (e) {
            e.preventDefault();
            var err = form.querySelector('.cg-error'), btn = form.querySelector('.cg-submit');
            var data = { session_id: sid, topic: form.elements.topic.value };
            if (!me) {
                data.fullname = form.elements.fullname.value.trim();
                data.phone = form.elements.phone.value.trim();
                data.email = form.elements.email.value.trim();
                if (data.fullname.length < 2) { err.textContent = 'Vui l\u00f2ng nh\u1eadp h\u1ecd v\u00e0 t\u00ean.'; return; }
                if (!data.phone && !data.email) { err.textContent = 'Vui l\u00f2ng nh\u1eadp s\u1ed1 \u0111i\u1ec7n tho\u1ea1i ho\u1eb7c email.'; return; }
            }
            err.textContent = '';
            btn.disabled = true;
            post(cfg.consult, data).then(function (r) {
                form.remove();
                enterWaiting(r.request, true);
            }).catch(function (ex) {
                err.textContent = ex.message;
                btn.disabled = false;
            });
        });
    }

    function summaryHtml(r) {
        function row(k, v) { return '<div><span>' + k + '</span><span>' + esc(v || 'Ch\u01b0a cung c\u1ea5p') + '</span></div>'; }
        return row('H\u1ecd v\u00e0 t\u00ean', r.fullname) + row('S\u1ed1 \u0111i\u1ec7n tho\u1ea1i', r.phone) + row('Email', r.email) + row('Nhu c\u1ea7u', r.topic);
    }

    function enterWaiting(r, announce) {
        mode = 'waiting';
        setHeader(TITLE, '\u25cf \u0110ang ch\u1edd nh\u00e2n vi\u00ean ti\u1ebfp nh\u1eadn');
        el.Compose.hidden = true;
        el.Wait.hidden = false;
        el.Ask.hidden = true;
        if (announce) {
            botSays('Y\u00eau c\u1ea7u c\u1ee7a b\u1ea1n \u0111\u00e3 \u0111\u01b0\u1ee3c g\u1eedi. Nh\u00e2n vi\u00ean t\u01b0 v\u1ea5n s\u1ebd ph\u1ea3n h\u1ed3i ngay t\u1ea1i \u0111\u00e2y khi ti\u1ebfp nh\u1eadn.');
            var s = node('div', 'cg-summary', summaryHtml(r || {}));
            el.Body.appendChild(s);
            var box = node('div', 'cg-chips');
            box.appendChild(chip('Quay l\u1ea1i cu\u1ed9c h\u1ed9i tho\u1ea1i', 'ghost', function (b) { lock(box, b); stack = []; path = []; setTrail(); startFlow(true); }));
            el.Body.appendChild(box);
            scrollDown();
        }
        schedulePoll(1500);
    }

    function enterLive(name, quiet) {
        var changed = mode !== 'live' && !quiet;
        mode = 'live';
        staffName = name || 'Nh\u00e2n vi\u00ean t\u01b0 v\u1ea5n';
        setHeader(staffName + ' \u2013 Nh\u00e2n vi\u00ean t\u01b0 v\u1ea5n', '\u25cf \u0110ang h\u1ed7 tr\u1ee3');
        el.Wait.hidden = true;
        el.Ask.hidden = true;
        el.Compose.hidden = false;
        if (changed) {
            sys('Y\u00eau c\u1ea7u \u0111\u00e3 \u0111\u01b0\u1ee3c ti\u1ebfp nh\u1eadn');
            if (isOpen) el.Input.focus();
        }
    }

    function enterDone() {
        if (mode === 'done') return;
        mode = 'done';
        setHeader(TITLE, '\u25cf Cu\u1ed9c t\u01b0 v\u1ea5n \u0111\u00e3 k\u1ebft th\u00fac');
        el.Compose.hidden = true;
        el.Wait.hidden = true;
        el.Ask.hidden = true;
        sys('Cu\u1ed9c t\u01b0 v\u1ea5n \u0111\u00e3 k\u1ebft th\u00fac. C\u1ea3m \u01a1n b\u1ea1n \u0111\u00e3 tin t\u01b0\u1edfng Charm Grand!');
        var box = node('div', 'cg-chips');
        box.appendChild(chip('B\u1eaft \u0111\u1ea7u cu\u1ed9c h\u1ed9i tho\u1ea1i m\u1edbi', 'ask', function (b) { lock(box, b); newConversation(); }));
        el.Body.appendChild(box);
        scrollDown();
    }

    function newConversation() {
        sid = newSid();
        store('cg_session', sid);
        mode = 'bot'; stack = []; path = []; seen = {}; lastService = ''; staffName = '';
        el.Body.innerHTML = '';
        el.Ask.hidden = false;
        setHeader(TITLE, '\u25cf S\u1eb5n s\u00e0ng h\u1ed7 tr\u1ee3 b\u1ea1n');
        setTrail();
        startFlow(false);
    }

    /* ---------------- Kh\u00f4i ph\u1ee5c h\u1ed9i tho\u1ea1i \u0111ang t\u01b0 v\u1ea5n (khi t\u1ea3i l\u1ea1i trang) ---------------- */
    function restore(st) {
        st.messages.forEach(function (m) {
            var meta = m.time;
            if (m.sender === 'Kh\u00e1ch h\u00e0ng') bubble('me', nl2br(m.content), 'B\u1ea1n \u2022 ' + meta);
            else if (m.sender === 'Nh\u00e2n vi\u00ean') { seen[m.id] = 1; bubble('staff', nl2br(m.content), (st.staff_name || 'Nh\u00e2n vi\u00ean') + ' \u2022 ' + meta); }
            else bubble('bot', nl2br(m.content), 'Chatbot \u2022 ' + meta);
        });
        if (st.status === 'Ch\u1edd x\u1eed l\u00fd') {
            mode = 'bot';
            enterWaiting(st.request, false);
        } else if (st.status === '\u0110ang x\u1eed l\u00fd') {
            mode = 'waiting';
            enterLive(st.staff_name, true);
        } else {
            mode = 'live';
            enterDone();
        }
    }

    /* ---------------- Nh\u1eafn tin tr\u1ef1c ti\u1ebfp ---------------- */
    function sendMessage() {
        var text = el.Input.value.trim();
        if (!text || mode !== 'live') return;
        el.Input.value = '';
        bubble('me', nl2br(text), 'B\u1ea1n \u2022 ' + nowTime());
        post(cfg.send, { session_id: sid, message: text }).catch(function (err) {
            sys('Kh\u00f4ng g\u1eedi \u0111\u01b0\u1ee3c tin nh\u1eafn: ' + err.message);
        });
    }

    /* ---------------- C\u1eadp nh\u1eadt \u0111\u1ecbnh k\u1ef3 ---------------- */
    function schedulePoll(delay) {
        clearTimeout(pollTimer);
        if (mode !== 'waiting' && mode !== 'live') return;
        pollTimer = setTimeout(tick, delay == null ? (isOpen ? 3000 : 10000) : delay);
    }

    function tick() {
        if (mode !== 'waiting' && mode !== 'live') return;
        get(cfg.state + '?session_id=' + encodeURIComponent(sid)).then(handleState)
            .catch(function () { /* m\u1ea1ng ch\u1eadp ch\u1eddn: th\u1eed l\u1ea1i \u1edf l\u1ea7n sau */ })
            .then(function () { schedulePoll(); });
    }

    function handleState(st) {
        if (!st.exists || !st.has_request) return;
        if (st.status === '\u0110ang x\u1eed l\u00fd' || st.status === '\u0110\u00e3 ho\u00e0n t\u1ea5t') {
            if (mode === 'waiting') enterLive(st.staff_name);
            else if (staffName !== st.staff_name && st.staff_name) {
                staffName = st.staff_name;
                setHeader(staffName + ' \u2013 Nh\u00e2n vi\u00ean t\u01b0 v\u1ea5n', '\u25cf \u0110ang h\u1ed7 tr\u1ee3');
            }
        }
        st.messages.forEach(function (m) {
            if (m.sender === 'Nh\u00e2n vi\u00ean' && !seen[m.id]) {
                seen[m.id] = 1;
                bubble('staff', nl2br(m.content), (st.staff_name || 'Nh\u00e2n vi\u00ean') + ' \u2022 ' + m.time);
                if (!isOpen) { unread++; updateBadge(); }
            }
        });
        if (st.status === '\u0110\u00e3 ho\u00e0n t\u1ea5t') enterDone();
    }

    /* ---------------- Kh\u1edfi t\u1ea1o ---------------- */
    sid = load('cg_session');
    if (!/^[A-Za-z0-9]{6,10}$/.test(sid)) { sid = newSid(); store('cg_session', sid); }
    build();
    // T\u1eeb trang "L\u1ecbch s\u1eed h\u1ed9i tho\u1ea1i" b\u1ea5m "Ti\u1ebfp t\u1ee5c": t\u1ef1 m\u1edf khung chat (?open_chat=true)
    if (/[?&]open_chat=true/.test(window.location.search)) {
        openWindow();
        try {
            var u = new URL(window.location.href);
            u.searchParams.delete('open_chat');
            window.history.replaceState({}, '', u.pathname + u.search + u.hash);
        } catch (e) { /* b\u1ecf qua */ }
    }

    // Khi ch\u01b0a m\u1edf widget: ki\u1ec3m tra n\u1ec1n \u0111\u1ec3 hi\u1ec7n s\u1ed1 tin m\u1edbi c\u1ee7a nh\u00e2n vi\u00ean tr\u00ean n\u00fat m\u1edf chatbot
    var bgSeen = null;
    function bgTick() {
        if (booted) return;
        get(cfg.state + '?session_id=' + encodeURIComponent(sid)).then(function (st) {
            if (booted || !st.exists || !st.has_request || st.status === '\u0110\u00e3 ho\u00e0n t\u1ea5t') return;
            var staff = st.messages.filter(function (m) { return m.sender === 'Nh\u00e2n vi\u00ean'; });
            if (bgSeen === null) {
                bgSeen = {};
                staff.forEach(function (m) { bgSeen[m.id] = 1; });
            } else {
                staff.forEach(function (m) {
                    if (!bgSeen[m.id]) { bgSeen[m.id] = 1; unread++; updateBadge(); }
                });
            }
            setTimeout(bgTick, 10000);
        }).catch(function () { setTimeout(bgTick, 20000); });
    }
    bgTick();
})();
