/* ==========================================================================
   Trang "Ch\u1ec9nh s\u1eeda k\u1ecbch b\u1ea3n": palette k\u00e9o th\u1ea3, b\u1ea3ng thu\u1ed9c t\u00ednh, toolbar, l\u01b0u.
   ========================================================================== */
(function () {
    'use strict';

    document.addEventListener('DOMContentLoaded', function () {
        var cfg = window.FLOW_CONFIG || {};
        var esc = FlowEngine.esc;
        var $ = function (s) { return document.querySelector(s); };

        var vp = $('#fbViewport');
        var panelBody = $('#fbPanelBody');
        var panelSub = $('#fbPanelSub');
        var btnSave = $('#fbSave');
        var dirtyTag = $('#fbDirty');
        var btnUndo = $('#fbUndo'), btnRedo = $('#fbRedo');
        var graph = JSON.parse($('#flow-graph-data').textContent);

        var dirty = false, saving = false, cascade = 0;
        var LINKABLE = ['tin_nhan', 'hinh_anh', 'dich_vu'];       // lo\u1ea1i h\u1ed9p \u0111\u01b0\u1ee3c th\u00eam/x\u00f3a n\u00fat l\u1ef1a ch\u1ecdn
        var PALETTE_TYPES = ['tin_nhan', 'hinh_anh', 'nut_lua_chon', 'chuyen_nhan_vien', 'dich_vu'];

        var engine = new FlowEngine(vp, graph, {
            onSelect: renderPanel,
            onChange: onChange,
            onZoom: function (z) { $('#fbZoomLabel').textContent = Math.round(z * 100) + '%'; },
            onStats: function (s) {
                $('#fbStats').textContent = s.steps + ' b\u01b0\u1edbc' +
                    (s.firstTitle ? ' \u00b7 ' + s.branches + ' nh\u00e1nh t\u1eeb ' + s.firstTitle : '');
            }
        });

        refreshHistoryButtons();
        renderPanel(null);
        if (window.lucide) window.lucide.createIcons();

        /* ---------------- Th\u00f4ng b\u00e1o nh\u1ecf ---------------- */
        function toast(msg, kind) {
            var box = $('#fbToasts'), t = document.createElement('div');
            t.className = 'fb-toast' + (kind ? ' ' + kind : '');
            t.textContent = msg;
            box.appendChild(t);
            setTimeout(function () { t.remove(); }, kind === 'error' ? 6000 : 3200);
        }

        function setDirty(v) {
            dirty = v;
            dirtyTag.classList.toggle('show', v);
        }
        function refreshHistoryButtons() {
            btnUndo.disabled = !engine.canUndo();
            btnRedo.disabled = !engine.canRedo();
        }
        function onChange(reason) {
            setDirty(true);
            refreshHistoryButtons();
            if (reason === 'structure' || reason === 'link') renderPanel(engine.selectedId);
        }

        /* ---------------- B\u1ea3ng thu\u1ed9c t\u00ednh (b\u00ean ph\u1ea3i) ---------------- */
        function nextSelect(node, opt, idx) {
            var html = '<select class="fb-select" data-opt-next="' + idx + '"><option value="">\u2014 Ch\u01b0a n\u1ed1i \u2014</option>';
            engine.graph.nodes.forEach(function (t) {
                if (t.type === 'bat_dau' || t.id === node.id) return;
                html += '<option value="' + esc(t.id) + '"' + (opt.nextId === t.id ? ' selected' : '') + '>' +
                    esc(t.title || '(Ch\u01b0a \u0111\u1eb7t t\u00ean)') + ' \u00b7 ' + FlowEngine.TYPE_LABEL[t.type].toLowerCase() + '</option>';
            });
            return html + '</select>';
        }

        function renderPanel(id) {
            var n = id && engine.node(id);
            if (!n) {
                panelSub.textContent = 'Ch\u1ecdn m\u1ed9t b\u01b0\u1edbc \u0111\u1ec3 ch\u1ec9nh s\u1eeda';
                panelBody.innerHTML = '<div class="fb-empty">B\u1ea5m v\u00e0o m\u1ed9t kh\u1ed1i tr\u00ean s\u01a1 \u0111\u1ed3 \u0111\u1ec3 s\u1eeda n\u1ed9i dung v\u00e0 n\u1ed1i c\u00e1c b\u01b0\u1edbc.<br>' +
                    'K\u00e9o t\u1eeb ch\u1ea5m tr\u00f2n \u1edf cu\u1ed1i m\u1ed7i n\u00fat l\u1ef1a ch\u1ecdn sang m\u1ed9t kh\u1ed1i kh\u00e1c \u0111\u1ec3 n\u1ed1i.</div>';
                setToolsEnabled(false);
                return;
            }
            setToolsEnabled(n.type !== 'bat_dau');
            panelSub.textContent = (n.title || 'B\u01b0\u1edbc') + ' \u00b7 ' + FlowEngine.TYPE_LABEL[n.type].toLowerCase();

            if (n.type === 'bat_dau') {
                var o = n.options[0];
                panelBody.innerHTML =
                    '<div class="fb-note" style="margin-bottom:14px">Kh\u1ed1i "B\u1eaft \u0111\u1ea7u" t\u1ef1 ch\u1ea1y khi kh\u00e1ch m\u1edf chatbot. ' +
                    'Ch\u1ecdn b\u01b0\u1edbc \u0111\u1ea7u ti\u00ean m\u00e0 chatbot s\u1ebd hi\u1ec3n th\u1ecb.</div>' +
                    '<div class="fb-field"><label>B\u01b0\u1edbc \u0111\u1ea7u ti\u00ean</label>' + nextSelect(n, o, 0) + '</div>';
                return;
            }

            var h = '';
            h += '<div class="fb-field"><label>T\u00ean b\u01b0\u1edbc</label>' +
                '<input class="fb-input" data-f="title" value="' + esc(n.title) + '" maxlength="150"></div>';

            if (n.type === 'form') {
                h += '<div class="fb-note" style="margin-bottom:14px">Form thu th\u1eadp: H\u1ecd t\u00ean, S\u1ed1 \u0111i\u1ec7n tho\u1ea1i, Nhu c\u1ea7u t\u01b0 v\u1ea5n. ' +
                    'Kh\u00e1ch \u0111\u00e3 \u0111\u0103ng nh\u1eadp \u0111\u01b0\u1ee3c \u0111i\u1ec1n s\u1eb5n t\u1eeb t\u00e0i kho\u1ea3n.</div>';
            } else {
                var label = n.type === 'hinh_anh' ? 'Ch\u00fa th\u00edch \u1ea3nh' : (n.type === 'dich_vu' ? 'M\u00f4 t\u1ea3 d\u1ecbch v\u1ee5' : 'N\u1ed9i dung tin nh\u1eafn');
                h += '<div class="fb-field"><label>' + label + '</label>' +
                    '<textarea class="fb-textarea" data-f="content" maxlength="1000">' + esc(n.content) + '</textarea></div>';
            }
            if (n.type === 'dich_vu') {
                h += '<div class="fb-row"><div class="fb-field"><label>Th\u1eddi l\u01b0\u1ee3ng (ph\u00fat)</label>' +
                    '<input class="fb-input" type="number" min="0" data-f="duration" value="' + (n.duration || 0) + '"></div>' +
                    '<div class="fb-field"><label>Gi\u00e1 (\u0111)</label>' +
                    '<input class="fb-input" type="number" min="0" step="1000" data-f="price" value="' + (n.price || 0) + '"></div></div>';
            }
            if (n.type === 'hinh_anh') {
                var imgUrl = FlowEngine.safeUrl(n.image_url);
                h += '<div class="fb-field"><label>\u1ea2nh</label><div class="fb-upload" data-drop>' +
                    (imgUrl ? '<img class="fb-upload-prev" alt="" src="' + esc(imgUrl) + '">'
                            : '<div class="fb-upload-empty">Ch\u01b0a c\u00f3 \u1ea3nh \u00b7 k\u00e9o \u1ea3nh v\u00e0o \u0111\u00e2y ho\u1eb7c b\u1ea5m T\u1ea3i \u1ea3nh l\u00ean</div>') +
                    '<div class="fb-upload-actions"><label class="fb-addopt fb-upload-btn">' +
                    (imgUrl ? '\u0110\u1ed5i \u1ea3nh' : 'T\u1ea3i \u1ea3nh l\u00ean') +
                    '<input type="file" hidden data-upload accept="image/jpeg,image/png,image/webp,image/gif"></label>' +
                    (imgUrl ? '<button type="button" class="fb-addopt" data-act="clear-img">X\u00f3a \u1ea3nh</button>' : '') +
                    '</div></div><div class="fb-help" id="fbUpMsg">JPG, PNG, WEBP ho\u1eb7c GIF, t\u1ed1i \u0111a 5 MB.</div></div>' +
                    '<div class="fb-field"><label>Ho\u1eb7c d\u00e1n \u0111\u01b0\u1eddng d\u1eabn \u1ea3nh</label>' +
                    '<input class="fb-input" data-f="image_url" placeholder="https://..." value="' + esc(n.image_url || '') + '"></div>';
            }

            if (n.type !== 'chat_truc_tiep') {
                h += '<div class="fb-field"><label>N\u00fat l\u1ef1a ch\u1ecdn (\u0111i\u1ec1u h\u01b0\u1edbng)</label>';
                n.options.forEach(function (opt, idx) {
                    var fixed = LINKABLE.indexOf(n.type) === -1;
                    h += '<div class="fb-optcard"><div class="fb-optline">' +
                        '<input class="fb-input" data-opt-text="' + idx + '" value="' + esc(opt.text) + '" maxlength="100">' +
                        (fixed ? '' : '<button type="button" class="fb-iconbtn" data-act="del-opt" data-idx="' + idx +
                            '" title="X\u00f3a n\u00fat"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
                            'stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg></button>') +
                        '</div><small>B\u01b0\u1edbc ti\u1ebfp theo</small>' + nextSelect(n, opt, idx) + '</div>';
                });
                if (LINKABLE.indexOf(n.type) !== -1) {
                    h += '<button type="button" class="fb-addopt" data-act="add-opt">+ Th\u00eam n\u00fat l\u1ef1a ch\u1ecdn</button>';
                }
                h += '</div>';
            } else {
                h += '<div class="fb-note">\u0110\u00e2y l\u00e0 b\u01b0\u1edbc cu\u1ed1i: nh\u00e2n vi\u00ean trao \u0111\u1ed5i tr\u1ef1c ti\u1ebfp v\u1edbi kh\u00e1ch trong khung chat.</div>';
            }
            panelBody.innerHTML = h;
        }

        function setToolsEnabled(on) {
            $('#fbDup').disabled = !on;
            $('#fbDel').disabled = !on;
        }

        // G\u00f5 trong b\u1ea3ng thu\u1ed9c t\u00ednh: c\u1eadp nh\u1eadt t\u1ee9c th\u1eddi l\u00ean s\u01a1 \u0111\u1ed3
        panelBody.addEventListener('input', function (e) {
            var t = e.target, id = engine.selectedId;
            if (!id) return;
            if (t.dataset.f) {
                var v = t.value;
                if (t.dataset.f === 'duration' || t.dataset.f === 'price') v = Math.max(0, parseInt(v, 10) || 0);
                var patch = {}; patch[t.dataset.f] = v;
                engine.update(id, patch);
            } else if (t.dataset.optText !== undefined) {
                engine.updateOption(id, parseInt(t.dataset.optText, 10), { text: t.value });
            }
        });
        // R\u1eddi \u00f4 nh\u1eadp / \u0111\u1ed5i l\u1ef1a ch\u1ecdn: ghi v\u00e0o l\u1ecbch s\u1eed (undo)
        panelBody.addEventListener('change', function (e) {
            var t = e.target, id = engine.selectedId;
            if (!id) return;
            if (t.dataset.upload !== undefined) {
                if (t.files && t.files[0]) uploadImage(id, t.files[0]);
                t.value = '';
                return;
            }
            if (t.dataset.optNext !== undefined) {
                engine.updateOption(id, parseInt(t.dataset.optNext, 10), { nextId: t.value });
                engine.commit('link');
            } else {
                engine.commit('text');
            }
        });
        panelBody.addEventListener('click', function (e) {
            var b = e.target.closest('[data-act]'), id = engine.selectedId;
            if (!b || !id) return;
            if (b.dataset.act === 'clear-img') { engine.update(id, { image_url: '' }); engine.commit('structure'); }
            if (b.dataset.act === 'add-opt') engine.addOption(id);
            if (b.dataset.act === 'del-opt') engine.removeOption(id, parseInt(b.dataset.idx, 10));
        });


        /* ---------------- T\u1ea3i \u1ea3nh l\u00ean ---------------- */
        var IMG_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
        function upMsg(text, bad) {
            var m = $('#fbUpMsg');
            if (m) { m.textContent = text; m.style.color = bad ? '#8B1515' : ''; }
        }
        function uploadImage(id, file) {
            if (IMG_TYPES.indexOf(file.type) === -1) { upMsg('Ch\u1ec9 nh\u1eadn \u1ea3nh JPG, PNG, WEBP ho\u1eb7c GIF.', true); return; }
            if (file.size > 5 * 1024 * 1024) { upMsg('\u1ea2nh qu\u00e1 l\u1edbn, t\u1ed1i \u0111a 5 MB.', true); return; }
            upMsg('\u0110ang t\u1ea3i \u1ea3nh l\u00ean...');
            var fd = new FormData();
            fd.append('image', file);
            fetch(cfg.uploadUrl, {
                method: 'POST', credentials: 'same-origin',
                headers: { 'X-CSRFToken': csrf() }, body: fd
            }).then(function (res) {
                return res.json().catch(function () { return null; }).then(function (data) {
                    if (!res.ok || !data || !data.ok) {
                        throw new Error((data && data.error) || ('L\u1ed7i m\u00e1y ch\u1ee7 (' + res.status + ')'));
                    }
                    return data;
                });
            }).then(function (data) {
                if (!engine.node(id)) return;
                engine.update(id, { image_url: data.url });
                engine.commit('structure');
                toast('\u0110\u00e3 t\u1ea3i \u1ea3nh l\u00ean. Nh\u1edb b\u1ea5m L\u01b0u thay \u0111\u1ed5i.');
            }).catch(function (err) {
                upMsg('Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c \u1ea3nh: ' + err.message, true);
            });
        }
        // K\u00e9o th\u1ea3 file \u1ea3nh v\u00e0o khung t\u1ea3i \u1ea3nh
        panelBody.addEventListener('dragover', function (e) {
            if (e.target.closest('[data-drop]')) e.preventDefault();
        });
        panelBody.addEventListener('drop', function (e) {
            if (!e.target.closest('[data-drop]')) return;
            e.preventDefault();
            var f = e.dataTransfer.files && e.dataTransfer.files[0];
            if (f && engine.selectedId) uploadImage(engine.selectedId, f);
        });

        /* ---------------- Th\u00eam node ---------------- */
        function addByType(type, opt) {
            opt = opt || {};
            if (type === 'nut_lua_chon') {
                var tid = opt.dropNode || engine.selectedId, tn = tid && engine.node(tid);
                if (!tn || LINKABLE.indexOf(tn.type) === -1) {
                    toast('H\u00e3y ch\u1ecdn m\u1ed9t kh\u1ed1i Tin nh\u1eafn, H\u00ecnh \u1ea3nh ho\u1eb7c D\u1ecbch v\u1ee5 r\u1ed3i th\u00eam n\u00fat l\u1ef1a ch\u1ecdn.', 'warn');
                    return;
                }
                engine.select(tid);
                engine.addOption(tid);
                toast('\u0110\u00e3 th\u00eam m\u1ed9t n\u00fat l\u1ef1a ch\u1ecdn m\u1edbi v\u00e0o "' + (tn.title || 'b\u01b0\u1edbc') + '".');
                return;
            }
            var x = opt.x, y = opt.y;
            if (x == null) {
                var c = engine.viewCenter();
                x = c.x - 120 + cascade; y = c.y - 60 + cascade;
                cascade = (cascade + 28) % 140;
            }
            var nodes = FlowEngine.createNodes(type, Math.round(x), Math.round(y));
            engine.add(nodes, nodes[0].id);
        }

        document.querySelectorAll('.fb-block').forEach(function (b) {
            b.addEventListener('dragstart', function (e) {
                e.dataTransfer.setData('text/plain', b.dataset.type);
                e.dataTransfer.effectAllowed = 'copy';
            });
            b.addEventListener('click', function () { addByType(b.dataset.type); });
        });
        vp.addEventListener('dragover', function (e) { e.preventDefault(); e.dataTransfer.dropEffect = 'copy'; });
        vp.addEventListener('drop', function (e) {
            e.preventDefault();
            var type = e.dataTransfer.getData('text/plain');
            if (PALETTE_TYPES.indexOf(type) === -1) return;
            var w = engine.toWorld(e.clientX, e.clientY), nd = e.target.closest('.fb-node');
            addByType(type, { x: w.x - 120, y: w.y - 30, dropNode: nd ? nd.dataset.id : null });
        });

        /* ---------------- Toolbar ---------------- */
        var menu = $('#fbAddMenu');
        $('#fbAddBtn').addEventListener('click', function (e) { e.stopPropagation(); menu.classList.toggle('open'); });
        document.addEventListener('click', function () { menu.classList.remove('open'); });
        menu.addEventListener('click', function (e) {
            var b = e.target.closest('[data-type]');
            if (b) { addByType(b.dataset.type); menu.classList.remove('open'); }
        });
        $('#fbDup').addEventListener('click', function () {
            if (engine.selectedId) engine.duplicate(engine.selectedId);
        });
        $('#fbDel').addEventListener('click', deleteSelected);
        btnUndo.addEventListener('click', function () { engine.undo(); });
        btnRedo.addEventListener('click', function () { engine.redo(); });
        $('#fbZoomIn').addEventListener('click', function () { engine.zoomBy(1.15); });
        $('#fbZoomOut').addEventListener('click', function () { engine.zoomBy(1 / 1.15); });
        $('#fbFit').addEventListener('click', function () { engine.fit(); });

        function deleteSelected() {
            var id = engine.selectedId, n = id && engine.node(id);
            if (!n || n.type === 'bat_dau') return;
            engine.remove(id);
        }

        /* ---------------- Ph\u00edm t\u1eaft ---------------- */
        document.addEventListener('keydown', function (e) {
            var tag = (e.target.tagName || '').toLowerCase();
            var typing = tag === 'input' || tag === 'textarea' || tag === 'select';
            var mod = e.ctrlKey || e.metaKey;
            if (mod && e.key.toLowerCase() === 's') { e.preventDefault(); save(); return; }
            if (typing) return;
            if (mod && e.key.toLowerCase() === 'z') { e.preventDefault(); e.shiftKey ? engine.redo() : engine.undo(); }
            else if (mod && e.key.toLowerCase() === 'y') { e.preventDefault(); engine.redo(); }
            else if (e.key === 'Delete') { deleteSelected(); }
        });

        /* ---------------- L\u01b0u ---------------- */
        function csrf() {
            var el = document.querySelector('[name=csrfmiddlewaretoken]');
            return el ? el.value : '';
        }
        function countLoose() {
            var c = 0;
            engine.graph.nodes.forEach(function (n) {
                n.options.forEach(function (o) { if (!o.nextId && n.type !== 'chat_truc_tiep') c++; });
            });
            return c;
        }
        function save() {
            if (saving) return;
            saving = true;
            btnSave.disabled = true;
            fetch(cfg.saveUrl, {
                method: 'POST',
                credentials: 'same-origin',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
                body: JSON.stringify({ graph: engine.getGraph() })
            }).then(function (res) {
                return res.json().catch(function () { return null; }).then(function (data) {
                    if (!res.ok || !data || !data.ok) {
                        throw new Error((data && data.error) || ('L\u1ed7i m\u00e1y ch\u1ee7 (' + res.status + ')'));
                    }
                    return data;
                });
            }).then(function (data) {
                engine.applyServerIds(data.graph);
                setDirty(false);
                toast('\u0110\u00e3 l\u01b0u thay \u0111\u1ed5i k\u1ecbch b\u1ea3n l\u00fac ' + data.saved_at + '.');
                var loose = countLoose();
                if (loose) setTimeout(function () { toast(loose + ' n\u00fat l\u1ef1a ch\u1ecdn ch\u01b0a \u0111\u01b0\u1ee3c n\u1ed1i t\u1edbi b\u01b0\u1edbc n\u00e0o.', 'warn'); }, 600);
            }).catch(function (err) {
                toast('Kh\u00f4ng l\u01b0u \u0111\u01b0\u1ee3c: ' + err.message, 'error');
            }).then(function () {
                saving = false;
                btnSave.disabled = false;
            });
        }
        btnSave.addEventListener('click', save);

        // C\u1ea3nh b\u00e1o khi r\u1eddi trang m\u00e0 ch\u01b0a l\u01b0u
        window.addEventListener('beforeunload', function (e) {
            if (dirty) { e.preventDefault(); e.returnValue = ''; }
        });
        var previewBtn = $('#fbPreview');
        if (previewBtn) previewBtn.addEventListener('click', function (e) {
            if (dirty && !window.confirm('B\u1ea1n c\u00f3 thay \u0111\u1ed5i ch\u01b0a l\u01b0u. Xem tr\u01b0\u1edbc s\u1ebd d\u00f9ng b\u1ea3n \u0111\u00e3 l\u01b0u g\u1ea7n nh\u1ea5t. V\u1eabn ti\u1ebfp t\u1ee5c?')) {
                e.preventDefault();
            }
        });

        window.__flowEngine = engine; // ph\u1ee5c v\u1ee5 g\u1ee1 l\u1ed7i tr\u00ean console
    });
})();
