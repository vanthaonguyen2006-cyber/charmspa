/* ==========================================================================
   Widget chatbot tư vấn (khách hàng): chạy theo kịch bản đã thiết kế ở trang Quản lý kịch bản.
   - Nút lựa chọn lấy từ sơ đồ kịch bản (máy chủ quyết định bước tiếp theo).
   - "Yêu cầu tư vấn": khách vãng lai điền form, khách đã đăng nhập được lấy thông tin từ tài khoản.
   - Sau khi gửi: chờ nhân viên tiếp nhận -> mở ô nhắn tin -> kết thúc khi nhân viên hoàn tất.
   ========================================================================== */
(function () {
    'use strict';

    var cfg = window.CG_CONFIG || {};
    var root = document.getElementById('cgWidget');
    if (!root) return;

    var NEEDS = ['Chọn liệu trình', 'Hỗ trợ đặt lịch', 'Chăm sóc sau liệu trình', 'Khác'];
    var TITLE = 'Charm Grand – Trợ lý tư vấn';
    var ICON_CHAT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a8 8 0 0 1-11.6 7.1L4 20l1-4.6A8 8 0 1 1 21 12z"/></svg>';
    var ICON_SEND = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M2.5 11.2 20.8 3.4a.8.8 0 0 1 1.1.9l-3.2 15.4a.8.8 0 0 1-1.2.5l-4.6-3-2.4 2.9a.5.5 0 0 1-.9-.3v-3.9l8-7-9.7 6-4.2-1.5a.8.8 0 0 1 0-1.5z"/></svg>';

    var sid = '';
    var me = null;               // thông tin tài khoản khách (nếu đã đăng nhập)
    var mode = 'bot';            // bot | waiting | live | done
    var isOpen = false, booted = false;
    var stack = [];              // các bước đã hiển thị (để "Quay lại")
    var path = [];               // đường đi khách đã chọn
    var lastService = '';
    var seen = {};               // id tin nhắn nhân viên đã hiển thị
    var staffName = '';
    var unread = 0;
    var pollTimer = null;
    var el = {};

    /* ---------------- Tiện ích ---------------- */
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
            if (!res.ok || d.ok === false) throw new Error(d.error || ('Lỗi máy chủ (' + res.status + ')'));
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
    function store(key, val) { try { window.localStorage.setItem(key, val); } catch (e) { /* bỏ qua */ } }
    function load(key) { try { return window.localStorage.getItem(key) || ''; } catch (e) { return ''; } }
    function node(tag, cls, html) {
        var n = document.createElement(tag);
        if (cls) n.className = cls;
        if (html != null) n.innerHTML = html;
        return n;
    }

    /* ---------------- Dựng giao diện ---------------- */
    function build() {
        root.innerHTML =
            '<button type="button" class="cg-launcher" id="cgLauncher" aria-label="Mở chatbot tư vấn">' + ICON_CHAT +
            '<span>Charm Grand tư vấn</span><i class="cg-badge" id="cgBadge" hidden>0</i></button>' +
            '<section class="cg-window" id="cgWindow" hidden role="dialog" aria-label="Chatbot tư vấn">' +
            '<header class="cg-head"><div><strong id="cgTitle">' + esc(TITLE) + '</strong>' +
            '<small id="cgStatus">● Sẵn sàng hỗ trợ bạn</small></div><div>' +
            '<button type="button" id="cgMin" aria-label="Thu nhỏ">&minus;</button>' +
            '<button type="button" id="cgClose" aria-label="Đóng">&times;</button></div></header>' +
            '<div class="cg-trail" id="cgTrail"></div>' +
            '<div class="cg-body" id="cgBody"></div>' +
            '<footer class="cg-foot">' +
            '<form class="cg-compose" id="cgCompose" hidden autocomplete="off">' +
            '<input id="cgInput" type="text" maxlength="1000" placeholder="Nhập tin nhắn...">' +
            '<button type="submit" aria-label="Gửi">' + ICON_SEND + '</button></form>' +
            '<div class="cg-waitnote" id="cgWait" hidden>Ô nhắn tin sẽ mở khi nhân viên tiếp nhận yêu cầu của bạn.</div>' +
            '<div class="cg-links"><a id="cgHistory" href="' + esc(cfg.history || '#') + '">Lịch sử hội thoại</a>' +
            '<button type="button" id="cgAsk">Yêu cầu tư vấn</button></div></footer></section>';
        ['Launcher', 'Badge', 'Window', 'Title', 'Status', 'Min', 'Close', 'Trail', 'Body', 'Compose', 'Input', 'Wait', 'Ask']
            .forEach(function (k) { el[k] = document.getElementById('cg' + k); });

        el.Launcher.addEventListener('click', openWindow);
        el.Min.addEventListener('click', closeWindow);
        el.Close.addEventListener('click', closeWindow);
        el.Ask.addEventListener('click', function () {
            openConsult({ title: 'Yêu cầu tư vấn', options: [{ text: 'Gửi yêu cầu' }] });
        });
        el.Compose.addEventListener('submit', function (e) { e.preventDefault(); sendMessage(); });
    }

    function scrollDown() { el.Body.scrollTop = el.Body.scrollHeight; }
    function setHeader(title, status) {
        el.Title.textContent = title;
        el.Status.textContent = status;
    }
    function setTrail() { el.Trail.textContent = path.length ? path.join(' → ') : ''; }

    function bubble(kind, html, meta) {
        var m = node('div', 'cg-msg ' + kind);
        if (meta) m.appendChild(node('span', 'cg-meta', esc(meta)));
        m.appendChild(node('div', 'cg-bubble', html));
        el.Body.appendChild(m);
        scrollDown();
        return m;
    }
    function botSays(html) { return bubble('bot', html, 'Chatbot • ' + nowTime()); }
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

    /* ---------------- Mở / đóng ---------------- */
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

    /* ---------------- Khởi động ---------------- */
    function boot() {
        booted = true;
        get(cfg.me).then(function (m) { me = m && m.authenticated ? m : null; })
            .catch(function () { me = null; })
            .then(function () { return get(cfg.state + '?session_id=' + encodeURIComponent(sid)); })
            .then(function (st) {
                if (st.forbidden) {                 // mã phiên cũ thuộc tài khoản khác
                    sid = newSid();
                    store('cg_session', sid);
                    startFlow(false);
                    return;
                }
                if (st.exists && st.has_request) restore(st); else startFlow(false);
            })
            .catch(function () { startFlow(false); });
    }

    function greeting() {
        var who = me && me.fullname ? me.fullname : 'quý khách';
        botSays('Xin chào ' + esc(who) + '! Charm Grand rất vui được hỗ trợ bạn.');
    }

    function startFlow(silent) {
        if (!silent) greeting();
        post(cfg.flow, { session_id: sid }).then(function (r) {
            if (r.session_id && r.session_id !== sid) {   // máy chủ cấp mã phiên mới
                sid = r.session_id;
                store('cg_session', sid);
            }
            if (r.node) showNode(r.node);
            else fallbackMenu();
        }).catch(function () {
            sys('Không thể kết nối với hệ thống tư vấn lúc này, vui lòng thử lại sau.');
            var box = node('div', 'cg-chips');
            box.appendChild(chip('Thử lại', 'ghost', function (b) { lock(box, b); startFlow(true); }));
            el.Body.appendChild(box);
            scrollDown();
        });
    }

    function fallbackMenu() {
        botSays('Bạn cần Charm Grand hỗ trợ điều gì ạ?');
        var box = node('div', 'cg-chips');
        box.appendChild(chip('Yêu cầu tư vấn', 'ask', function (b) {
            lock(box, b);
            openConsult({ title: 'Yêu cầu tư vấn', options: [{ text: 'Gửi yêu cầu' }] });
        }));
        el.Body.appendChild(box);
        scrollDown();
    }

    /* ---------------- Hiển thị một bước của kịch bản ---------------- */
    function showNode(n, isBack) {
        if (!isBack) stack.push(n);
        setTrail();

        if (n.handoff) { openConsult(n); return; }

        var html;
        if (n.type === 'hinh_anh') {
            var url = safeUrl(n.image_url);
            html = (url ? '<img src="' + esc(url) + '" alt="">' : '<div class="cg-card-ph">Chưa có ảnh</div>') + nl2br(n.content);
        } else if (n.type === 'dich_vu') {
            lastService = n.title || lastService;
            html = '<div class="cg-card-title">' + esc(n.title) + '</div>' +
                '<div class="cg-card-meta">' + esc(n.duration || 0) + ' phút · ' + money(n.price) + ' đ</div>' + nl2br(n.content);
        } else {
            html = nl2br(n.content || n.title);
        }
        botSays(html);

        var box = node('div', 'cg-chips');
        (n.options || []).forEach(function (o) {
            box.appendChild(chip(o.text || 'Tiếp tục', '', function (b) { choose(n, o, box, b); }));
        });
        if (!(n.options || []).length) {
            box.appendChild(chip('Yêu cầu tư vấn', 'ask', function (b) {
                lock(box, b);
                openConsult({ title: 'Yêu cầu tư vấn', options: [{ text: 'Gửi yêu cầu' }] });
            }));
        }
        if (stack.length > 1) {
            box.appendChild(chip('← Quay lại', 'ghost', function (b) { lock(box, b); goBack(); }));
        }
        el.Body.appendChild(box);
        scrollDown();
    }

    function choose(n, opt, box, btn) {
        lock(box, btn);
        bubble('me', esc(opt.text), 'Bạn • ' + nowTime());
        path.push(opt.text);
        setTrail();
        post(cfg.flow, { session_id: sid, node_id: n.id, option_id: opt.id }).then(function (r) {
            if (r.session_id && r.session_id !== sid) {
                sid = r.session_id;
                store('cg_session', sid);
            }
            if (r.node) { showNode(r.node); return; }
            botSays('Cảm ơn bạn. Bạn có thể quay lại hoặc gửi yêu cầu để nhân viên tư vấn trực tiếp.');
            var b2 = node('div', 'cg-chips');
            b2.appendChild(chip('Yêu cầu tư vấn', 'ask', function (b) {
                lock(b2, b);
                openConsult({ title: 'Yêu cầu tư vấn', options: [{ text: 'Gửi yêu cầu' }] });
            }));
            if (stack.length > 1) b2.appendChild(chip('← Quay lại', 'ghost', function (b) { lock(b2, b); goBack(); }));
            el.Body.appendChild(b2);
            scrollDown();
        }).catch(function (err) {
            sys('Không thể tải bước tiếp theo: ' + err.message);
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

    /* ---------------- Yêu cầu tư vấn ---------------- */
    function needOptions() {
        var list = [];
        if (lastService) list.push(lastService);
        NEEDS.forEach(function (x) { if (list.indexOf(x) === -1) list.push(x); });
        return list.map(function (x) { return '<option value="' + esc(x) + '">' + esc(x) + '</option>'; }).join('');
    }
    function roField(label, value) {
        return '<div class="cg-field"><label>' + label + '</label><div class="cg-ro' + (value ? '' : ' empty') + '">' +
            (value ? esc(value) : 'Chưa cập nhật') + '</div></div>';
    }

    function openConsult(n) {
        if (mode === 'waiting') { sys('Yêu cầu của bạn đang chờ nhân viên tiếp nhận.'); return; }
        if (mode === 'live') { sys('Bạn đang được nhân viên hỗ trợ trực tiếp.'); return; }
        if (mode === 'done') { return; }

        var submitText = (n.options && n.options[0] && n.options[0].text) || 'Gửi yêu cầu';
        var form = node('form', 'cg-form');
        form.setAttribute('novalidate', 'novalidate');
        var html = '<h4>' + esc(n.title || 'Yêu cầu tư vấn') + '</h4>';
        if (me) {
            html += '<p class="cg-hint">Thông tin của bạn được lấy từ tài khoản. Chọn nhu cầu để nhân viên hỗ trợ nhanh hơn.</p>' +
                roField('Họ và tên', me.fullname) + roField('Số điện thoại', me.phone) + roField('Email', me.email);
        } else {
            html += '<p class="cg-hint">Vui lòng để lại thông tin để nhân viên liên hệ và tư vấn riêng cho bạn.</p>' +
                '<div class="cg-field"><label>Họ và tên *</label><input name="fullname" maxlength="100" autocomplete="name"></div>' +
                '<div class="cg-field"><label>Số điện thoại *</label><input name="phone" maxlength="20" inputmode="tel" autocomplete="tel"></div>' +
                '<div class="cg-field"><label>Email (không bắt buộc)</label><input name="email" maxlength="100" autocomplete="email"></div>';
        }
        html += '<div class="cg-field"><label>Nhu cầu tư vấn</label><select name="topic">' + needOptions() + '</select></div>' +
            '<p class="cg-hint">Bạn chỉ có thể nhắn tin trực tiếp sau khi nhân viên tiếp nhận yêu cầu. Thông tin chỉ dùng để hỗ trợ tư vấn.</p>' +
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
                if (data.fullname.length < 2) { err.textContent = 'Vui lòng nhập họ và tên.'; return; }
                if (!data.phone && !data.email) { err.textContent = 'Vui lòng nhập số điện thoại hoặc email.'; return; }
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
        function row(k, v) { return '<div><span>' + k + '</span><span>' + esc(v || 'Chưa cung cấp') + '</span></div>'; }
        return row('Họ và tên', r.fullname) + row('Số điện thoại', r.phone) + row('Email', r.email) + row('Nhu cầu', r.topic);
    }

    function enterWaiting(r, announce) {
        mode = 'waiting';
        setHeader(TITLE, '● Đang chờ nhân viên tiếp nhận');
        el.Compose.hidden = true;
        el.Wait.hidden = false;
        el.Ask.hidden = true;
        if (announce) {
            botSays('Yêu cầu của bạn đã được gửi. Nhân viên tư vấn sẽ phản hồi ngay tại đây khi tiếp nhận.');
            var s = node('div', 'cg-summary', summaryHtml(r || {}));
            el.Body.appendChild(s);
            var box = node('div', 'cg-chips');
            box.appendChild(chip('Quay lại cuộc hội thoại', 'ghost', function (b) { lock(box, b); stack = []; path = []; setTrail(); startFlow(true); }));
            el.Body.appendChild(box);
            scrollDown();
        }
        schedulePoll(1500);
    }

    function enterLive(name, quiet) {
        var changed = mode !== 'live' && !quiet;
        mode = 'live';
        staffName = name || 'Nhân viên tư vấn';
        setHeader(staffName + ' – Nhân viên tư vấn', '● Đang hỗ trợ');
        el.Wait.hidden = true;
        el.Ask.hidden = true;
        el.Compose.hidden = false;
        if (changed) {
            sys('Yêu cầu đã được tiếp nhận');
            if (isOpen) el.Input.focus();
        }
    }

    function enterDone() {
        if (mode === 'done') return;
        mode = 'done';
        setHeader(TITLE, '● Cuộc tư vấn đã kết thúc');
        el.Compose.hidden = true;
        el.Wait.hidden = true;
        el.Ask.hidden = true;
        sys('Cuộc tư vấn đã kết thúc. Cảm ơn bạn đã tin tưởng Charm Grand!');
        var box = node('div', 'cg-chips');
        box.appendChild(chip('Bắt đầu cuộc hội thoại mới', 'ask', function (b) { lock(box, b); newConversation(); }));
        el.Body.appendChild(box);
        scrollDown();
    }

    function newConversation() {
        sid = newSid();
        store('cg_session', sid);
        mode = 'bot'; stack = []; path = []; seen = {}; lastService = ''; staffName = '';
        el.Body.innerHTML = '';
        el.Ask.hidden = false;
        setHeader(TITLE, '● Sẵn sàng hỗ trợ bạn');
        setTrail();
        startFlow(false);
    }

    /* ---------------- Khôi phục hội thoại đang tư vấn (khi tải lại trang) ---------------- */
    function restore(st) {
        st.messages.forEach(function (m) {
            var meta = m.time;
            if (m.sender === 'Khách hàng') bubble('me', nl2br(m.content), 'Bạn • ' + meta);
            else if (m.sender === 'Nhân viên') { seen[m.id] = 1; bubble('staff', nl2br(m.content), (st.staff_name || 'Nhân viên') + ' • ' + meta); }
            else bubble('bot', nl2br(m.content), 'Chatbot • ' + meta);
        });
        if (st.status === 'Chờ xử lý') {
            mode = 'bot';
            enterWaiting(st.request, false);
        } else if (st.status === 'Đang xử lý') {
            mode = 'waiting';
            enterLive(st.staff_name, true);
        } else {
            mode = 'live';
            enterDone();
        }
    }

    /* ---------------- Nhắn tin trực tiếp ---------------- */
    function sendMessage() {
        var text = el.Input.value.trim();
        if (!text || mode !== 'live') return;
        el.Input.value = '';
        bubble('me', nl2br(text), 'Bạn • ' + nowTime());
        post(cfg.send, { session_id: sid, message: text }).catch(function (err) {
            sys('Không gửi được tin nhắn: ' + err.message);
        });
    }

    /* ---------------- Cập nhật định kỳ ---------------- */
    function schedulePoll(delay) {
        clearTimeout(pollTimer);
        if (mode !== 'waiting' && mode !== 'live') return;
        pollTimer = setTimeout(tick, delay == null ? (isOpen ? 3000 : 10000) : delay);
    }

    function tick() {
        if (mode !== 'waiting' && mode !== 'live') return;
        get(cfg.state + '?session_id=' + encodeURIComponent(sid)).then(handleState)
            .catch(function () { /* mạng chập chờn: thử lại ở lần sau */ })
            .then(function () { schedulePoll(); });
    }

    function handleState(st) {
        if (!st.exists || !st.has_request) return;
        if (st.status === 'Đang xử lý' || st.status === 'Đã hoàn tất') {
            if (mode === 'waiting') enterLive(st.staff_name);
            else if (staffName !== st.staff_name && st.staff_name) {
                staffName = st.staff_name;
                setHeader(staffName + ' – Nhân viên tư vấn', '● Đang hỗ trợ');
            }
        }
        st.messages.forEach(function (m) {
            if (m.sender === 'Nhân viên' && !seen[m.id]) {
                seen[m.id] = 1;
                bubble('staff', nl2br(m.content), (st.staff_name || 'Nhân viên') + ' • ' + m.time);
                if (!isOpen) { unread++; updateBadge(); }
            }
        });
        if (st.status === 'Đã hoàn tất') enterDone();
    }

    /* ---------------- Khởi tạo ---------------- */
    sid = load('cg_session');
    if (!/^[A-Za-z0-9]{6,10}$/.test(sid)) { sid = newSid(); store('cg_session', sid); }
    build();
    // Từ trang "Lịch sử hội thoại" bấm "Tiếp tục": tự mở khung chat (?open_chat=true)
    if (/[?&]open_chat=true/.test(window.location.search)) {
        openWindow();
        try {
            var u = new URL(window.location.href);
            u.searchParams.delete('open_chat');
            window.history.replaceState({}, '', u.pathname + u.search + u.hash);
        } catch (e) { /* bỏ qua */ }
    }

    // Khi chưa mở widget: kiểm tra nền để hiện số tin mới của nhân viên trên nút mở chatbot
    var bgSeen = null;
    function bgTick() {
        if (booted) return;
        get(cfg.state + '?session_id=' + encodeURIComponent(sid)).then(function (st) {
            if (booted || !st.exists || !st.has_request || st.status === 'Đã hoàn tất') return;
            var staff = st.messages.filter(function (m) { return m.sender === 'Nhân viên'; });
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