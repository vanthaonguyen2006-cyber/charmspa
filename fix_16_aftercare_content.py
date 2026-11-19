# -*- coding: utf-8 -*-
"""Sửa định dạng nội dung của 16 mẫu HDCS được import trước đó.

- Chỉ tác động các mã HD260001..HD260016 nếu gắn đúng DV01..DV16.
- Giữ tên mẫu, dịch vụ, trạng thái và những mẫu ngoài danh sách.
- Tự sao lưu nội dung cũ ra JSON trước khi ghi thật.
- Chạy lại an toàn: nội dung chuẩn rồi thì không ghi thêm.

PowerShell (tại thư mục chứa manage.py):
python manage.py shell -c "exec(compile(open('fix_16_aftercare_content.py', encoding='utf-8').read(), 'fix_16_aftercare_content.py', 'exec'))"
"""
import json
from pathlib import Path
from datetime import datetime
from django.db import transaction
from notifications.models import HuongDanChamSoc

DRY_RUN = False  # Đổi False sau khi kiểm tra kết quả xem thử.

# (mã hướng dẫn, mã dịch vụ, tiêu đề tham khảo, nội dung đã định dạng)
DATA = [('HD260001',
  'DV01',
  'Chăm sóc tóc và da đầu sau gội dưỡng sinh',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Giữ da đầu sạch và khô thoáng theo hướng dẫn của kỹ thuật viên.\n'
  '- Ưu tiên sản phẩm chăm sóc dịu nhẹ đã phù hợp với da đầu của mình.\n'
  '- Nếu thấy kích ứng hoặc khó chịu kéo dài, liên hệ spa để được kiểm tra và tư vấn.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260002',
  'DV02',
  'Lưu ý sau liệu trình massage dành cho thai phụ',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Dành thời gian nghỉ ngơi và theo dõi cảm giác của cơ thể sau buổi trị liệu.\n'
  '- Chỉ thực hiện các hoạt động và tư thế thoải mái, phù hợp với hướng dẫn của bác sĩ đang theo dõi thai '
  'kỳ.\n'
  '- Nếu xuất hiện đau bụng, ra máu, chóng mặt nhiều hoặc dấu hiệu bất thường, liên hệ cơ sở y tế ngay.\n'
  '- Nội dung này chỉ mang tính chăm sóc chung; mọi tư vấn riêng cần được chuyên môn sản khoa xác nhận.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260003',
  'DV03',
  'Chăm sóc cơ thể sau massage truyền thống Việt Nam',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Đứng lên và thay đổi tư thế từ từ nếu cảm thấy thư giãn hoặc hơi choáng.\n'
  '- Uống nước theo nhu cầu thường ngày và nghỉ ngơi khi cần.\n'
  '- Nếu đau tăng, bầm tím nhiều hoặc có triệu chứng bất thường, liên hệ spa hoặc cơ sở y tế.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260004',
  'DV04',
  'Lưu ý sau massage đá nóng',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Để da nghỉ ngơi và tránh tiếp xúc thêm với nguồn nhiệt mạnh ngay sau liệu trình nếu da còn nhạy cảm.\n'
  '- Quan sát vùng da vừa trị liệu; báo cho spa nếu đỏ rát kéo dài, phồng rộp hoặc khó chịu.\n'
  '- Ưu tiên hoạt động nhẹ nhàng theo mức độ thoải mái của cơ thể.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260005',
  'DV05',
  'Chăm sóc sau liệu pháp thảo dược',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Theo dõi phản ứng của da với sản phẩm thảo dược được sử dụng trong liệu trình.\n'
  '- Không tiếp tục sử dụng sản phẩm nếu có biểu hiện kích ứng; liên hệ spa để xác định sản phẩm đã dùng.\n'
  '- Nếu ngứa nhiều, sưng hoặc xuất hiện phản ứng bất thường, tìm hỗ trợ y tế phù hợp.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260006',
  'DV06',
  'Lưu ý sau massage mô sâu',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Có thể có cảm giác ê nhẹ sau buổi trị liệu; nên nghỉ ngơi và vận động theo mức thoải mái.\n'
  '- Tránh cố gắng tập luyện nặng ngay khi còn đau hoặc khó chịu.\n'
  '- Nếu đau dữ dội, tê yếu hoặc triệu chứng kéo dài, liên hệ nhân viên y tế.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260007',
  'DV07',
  'Chăm sóc sau liệu pháp massage Thái',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Chuyển từ tư thế nằm sang ngồi và đứng từ từ.\n'
  '- Vận động nhẹ và dừng nếu thấy đau hoặc căng khó chịu.\n'
  '- Nếu có đau tăng hoặc triệu chứng khác thường sau liệu trình, liên hệ spa để được hỗ trợ.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260008',
  'DV08',
  'Hướng dẫn sau massage Bamboo Cane',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Dành thời gian nghỉ ngơi nếu vùng cơ vừa được tác động còn nhạy cảm.\n'
  '- Theo dõi da và cảm giác cơ thể sau buổi massage.\n'
  '- Thông báo cho spa khi có bầm tím nhiều, đau tăng hoặc bất thường.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260009',
  'DV09',
  'Chăm sóc sau massage tinh dầu',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Nếu da nhạy cảm, hỏi kỹ thuật viên về loại tinh dầu đã sử dụng trong liệu trình.\n'
  '- Tránh tiếp tục dùng sản phẩm gây ngứa, đỏ hoặc khó chịu.\n'
  '- Dành thời gian thư giãn và liên hệ spa nếu có phản ứng da bất thường.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260010',
  'DV10',
  'Chăm sóc sau Swedish Massage',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Nghỉ ngơi và trở lại các hoạt động thường ngày theo cảm giác thoải mái của cơ thể.\n'
  '- Uống nước theo nhu cầu và quan sát cảm giác sau buổi massage.\n'
  '- Nếu đau hoặc khó chịu khác thường, liên hệ spa để được hỗ trợ.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260011',
  'DV11',
  'Lưu ý sau massage vùng cơ thể',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Theo dõi vùng cơ thể đã được tác động và tránh gây áp lực thêm nếu còn ê.\n'
  '- Vận động vừa sức và nghỉ khi cần.\n'
  '- Nếu đau tăng, bầm hoặc khó chịu kéo dài, liên hệ spa hoặc nhân viên y tế.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260012',
  'DV12',
  'Hướng dẫn sau Body Relaxation',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Sau liệu trình, dành thời gian thư giãn và trở lại sinh hoạt bình thường theo nhu cầu.\n'
  '- Nếu cảm thấy choáng khi đứng dậy, nên ngồi nghỉ một lúc trước khi di chuyển.\n'
  '- Liên hệ spa nếu có bất kỳ phản ứng bất thường nào.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260013',
  'DV13',
  'Chăm sóc sau Foot Reflexology',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Đứng lên và đi lại từ từ sau khi hoàn thành massage chân.\n'
  '- Chọn giày dép thoải mái nếu bàn chân còn nhạy cảm.\n'
  '- Nếu đau, sưng hoặc khó chịu kéo dài ở chân, liên hệ spa hoặc cơ sở y tế.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260014',
  'DV14',
  'Chăm sóc da sau Facial Treatment',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Làm sạch và dưỡng ẩm da bằng sản phẩm dịu nhẹ phù hợp với tình trạng da.\n'
  '- Sử dụng biện pháp chống nắng phù hợp khi ra ngoài.\n'
  '- Nếu liệu trình có bước treatment đặc biệt, tuân thủ hướng dẫn riêng đã được kỹ thuật viên tư vấn.\n'
  '- Nếu da kích ứng mạnh hoặc kéo dài, liên hệ spa hoặc bác sĩ da liễu.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260015',
  'DV15',
  'Chăm sóc sau Body Treatment',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Dưỡng ẩm vùng da đã được chăm sóc bằng sản phẩm phù hợp.\n'
  '- Tránh chà xát mạnh hoặc dùng thêm sản phẩm tẩy da chết nếu da còn nhạy cảm.\n'
  '- Theo dõi tình trạng da; liên hệ spa nếu có dấu hiệu kích ứng.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.'),
 ('HD260016',
  'DV16',
  'Lưu ý sau gói chăm sóc toàn diện',
  'LỜI DẶN SAU LIỆU TRÌNH\n'
  '- Các dịch vụ trong gói có thể khác nhau; ưu tiên hướng dẫn trực tiếp của kỹ thuật viên cho từng bước đã '
  'thực hiện.\n'
  '- Cho cơ thể nghỉ ngơi và chăm sóc da bằng sản phẩm phù hợp sau liệu trình.\n'
  '- Nếu có dấu hiệu bất thường ở da hoặc cơ thể, liên hệ spa để kiểm tra và được hướng dẫn.\n'
  '\n'
  'LƯU Ý CHUNG\n'
  'Hướng dẫn chung không thay thế tư vấn cá nhân của chuyên viên hoặc nhân viên y tế khi cần.')]

