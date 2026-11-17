/* ==========================================================================
   Trang "Chỉnh sửa kịch bản": Tự động tải Dịch vụ & Giá từ CSDL qua JSON hoặc API
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

        // 1. Đọc danh sách Dịch vụ từ thẻ json_script (nếu có)
        var catalog = { services: [], categories: [] };
        var catalogEl = $('#services-catalog-data');
        if (catalogEl && catalogEl.textContent) {
            try {
                var parsed = JSON.parse(catalogEl.textContent);
                if (parsed && Array.isArray(parsed.services) && parsed.services.length > 0) {
                    catalog = parsed;
                }
            } catch (e) {}
        }

        var dirty = false, saving = false, cascade = 0;
        var LINKABLE = ['tin_nhan', 'hinh_anh', 'dich_vu'];
        var PALETTE_TYPES = ['tin_nhan', 'hinh_anh', 'nut_lua_chon', 'chuyen_nhan_vien', 'dich_vu'];

        var engine = new FlowEngine(vp, graph, {
            onSelect: renderPanel,
            onChange: onChange,
            onZoom: function (z) { $('#fbZoomLabel').textContent = Math.round(z * 100) + '%'; },
            onStats: function (s) {
                $('#fbStats').textContent = s.steps + ' bước' +
                    (s.firstTitle ? ' · ' + s.branches + ' nhánh từ ' + s.firstTitle : '');
            }
        });

        // 2. Nếu catalog chưa có dữ liệu (do view khác render), tự động gọi API lấy từ CSDL
        if (!catalog.services.length) {
            fetch('/chatbot/api/services-catalog/', { credentials: 'same-origin' })
                .then(function (r) { return r.json(); })
                .then(function (data) {
                    if (data && Array.isArray(data.services)) {
                        catalog = data;
                        syncExistingServiceNodes();
                        if (engine.selectedId) renderPanel(engine.selectedId);
                    }
                })
                .catch(function () {});
        } else {
            syncExistingServiceNodes();
        }

        function syncExistingServiceNodes() {
            if (!catalog.services.length || !engine.graph || !Array.isArray(engine.graph.nodes)) return;
            var changed = false;
            engine.graph.nodes.forEach(function (nd) {
                if (nd.type === 'dich_vu') {
                    var matched = catalog.services.find(function (dv) {
                        return (nd.ma_dv && dv.ma_dv === nd.ma_dv) || dv.ten_dich_vu === nd.title;
                    });
                    if (matched) {
                        nd.ma_dv = matched.ma_dv;
                        nd.price = matched.gia_dich_vu;
                        nd.duration = matched.thoi_luong;
                        changed = true;
                    }
                }
            });
            if (changed) engine.render();
        }

        refreshHistoryButtons();
        renderPanel(null);
        if (window.lucide) window.lucide.createIcons();

        /* ---------------- Thông báo nhỏ ---------------- */
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

        /* ---------------- Bảng thuộc tính (bên phải) ---------------- */
        function nextSelect(node, opt, idx) {
            var html = '<select class="fb-select" data-opt-next="' + idx + '"><option value="">— Chưa nối —</option>';
            engine.graph.nodes.forEach(function (t) {
                if (t.type === 'bat_dau' || t.id === node.id) return;
                html += '<option value="' + esc(t.id) + '"' + (opt.nextId === t.id ? ' selected' : '') + '>' +
                    esc(t.title || '(Chưa đặt tên)') + ' · ' + FlowEngine.TYPE_LABEL[t.type].toLowerCase() + '</option>';
            });
            return html + '</select>';
        }

        function renderPanel(id) {
            var n = id && engine.node(id);
            if (!n) {
                panelSub.textContent = 'Chọn một bước để chỉnh sửa';
                panelBody.innerHTML = '<div class="fb-empty">Bấm vào một khối trên sơ đồ để sửa nội dung và nối các bước.<br>' +
                    'Kéo từ chấm tròn ở cuối mỗi nút lựa chọn sang một khối khác để nối.</div>';
                setToolsEnabled(false);
                return;
            }
            setToolsEnabled(n.type !== 'bat_dau');
            panelSub.textContent = (n.title || 'Bước') + ' · ' + FlowEngine.TYPE_LABEL[n.type].toLowerCase();

            if (n.type === 'bat_dau') {
                var o = n.options[0];
                panelBody.innerHTML =
                    '<div class="fb-note" style="margin-bottom:14px">Khối "Bắt đầu" tự chạy khi khách mở chatbot. ' +
                    'Chọn bước đầu tiên mà chatbot sẽ hiển thị.</div>' +
                    '<div class="fb-field"><label>Bước đầu tiên</label>' + nextSelect(n, o, 0) + '</div>';
                return;
            }

            var h = '';

            // NẾU LÀ KHỐI DỊCH VỤ: Thay ô tự gõ Tên dịch vụ bằng Dropdown chọn Dịch vụ có sẵn trong CSDL
            if (n.type === 'dich_vu') {
                h += '<div class="fb-field">' +
                    '<label>Chọn dịch vụ (từ CSDL Quản lý dịch vụ)</label>' +
                    '<select class="fb-select" data-db-service style="font-weight:600">' +
                    '<option value="">-- Chọn dịch vụ có sẵn trong CSDL --</option>';
                catalog.services.forEach(function (dv) {
                    var selected = (n.ma_dv === dv.ma_dv || n.title === dv.ten_dich_vu) ? ' selected' : '';
                    h += '<option value="' + esc(dv.ma_dv) + '"' + selected + '>' +
                        '[' + esc(dv.ma_dv) + '] ' + esc(dv.ten_dich_vu) + ' — ' + FlowEngine.money(dv.gia_dich_vu) + ' đ</option>';
                });
                h += '</select></div>';

                h += '<div class="fb-field"><label>Tên hiển thị trên thẻ</label>' +
                    '<input class="fb-input" data-f="title" value="' + esc(n.title) + '" maxlength="150" placeholder="Tự động điền khi chọn dịch vụ..."></div>';
            } else {
                h += '<div class="fb-field"><label>Tên bước</label>' +
                    '<input class="fb-input" data-f="title" value="' + esc(n.title) + '" maxlength="150"></div>';
            }

            if (n.type === 'form') {
                h += '<div class="fb-note" style="margin-bottom:14px">Form thu thập: Họ tên, Số điện thoại, Nhu cầu tư vấn. ' +
                    'Khách đã đăng nhập được điền sẵn từ tài khoản.</div>';
            } else {
                var label = n.type === 'hinh_anh' ? 'Chú thích ảnh' : (n.type === 'dich_vu' ? 'Mô tả dịch vụ (tự lấy từ CSDL)' : 'Nội dung tin nhắn');
                h += '<div class="fb-field"><label>' + label + '</label>' +
                    '<textarea class="fb-textarea" data-f="content" maxlength="1000">' + esc(n.content) + '</textarea></div>';
            }

            if (n.type === 'dich_vu') {
                h += '<div class="fb-row"><div class="fb-field"><label>Thời lượng (phút)</label>' +
                    '<input class="fb-input" type="number" min="0" data-f="duration" value="' + (n.duration || 0) + '"></div>' +
                    '<div class="fb-field"><label>Giá từ CSDL (đ)</label>' +
                    '<input class="fb-input" type="number" min="0" step="1000" data-f="price" value="' + (n.price || 0) + '"></div></div>';
            }

            if (n.type === 'hinh_anh') {
                var imgUrl = FlowEngine.safeUrl(n.image_url);
                h += '<div class="fb-field"><label>Ảnh</label><div class="fb-upload" data-drop>' +
                    (imgUrl ? '<img class="fb-upload-prev" alt="" src="' + esc(imgUrl) + '">'
                            : '<div class="fb-upload-empty">Chưa có ảnh · kéo ảnh vào đây hoặc bấm Tải ảnh lên</div>') +
                    '<div class="fb-upload-actions"><label class="fb-addopt fb-upload-btn">' +
                    (imgUrl ? 'Đổi ảnh' : 'Tải ảnh lên') +
                    '<input type="file" hidden data-upload accept="image/jpeg,image/png,image/webp,image/gif"></label>' +
                    (imgUrl ? '<button type="button" class="fb-addopt" data-act="clear-img">Xóa ảnh</button>' : '') +
                    '</div></div><div class="fb-help" id="fbUpMsg">JPG, PNG, WEBP hoặc GIF, tối đa 5 MB.</div></div>' +
                    '<div class="fb-field"><label>Hoặc dán đường dẫn ảnh</label>' +
                    '<input class="fb-input" data-f="image_url" placeholder="https://..." value="' + esc(n.image_url || '') + '"></div>';
            }

            if (n.type !== 'chat_truc_tiep') {
                h += '<div class="fb-field"><label>Nút lựa chọn (điều hướng)</label>';
                n.options.forEach(function (opt, idx) {
                    var fixed = LINKABLE.indexOf(n.type) === -1;
                    h += '<div class="fb-optcard"><div class="fb-optline">' +
                        '<input class="fb-input" data-opt-text="' + idx + '" value="' + esc(opt.text) + '" maxlength="100">' +
                        (fixed ? '' : '<button type="button" class="fb-iconbtn" data-act="del-opt" data-idx="' + idx +
                            '" title="Xóa nút"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
                            'stroke-linecap="round" stroke-linejoin="round"><path d="M3 6h18M8 6V4h8v2M6 6l1 14h10l1-14"/></svg></button>') +
                        '</div><small>Bước tiếp theo</small>' + nextSelect(n, opt, idx) + '</div>';
                });

                if (LINKABLE.indexOf(n.type) !== -1) {
                    // Hộp công cụ chọn nút bấm từ CSDL
                    if (catalog.services.length) {
                        h += '<div style="background:#FAF7F2;padding:10px;border-radius:10px;border:1px solid #E8DFD2;margin-bottom:8px">' +
                            '<small style="display:block;font-weight:700;color:#9A7B3E;margin-bottom:6px">★ Thêm nút bấm từ CSDL Dịch vụ:</small>' +
                            '<div style="display:flex;gap:6px;margin-bottom:6px">' +
                            '<select class="fb-select" id="fbQuickServiceOpt" style="flex:1">' +
                            '<option value="">-- Chọn dịch vụ trong CSDL --</option>';
                        catalog.services.forEach(function (dv) {
                            h += '<option value="' + esc(dv.ma_dv) + '">' + esc(dv.ten_dich_vu) + ' (' + FlowEngine.money(dv.gia_dich_vu) + ' đ)</option>';
                        });
                        h += '</select>' +
                            '<button type="button" class="fb-addopt" data-act="add-db-service-opt" style="width:auto;padding:6px 10px;white-space:nowrap;font-size:12px;background:#1a1a1a;color:#fff">+ Thêm nút</button>' +
                            '</div>';

                        if (catalog.categories && catalog.categories.length) {
                            h += '<button type="button" class="fb-addopt" data-act="add-db-categories" style="font-size:12px">' +
                                '+ Thêm các nút Loại dịch vụ từ CSDL (' + catalog.categories.length + ' loại)</button>';
                        }
                        h += '</div>';
                    }

                    h += '<button type="button" class="fb-addopt" data-act="add-opt">+ Thêm nút lựa chọn tự gõ</button>';
                }
                h += '</div>';
            } else {
                h += '<div class="fb-note">Đây là bước cuối: nhân viên trao đổi trực tiếp với khách trong khung chat.</div>';
            }
            panelBody.innerHTML = h;
        }

        function setToolsEnabled(on) {
            $('#fbDup').disabled = !on;
            $('#fbDel').disabled = !on;
        }

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

        panelBody.addEventListener('change', function (e) {
            var t = e.target, id = engine.selectedId;
            if (!id) return;

            // Khi chọn 1 Dịch vụ từ Dropdown CSDL -> Tự động điền Tên, Mô tả, Thời lượng, Giá tiền
            if (t.dataset.dbService !== undefined) {
                var maDv = t.value;
                var dv = catalog.services.find(function (x) { return x.ma_dv === maDv; });
                if (dv) {
                    engine.update(id, {
                        ma_dv: dv.ma_dv,
                        title: dv.ten_dich_vu,
                        content: dv.mo_ta || ('Loại dịch vụ: ' + dv.loai_dich_vu + ' · Thời lượng: ' + dv.thoi_luong + ' phút'),
                        duration: dv.thoi_luong,
                        price: dv.gia_dich_vu
                    });
                    engine.commit('structure');
                    renderPanel(id);
                    toast('Đã cập nhật "' + dv.ten_dich_vu + '" (' + FlowEngine.money(dv.gia_dich_vu) + ' đ) từ CSDL.');
                }
                return;
            }

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
            var n = engine.node(id);
            if (!n) return;

            if (b.dataset.act === 'clear-img') { engine.update(id, { image_url: '' }); engine.commit('structure'); }
            if (b.dataset.act === 'add-opt') engine.addOption(id);
            if (b.dataset.act === 'del-opt') engine.removeOption(id, parseInt(b.dataset.idx, 10));

            if (b.dataset.act === 'add-db-categories') {
                var added = 0;
                catalog.categories.forEach(function (catName) {
                    var exists = n.options.some(function (o) { return o.text === catName; });
                    if (!exists) {
                        n.options.push({ id: FlowEngine.uid('o'), text: catName, nextId: '' });
                        added++;
                    }
                });
                if (added > 0) {
                    engine.refreshNode(id);
                    engine.commit('structure');
                    toast('Đã thêm ' + added + ' nút Loại dịch vụ từ CSDL.');
                } else {
                    toast('Các Loại dịch vụ này đã có sẵn trong bước hiện tại.', 'warn');
                }
            }

            if (b.dataset.act === 'add-db-service-opt') {
                var sel = $('#fbQuickServiceOpt');
                var maDv = sel ? sel.value : '';
                var dv = catalog.services.find(function (x) { return x.ma_dv === maDv; });
                if (!dv) {
                    toast('Hãy chọn 1 dịch vụ trong danh sách trước khi bấm Thêm nút.', 'warn');
                    return;
                }
                var targetNode = engine.graph.nodes.find(function (x) {
                    return x.type === 'dich_vu' && (x.ma_dv === dv.ma_dv || x.title === dv.ten_dich_vu);
                });
                if (!targetNode) {
                    var newNodes = FlowEngine.createNodes('dich_vu', n.x + 300, n.y + (n.options.length * 90));
                    targetNode = newNodes[0];
                    targetNode.ma_dv = dv.ma_dv;
                    targetNode.title = dv.ten_dich_vu;
                    targetNode.content = dv.mo_ta || ('Loại dịch vụ: ' + dv.loai_dich_vu);
                    targetNode.duration = dv.thoi_luong;
                    targetNode.price = dv.gia_dich_vu;
                    engine.graph.nodes.push(targetNode);
                }
                n.options.push({
                    id: FlowEngine.uid('o'),
                    text: dv.ten_dich_vu,
                    nextId: targetNode.id
                });
                engine.render();
                engine.commit('structure');
                toast('Đã thêm nút "' + dv.ten_dich_vu + '" & nối tới hộp giá (' + FlowEngine.money(dv.gia_dich_vu) + ' đ).');
            }
        });

        /* ---------------- Tải ảnh lên ---------------- */
        var IMG_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/gif'];
        function upMsg(text, bad) {
            var m = $('#fbUpMsg');
            if (m) { m.textContent = text; m.style.color = bad ? '#dc3545' : ''; }
        }
        function uploadImage(id, file) {
            if (IMG_TYPES.indexOf(file.type) === -1) { upMsg('Chỉ nhận ảnh JPG, PNG, WEBP hoặc GIF.', true); return; }
            if (file.size > 5 * 1024 * 1024) { upMsg('Ảnh quá lớn, tối đa 5 MB.', true); return; }
            upMsg('Đang tải ảnh lên...');
            var fd = new FormData();
            fd.append('image', file);
            fetch(cfg.uploadUrl, {
                method: 'POST', credentials: 'same-origin',
                headers: { 'X-CSRFToken': csrf() }, body: fd
            }).then(function (res) {
                return res.json().catch(function () { return null; }).then(function (data) {
                    if (!res.ok || !data || !data.ok) {
                        throw new Error((data && data.error) || ('Lỗi máy chủ (' + res.status + ')'));
                    }
                    return data;
                });
            }).then(function (data) {
                if (!engine.node(id)) return;
                engine.update(id, { image_url: data.url });
                engine.commit('structure');
                toast('Đã tải ảnh lên. Nhớ bấm Lưu thay đổi.');
            }).catch(function (err) {
                upMsg('Không tải được ảnh: ' + err.message, true);
            });
        }
        panelBody.addEventListener('dragover', function (e) {
            if (e.target.closest('[data-drop]')) e.preventDefault();
        });
        panelBody.addEventListener('drop', function (e) {
            if (!e.target.closest('[data-drop]')) return;
            e.preventDefault();
            var f = e.dataTransfer.files && e.dataTransfer.files[0];
            if (f && engine.selectedId) uploadImage(engine.selectedId, f);
        });

        /* ---------------- Thêm node ---------------- */
        function addByType(type, opt) {
            opt = opt || {};
            if (type === 'nut_lua_chon') {
                var tid = opt.dropNode || engine.selectedId, tn = tid && engine.node(tid);
                if (!tn || LINKABLE.indexOf(tn.type) === -1) {
                    toast('Hãy chọn một khối Tin nhắn, Hình ảnh hoặc Dịch vụ rồi thêm nút lựa chọn.', 'warn');
                    return;
                }
                engine.select(tid);
                engine.addOption(tid);
                toast('Đã thêm một nút lựa chọn mới vào "' + (tn.title || 'bước') + '".');
                return;
            }
            var x = opt.x, y = opt.y;
            if (x == null) {
                var c = engine.viewCenter();
                x = c.x - 120 + cascade; y = c.y - 60 + cascade;
                cascade = (cascade + 28) % 140;
            }
            var nodes = FlowEngine.createNodes(type, Math.round(x), Math.round(y));
            // Khi kéo hoặc bấm thêm mới khối "Dịch vụ & Giá (CSDL)", tự động gán dịch vụ đầu tiên trong CSDL
            if (type === 'dich_vu' && catalog.services.length) {
                var firstDv = catalog.services[0];
                nodes[0].ma_dv = firstDv.ma_dv;
                nodes[0].title = firstDv.ten_dich_vu;
                nodes[0].content = firstDv.mo_ta || ('Loại dịch vụ: ' + firstDv.loai_dich_vu);
                nodes[0].duration = firstDv.thoi_luong;
                nodes[0].price = firstDv.gia_dich_vu;
            }
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

        /* ---------------- Phím tắt ---------------- */
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

        /* ---------------- Lưu ---------------- */
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
                        throw new Error((data && data.error) || ('Lỗi máy chủ (' + res.status + ')'));
                    }
                    return data;
                });
            }).then(function (data) {
                engine.applyServerIds(data.graph);
                setDirty(false);
                toast('Đã lưu thay đổi kịch bản lúc ' + data.saved_at + '.');
                var loose = countLoose();
                if (loose) setTimeout(function () { toast(loose + ' nút lựa chọn chưa được nối tới bước nào.', 'warn'); }, 600);
            }).catch(function (err) {
                toast('Không lưu được: ' + err.message, 'error');
            }).then(function () {
                saving = false;
                btnSave.disabled = false;
            });
        }
        btnSave.addEventListener('click', save);

        window.addEventListener('beforeunload', function (e) {
            if (dirty) { e.preventDefault(); e.returnValue = ''; }
        });
        var previewBtn = $('#fbPreview');
        if (previewBtn) previewBtn.addEventListener('click', function (e) {
            if (dirty && !window.confirm('Bạn có thay đổi chưa lưu. Xem trước sẽ dùng bản đã lưu gần nhất. Vẫn tiếp tục?')) {
                e.preventDefault();
            }
        });

        window.__flowEngine = engine;
    });
})();