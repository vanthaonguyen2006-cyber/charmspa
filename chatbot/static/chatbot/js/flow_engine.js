/* ==========================================================================
   FlowEngine - v\u1ebd v\u00e0 ch\u1ec9nh s\u1eeda s\u01a1 \u0111\u1ed3 k\u1ecbch b\u1ea3n chatbot b\u1eb1ng JS thu\u1ea7n + SVG.
   D\u00f9ng chung cho 3 trang: Ch\u1ec9nh s\u1eeda (k\u00e9o th\u1ea3), Chi ti\u1ebft (ch\u1ec9 xem), Xem tr\u01b0\u1edbc.
   ========================================================================== */
(function (global) {
    'use strict';

    var SVG_NS = 'http://www.w3.org/2000/svg';
    var TYPE_LABEL = {
        bat_dau: 'B\u1eaeT \u0110\u1ea6U',
        tin_nhan: 'TIN NH\u1eaeN',
        hinh_anh: 'H\u00ccNH \u1ea2NH',
        dich_vu: 'D\u1ecaCH V\u1ee4',
        form: 'FORM TH\u00d4NG TIN',
        chuyen_nhan_vien: 'CHUY\u1ec2N NH\u00c2N VI\u00caN',
        chat_truc_tiep: 'CHAT TR\u1ef0C TI\u1ebeP'
    };
    var ARROW = '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" ' +
        'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';
    var ZOOM_MIN = 0.3, ZOOM_MAX = 1.6;

    function noop() {}
    function clone(o) { return JSON.parse(JSON.stringify(o)); }
    function uid(prefix) {
        return (prefix || 'n') + '_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    }
    function esc(s) {
        return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) {
            return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
        });
    }
    function money(n) { return Number(n || 0).toLocaleString('vi-VN'); }
    function safeUrl(u) { return /^(https?:\/\/|\/)/.test(u || '') ? u : ''; }
    function bezier(x1, y1, x2, y2) {
        var dx = Math.max(40, Math.abs(x2 - x1) * 0.5);
        return 'M' + x1 + ',' + y1 + ' C' + (x1 + dx) + ',' + y1 + ' ' + (x2 - dx) + ',' + y2 + ' ' + x2 + ',' + y2;
    }

    function normalize(g) {
        g = g && typeof g === 'object' ? clone(g) : {};
        g.nodes = Array.isArray(g.nodes) ? g.nodes : [];
        g.nodes.forEach(function (n) {
            n.id = n.id || uid('n');
            n.type = n.type || 'tin_nhan';
            n.title = n.title || '';
            n.content = n.content || '';
            n.x = Number(n.x) || 0;
            n.y = Number(n.y) || 0;
            n.options = (Array.isArray(n.options) ? n.options : []).map(function (o) {
                return { id: o.id || uid('o'), text: o.text || '', nextId: o.nextId || '' };
            });
        });
        if (!g.nodes.some(function (n) { return n.type === 'bat_dau'; })) {
            g.nodes.unshift({
                id: 'start_node', type: 'bat_dau', title: 'B\u1eaft \u0111\u1ea7u', content: '', x: 20, y: 20,
                options: [{ id: uid('o'), text: '', nextId: '' }]
            });
        }
        return g;
    }

    /* ---------------- T\u1ea1o node m\u1edbi theo lo\u1ea1i ---------------- */
    function createNodes(type, x, y) {
        function base(t, title, content, ox, oy, opts) {
            return {
                id: uid('n'), type: t, title: title, content: content, x: x + ox, y: y + oy,
                options: (opts || []).map(function (o) { return { id: uid('o'), text: o, nextId: '' }; })
            };
        }
        if (type === 'hinh_anh') {
            var img = base('hinh_anh', '\u1ea2nh d\u1ecbch v\u1ee5', 'M\u00f4 t\u1ea3 \u1ea3nh', 0, 0, []);
            img.image_url = '';
            return [img];
        }
        if (type === 'dich_vu') {
            var dv = base('dich_vu', 'T\u00ean d\u1ecbch v\u1ee5', 'M\u00f4 t\u1ea3 ng\u1eafn v\u1ec1 d\u1ecbch v\u1ee5', 0, 0, ['Y\u00eau c\u1ea7u t\u01b0 v\u1ea5n']);
            dv.duration = 60; dv.price = 0;
            return [dv];
        }
        if (type === 'chuyen_nhan_vien') {
            // Chu\u1ed7i 3 h\u1ed9p: Form th\u00f4ng tin -> Ch\u1edd ti\u1ebfp nh\u1eadn -> Chat tr\u1ef1c ti\u1ebfp
            var form = base('form', 'Y\u00eau c\u1ea7u t\u01b0 v\u1ea5n', 'H\u1ecd t\u00ean, S\u1ed1 \u0111i\u1ec7n tho\u1ea1i, Nhu c\u1ea7u t\u01b0 v\u1ea5n', 0, 0, ['G\u1eedi y\u00eau c\u1ea7u']);
            var wait = base('chuyen_nhan_vien', 'Ch\u1edd ti\u1ebfp nh\u1eadn', 'Sau khi g\u1eedi form', 300, 0, ['Khi nh\u00e2n vi\u00ean ti\u1ebfp nh\u1eadn']);
            var chat = base('chat_truc_tiep', 'Nh\u00e2n vi\u00ean ti\u1ebfp nh\u1eadn', 'Nh\u00e2n vi\u00ean t\u01b0 v\u1ea5n \u00b7 M\u1edf \u00f4 nh\u1eadp tin nh\u1eafn', 300, 170, []);
            form.options[0].nextId = wait.id;
            wait.options[0].nextId = chat.id;
            return [form, wait, chat];
        }
        return [base('tin_nhan', 'Tin nh\u1eafn m\u1edbi', 'N\u1ed9i dung ph\u1ea3n h\u1ed3i...', 0, 0, [])];
    }

    /* ======================================================================
       L\u1edbp FlowEngine
       ====================================================================== */
    function FlowEngine(viewport, graph, opts) {
        opts = opts || {};
        this.vp = viewport;
        this.readOnly = !!opts.readOnly;
        this.cb = {
            select: opts.onSelect || noop,
            change: opts.onChange || noop,
            zoom: opts.onZoom || noop,
            stats: opts.onStats || noop
        };
        this.graph = normalize(graph);
        this.selectedId = null;
        this.zoom = 1; this.panX = 0; this.panY = 0;
        this.undoStack = []; this.redoStack = [];
        this.maMap = {};
        this.graph.nodes.forEach(function (n) { if (n.ma_buoc) this.maMap[n.id] = n.ma_buoc; }, this);
        this.snap = this._serialize();
        this.els = {};
        this._build();
        this.render();
        this.fit();
    }

    var P = FlowEngine.prototype;

    P._serialize = function () { return JSON.stringify(this.graph.nodes); };
    P.node = function (id) {
        for (var i = 0; i < this.graph.nodes.length; i++) if (this.graph.nodes[i].id === id) return this.graph.nodes[i];
        return null;
    };
    P.getGraph = function () { return clone(this.graph); };

    /* ---------------- D\u1ef1ng khung ---------------- */
    P._build = function () {
        var vp = this.vp, self = this;
        vp.classList.add('fb-viewport');
        if (this.readOnly) vp.classList.add('is-readonly');
        vp.innerHTML =
            '<div class="fb-world">' +
            '<svg class="fb-links" xmlns="' + SVG_NS + '"><defs>' +
            '<marker id="fbArrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">' +
            '<path d="M0 0L10 5L0 10z" fill="#C4B49C"/></marker>' +
            '<marker id="fbArrowOn" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">' +
            '<path d="M0 0L10 5L0 10z" fill="#8B1515"/></marker></defs><g class="fb-links-g"></g></svg>' +
            '<div class="fb-nodes"></div></div>';
        this.world = vp.querySelector('.fb-world');
        this.gLinks = vp.querySelector('.fb-links-g');
        this.nodesEl = vp.querySelector('.fb-nodes');
        vp.addEventListener('pointerdown', function (e) { self._onVpDown(e); });
        vp.addEventListener('wheel', function (e) { self._onWheel(e); }, { passive: false });
    };

    /* ---------------- V\u1ebd node ---------------- */
    P._makeEl = function (n) {
        var el = document.createElement('div');
        el.className = 'fb-node fb-t-' + n.type + (n.id === this.selectedId ? ' is-selected' : '');
        el.dataset.id = n.id;
        el.style.left = n.x + 'px';
        el.style.top = n.y + 'px';

        if (n.type === 'bat_dau') {
            el.innerHTML = '<div class="fb-opt" data-idx="0"><span class="fb-dot"></span><span>B\u1eaft \u0111\u1ea7u</span><i class="fb-port"></i></div>';
        } else {
            var html = '<div class="fb-node-head"><span class="fb-badge">' + TYPE_LABEL[n.type] + '</span>' +
                '<span class="fb-more">\u00b7\u00b7\u00b7</span></div>' +
                '<div class="fb-title">' + esc(n.title || '(Ch\u01b0a \u0111\u1eb7t t\u00ean)') + '</div>';
            if (n.type === 'dich_vu') {
                html += '<div class="fb-meta">' + esc(n.duration || 0) + ' ph\u00fat \u00b7 ' + money(n.price) + ' \u0111</div>';
            }
            if (n.type === 'hinh_anh') {
                var url = safeUrl(n.image_url);
                html += url
                    ? '<div class="fb-img" style="background-image:url(\'' + esc(url) + '\')"></div>'
                    : '<div class="fb-img">Ch\u01b0a c\u00f3 \u1ea3nh</div>';
            }
            var desc = n.type === 'form' ? 'H\u1ecd t\u00ean \u00b7 S\u1ed1 \u0111i\u1ec7n tho\u1ea1i \u00b7 Nhu c\u1ea7u t\u01b0 v\u1ea5n' : n.content;
            if (desc) html += '<div class="fb-desc">' + esc(desc) + '</div>';
            if (n.options.length) {
                html += '<div class="fb-options">' + n.options.map(function (o, i) {
                    return '<div class="fb-opt" data-idx="' + i + '"><span>' + esc(o.text || '(N\u00fat ch\u01b0a \u0111\u1eb7t t\u00ean)') +
                        '</span>' + ARROW + '<i class="fb-port"></i></div>';
                }).join('') + '</div>';
            }
            el.innerHTML = html + '<i class="fb-in"></i>';
        }
        var self = this;
        el.addEventListener('pointerdown', function (e) { self._onNodeDown(e, n.id); });
        return el;
    };

    P.render = function () {
        this.nodesEl.innerHTML = '';
        this.els = {};
        this.graph.nodes.forEach(function (n) {
            var el = this._makeEl(n);
            this.nodesEl.appendChild(el);
            this.els[n.id] = el;
        }, this);
        this.drawLinks();
        this._stats();
    };

    P.refreshNode = function (id) {
        var n = this.node(id), old = this.els[id];
        if (!n || !old) return;
        var el = this._makeEl(n);
        old.replaceWith(el);
        this.els[id] = el;
        this.drawLinks();
    };

    /* ---------------- \u0110\u01b0\u1eddng n\u1ed1i ---------------- */
    P._portPos = function (id, idx) {
        var nodeEl = this.els[id], n = this.node(id);
        var port = nodeEl && nodeEl.querySelector('.fb-opt[data-idx="' + idx + '"] .fb-port');
        if (!port) return { x: n.x + (nodeEl ? nodeEl.offsetWidth : 240), y: n.y + 20 };
        var x = 0, y = 0, el = port;
        while (el && el !== nodeEl) { x += el.offsetLeft; y += el.offsetTop; el = el.offsetParent; }
        return { x: n.x + x + port.offsetWidth / 2, y: n.y + y + port.offsetHeight / 2 };
    };

    P.drawLinks = function () {
        var g = this.gLinks;
        g.innerHTML = '';
        var sel = this.selectedId;
        this.graph.nodes.forEach(function (n) {
            n.options.forEach(function (o, idx) {
                if (!o.nextId || !this.els[n.id] || !this.els[o.nextId]) return;
                var t = this.node(o.nextId);
                var p1 = this._portPos(n.id, idx);
                var path = document.createElementNS(SVG_NS, 'path');
                var on = sel && (sel === n.id || sel === o.nextId);
                path.setAttribute('class', 'fb-link' + (on ? ' is-on' : ''));
                path.setAttribute('d', bezier(p1.x, p1.y, t.x, t.y + 25));
                path.setAttribute('marker-end', 'url(#' + (on ? 'fbArrowOn' : 'fbArrow') + ')');
                g.appendChild(path);
            }, this);
        }, this);
    };

    /* ---------------- Ch\u1ecdn node ---------------- */
    P._setSel = function (id) {
        this.selectedId = id;
        for (var k in this.els) this.els[k].classList.toggle('is-selected', k === id);
    };
    P.select = function (id) {
        this._setSel(id);
        this.drawLinks();
        this.cb.select(id);
    };

    /* ---------------- T\u1ecda \u0111\u1ed9 & pan/zoom ---------------- */
    P.toWorld = function (cx, cy) {
        var r = this.vp.getBoundingClientRect();
        return { x: (cx - r.left - this.panX) / this.zoom, y: (cy - r.top - this.panY) / this.zoom };
    };
    P.viewCenter = function () {
        var r = this.vp.getBoundingClientRect();
        return this.toWorld(r.left + r.width / 2, r.top + r.height / 2);
    };
    P._applyTransform = function () {
        this.world.style.transform = 'translate(' + this.panX + 'px,' + this.panY + 'px) scale(' + this.zoom + ')';
        this.vp.style.backgroundPosition = this.panX + 'px ' + this.panY + 'px';
        this.vp.style.backgroundSize = (22 * this.zoom) + 'px ' + (22 * this.zoom) + 'px';
        this.cb.zoom(this.zoom);
    };
    P.setZoom = function (z, cx, cy) {
        z = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, z));
        var r = this.vp.getBoundingClientRect();
        if (cx == null) { cx = r.width / 2; cy = r.height / 2; }
        var wx = (cx - this.panX) / this.zoom, wy = (cy - this.panY) / this.zoom;
        this.panX = cx - wx * z;
        this.panY = cy - wy * z;
        this.zoom = z;
        this._applyTransform();
    };
    P.zoomBy = function (f) { this.setZoom(this.zoom * f); };
    P.fit = function () {
        var vw = this.vp.clientWidth, vh = this.vp.clientHeight;
        if (!vw || !vh || !this.graph.nodes.length) { this._applyTransform(); return; }
        var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
        this.graph.nodes.forEach(function (n) {
            var el = this.els[n.id];
            var w = el ? el.offsetWidth : 240, h = el ? el.offsetHeight : 100;
            minX = Math.min(minX, n.x); minY = Math.min(minY, n.y);
            maxX = Math.max(maxX, n.x + w); maxY = Math.max(maxY, n.y + h);
        }, this);
        var padX = 50, padTop = this.readOnly ? 40 : 70, padBottom = 60;
        var bw = maxX - minX, bh = maxY - minY;
        var z = Math.min(1, (vw - padX * 2) / bw, (vh - padTop - padBottom) / bh);
        z = Math.max(ZOOM_MIN, z);
        this.zoom = z;
        this.panX = (vw - bw * z) / 2 - minX * z;
        this.panY = padTop + Math.max(0, (vh - padTop - padBottom - bh * z) / 2) - minY * z;
        this._applyTransform();
    };
    P._onWheel = function (e) {
        e.preventDefault();
        if (e.ctrlKey || e.metaKey) {
            var r = this.vp.getBoundingClientRect();
            var d = Math.max(-60, Math.min(60, e.deltaY));
            this.setZoom(this.zoom * Math.pow(1.0015, -d) * 1, e.clientX - r.left, e.clientY - r.top);
        } else {
            this.panX -= e.deltaX;
            this.panY -= e.deltaY;
            this._applyTransform();
        }
    };

    /* ---------------- K\u00e9o canvas (pan) ---------------- */
    P._onVpDown = function (e) {
        if (e.button !== 0 && e.button !== 1) return;
        if (!this.readOnly && e.target.closest('.fb-node')) return; // node t\u1ef1 x\u1eed l\u00fd
        var self = this, sx = e.clientX, sy = e.clientY, px = this.panX, py = this.panY, moved = false;
        var hitNode = e.target.closest('.fb-node');
        this.vp.classList.add('is-panning');
        function mv(ev) {
            var dx = ev.clientX - sx, dy = ev.clientY - sy;
            if (Math.abs(dx) + Math.abs(dy) > 3) moved = true;
            self.panX = px + dx; self.panY = py + dy;
            self._applyTransform();
        }
        function up() {
            window.removeEventListener('pointermove', mv);
            window.removeEventListener('pointerup', up);
            window.removeEventListener('pointercancel', up);
            self.vp.classList.remove('is-panning');
            if (!moved) self.select(hitNode ? hitNode.dataset.id : null);
        }
        window.addEventListener('pointermove', mv);
        window.addEventListener('pointerup', up);
        window.addEventListener('pointercancel', up);
    };

    /* ---------------- K\u00e9o node / k\u00e9o n\u1ed1i ---------------- */
    P._onNodeDown = function (e, id) {
        if (this.readOnly || e.button !== 0) return;
        e.stopPropagation();
        var portEl = e.target.closest('.fb-port');
        if (portEl) {
            e.preventDefault();
            this._startLink(e, id, portEl.closest('.fb-opt'));
            return;
        }
        this.select(id);
        var self = this, n = this.node(id), el = this.els[id];
        var sx = e.clientX, sy = e.clientY, ox = n.x, oy = n.y, moved = false;
        function mv(ev) {
            var dx = (ev.clientX - sx) / self.zoom, dy = (ev.clientY - sy) / self.zoom;
            if (!moved && Math.abs(dx) + Math.abs(dy) < 3 / self.zoom) return;
            if (!moved) { moved = true; el.classList.add('is-dragging'); }
            n.x = Math.round(ox + dx); n.y = Math.round(oy + dy);
            el.style.left = n.x + 'px'; el.style.top = n.y + 'px';
            self.drawLinks();
        }
        function up() {
            window.removeEventListener('pointermove', mv);
            window.removeEventListener('pointerup', up);
            window.removeEventListener('pointercancel', up);
            el.classList.remove('is-dragging');
            if (moved) self.commit('move');
        }
        window.addEventListener('pointermove', mv);
        window.addEventListener('pointerup', up);
        window.addEventListener('pointercancel', up);
    };

    P._nodeAt = function (ev) {
        var el = document.elementFromPoint(ev.clientX, ev.clientY);
        var nd = el && el.closest && el.closest('.fb-node');
        return nd && this.vp.contains(nd) ? nd.dataset.id : null;
    };

    P._startLink = function (e, id, optEl) {
        var self = this, n = this.node(id), idx = parseInt(optEl.dataset.idx, 10), opt = n.options[idx];
        if (!opt) return;
        this.select(id);
        var p1 = this._portPos(id, idx);
        var tmp = document.createElementNS(SVG_NS, 'path');
        tmp.setAttribute('class', 'fb-link fb-link-temp');
        this.gLinks.appendChild(tmp);
        this.vp.classList.add('is-linking');
        var hover = null;
        function setHover(tid) {
            if (hover === tid) return;
            if (hover && self.els[hover]) self.els[hover].classList.remove('is-drop');
            hover = tid;
            if (hover && self.els[hover]) self.els[hover].classList.add('is-drop');
        }
        function valid(tid) { return tid && tid !== id && self.node(tid) && self.node(tid).type !== 'bat_dau'; }
        function mv(ev) {
            var w = self.toWorld(ev.clientX, ev.clientY);
            tmp.setAttribute('d', bezier(p1.x, p1.y, w.x, w.y));
            var t = self._nodeAt(ev);
            setHover(valid(t) ? t : null);
        }
        function up(ev) {
            window.removeEventListener('pointermove', mv);
            window.removeEventListener('pointerup', up);
            window.removeEventListener('pointercancel', up);
            self.vp.classList.remove('is-linking');
            var t = self._nodeAt(ev);
            setHover(null);
            tmp.remove();
            if (valid(t) && opt.nextId !== t) {
                opt.nextId = t;
                self.drawLinks();
                self.commit('link');
            }
        }
        window.addEventListener('pointermove', mv);
        window.addEventListener('pointerup', up);
        window.addEventListener('pointercancel', up);
    };

    /* ---------------- L\u1ecbch s\u1eed (undo / redo) ---------------- */
    P.commit = function (reason) {
        var now = this._serialize();
        if (now === this.snap) return;
        this.undoStack.push(this.snap);
        if (this.undoStack.length > 100) this.undoStack.shift();
        this.redoStack = [];
        this.snap = now;
        this._stats();
        this.cb.change(reason || 'text');
    };
    P._restore = function (s) {
        var self = this;
        this.snap = s;
        this.graph.nodes = JSON.parse(s);
        this.graph.nodes.forEach(function (n) { if (self.maMap[n.id]) n.ma_buoc = self.maMap[n.id]; });
        if (this.selectedId && !this.node(this.selectedId)) this.selectedId = null;
        this.render();
        this.cb.change('structure');
    };
    P.undo = function () {
        if (!this.undoStack.length) return false;
        this.redoStack.push(this.snap);
        this._restore(this.undoStack.pop());
        return true;
    };
    P.redo = function () {
        if (!this.redoStack.length) return false;
        this.undoStack.push(this.snap);
        this._restore(this.redoStack.pop());
        return true;
    };
    P.canUndo = function () { return this.undoStack.length > 0; };
    P.canRedo = function () { return this.redoStack.length > 0; };

    /* Sau khi l\u01b0u, server g\u00e1n m\u00e3 b\u01b0\u1edbc (ma_buoc) cho node m\u1edbi */
    P.applyServerIds = function (serverGraph) {
        var self = this;
        (serverGraph.nodes || []).forEach(function (sn) {
            var n = self.node(sn.id);
            if (n && sn.ma_buoc) { n.ma_buoc = sn.ma_buoc; self.maMap[sn.id] = sn.ma_buoc; }
        });
        this.snap = this._serialize();
    };

    /* ---------------- Thao t\u00e1c ch\u1ec9nh s\u1eeda ---------------- */
    P.add = function (nodes, selectId) {
        nodes.forEach(function (n) {
            this.graph.nodes.push(n);
            var el = this._makeEl(n);
            this.nodesEl.appendChild(el);
            this.els[n.id] = el;
        }, this);
        if (selectId) this._setSel(selectId);
        this.drawLinks();
        this.commit('structure');
        if (selectId) this.cb.select(selectId);
    };
    P.remove = function (id) {
        var n = this.node(id);
        if (!n || n.type === 'bat_dau') return false;
        this.graph.nodes = this.graph.nodes.filter(function (x) { return x.id !== id; });
        this.graph.nodes.forEach(function (x) {
            x.options.forEach(function (o) { if (o.nextId === id) o.nextId = ''; });
        });
        if (this.selectedId === id) this.selectedId = null;
        this.render();
        this.commit('structure');
        if (this.selectedId === null) this.cb.select(null);
        return true;
    };
    P.duplicate = function (id) {
        var n = this.node(id);
        if (!n || n.type === 'bat_dau') return null;
        var c = clone(n);
        c.id = uid('n'); c.x += 40; c.y += 40;
        c.title = (n.title || '') + ' (b\u1ea3n sao)';
        delete c.ma_buoc;
        c.options.forEach(function (o) { o.id = uid('o'); });
        this.add([c], c.id);
        return c.id;
    };
    P.update = function (id, patch) {            // c\u1eadp nh\u1eadt t\u1ee9c th\u1eddi (ch\u01b0a ghi l\u1ecbch s\u1eed)
        var n = this.node(id);
        if (!n) return;
        for (var k in patch) n[k] = patch[k];
        this.refreshNode(id);
    };
    P.updateOption = function (id, idx, patch) { // c\u1eadp nh\u1eadt t\u1ee9c th\u1eddi n\u00fat l\u1ef1a ch\u1ecdn
        var n = this.node(id);
        if (!n || !n.options[idx]) return;
        for (var k in patch) n.options[idx][k] = patch[k];
        this.refreshNode(id);
    };
    P.addOption = function (id, text) {
        var n = this.node(id);
        if (!n) return;
        n.options.push({ id: uid('o'), text: text || 'L\u1ef1a ch\u1ecdn m\u1edbi', nextId: '' });
        this.refreshNode(id);
        this.commit('structure');
    };
    P.removeOption = function (id, idx) {
        var n = this.node(id);
        if (!n || !n.options[idx]) return;
        n.options.splice(idx, 1);
        this.refreshNode(id);
        this.commit('structure');
    };

    /* ---------------- Th\u1ed1ng k\u00ea ---------------- */
    P._stats = function () {
        var start = this.graph.nodes.filter(function (n) { return n.type === 'bat_dau'; })[0];
        var first = start && start.options[0] && this.node(start.options[0].nextId);
        this.cb.stats({
            steps: this.graph.nodes.length,
            branches: first ? first.options.length : 0,
            firstTitle: first ? first.title : ''
        });
    };

    FlowEngine.TYPE_LABEL = TYPE_LABEL;
    FlowEngine.createNodes = createNodes;
    FlowEngine.esc = esc;
    FlowEngine.uid = uid;
    FlowEngine.money = money;
    FlowEngine.safeUrl = safeUrl;
    global.FlowEngine = FlowEngine;
})(window);