# Chỉ cho sửa các mẫu cũ do chính bộ import tạo, xác nhận đúng dịch vụ.
updates = []
for ma_hd, ma_dv, title, text in DATA:
    obj = HuongDanChamSoc.objects.filter(pk=ma_hd).first()
    if obj is None:
        print(f'BỎ QUA {ma_hd}: chưa có trong database')
        continue
    if obj.ma_dv_id != ma_dv:
        raise RuntimeError(f'DỪNG: {ma_hd} đang gắn {obj.ma_dv_id}, không phải {ma_dv}. Không cập nhật.')
    if obj.noi_dung != text:
        updates.append((obj, text))
    print(f'{ma_hd} | {ma_dv} | {"CẦN SỬA" if obj.noi_dung != text else "ĐÃ ĐÚNG"} | {title}')

print(f'\nCHẾ ĐỘ: {"XEM THỬ (KHÔNG GHI)" if DRY_RUN else "CẬP NHẬT THẬT"}; cần sửa {len(updates)} mẫu.')
if DRY_RUN:
    print('Mở file, đổi DRY_RUN = False, Ctrl+S rồi chạy lại.')
elif updates:
    # Sao lưu đầy đủ dữ liệu cũ, không chứa thông tin khách hàng.
    backup_file = Path.cwd() / ('aftercare_backup_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.json')
    backup = [dict(ma_hd=obj.pk, ma_dv=obj.ma_dv_id, tieu_de=obj.tieu_de,
                   noi_dung=obj.noi_dung, trang_thai=obj.trang_thai) for obj, _ in updates]
    backup_file.write_text(json.dumps(backup, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Đã sao lưu nội dung cũ vào:', backup_file)
    with transaction.atomic():
        for obj, new_text in updates:
            HuongDanChamSoc.objects.filter(pk=obj.pk, ma_dv_id=obj.ma_dv_id).update(noi_dung=new_text)
    print(f'HOÀN TẤT: cập nhật {len(updates)} mẫu; các trường khác giữ nguyên.')
else:
    print('Không có mẫu nào cần sửa.')
