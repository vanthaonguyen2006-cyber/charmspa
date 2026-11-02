# AGENTS.md - CHARM SPA GRAND

## 1. THÔNG TIN DỰ ÁN

Tên dự án: Website chăm sóc khách hàng Charm Spa Grand.

Mục tiêu:
Xây dựng website hỗ trợ khách hàng tìm hiểu dịch vụ spa, đặt lịch, quản lý tài khoản, tích lũy điểm thành viên và chăm sóc khách hàng.

Công nghệ:
- Backend: Python, Django.
- Database: SQLite trong môi trường phát triển hiện tại.
- Frontend: HTML, CSS, JavaScript, Bootstrap nếu dự án đang sử dụng.
- Authentication: Django Authentication và Django User.

## 2. CÁC CHỨC NĂNG NGHIỆP VỤ

Hệ thống có các nhóm chức năng:

- Trang chủ và giới thiệu spa.
- Quản lý tài khoản.
- Đăng nhập, đăng xuất và phân quyền.
- Quản lý khách hàng.
- Quản lý nhân viên.
- Quản lý dịch vụ.
- Đặt lịch và quản lý lịch hẹn.
- Quản lý lịch sử sử dụng dịch vụ.
- Tích lũy điểm và xếp hạng thành viên.
- Chăm sóc khách hàng.
- Quản trị hệ thống.

Chỉ triển khai những chức năng phù hợp với cấu trúc và yêu cầu thực tế của dự án.

## 3. QUY TẮC LẬP TRÌNH

- Đọc code hiện tại trước khi sửa.
- Tận dụng model, view, form và template đã có.
- Không tạo model trùng lặp.
- Không tạo ứng dụng Django mới nếu chưa thực sự cần thiết.
- Không thay đổi tên bảng, tên trường hoặc khóa ngoại tùy tiện.
- Sử dụng Django ORM để thao tác cơ sở dữ liệu.
- Tuân thủ cấu trúc MVC theo cách tổ chức của Django.
- Tách biệt logic xử lý, giao diện HTML, CSS và JavaScript.
- Sử dụng Django Authentication để quản lý đăng nhập.
- Kiểm tra quyền truy cập ở phía server.
- Sử dụng CSRF protection cho các form.
- Sử dụng POST đối với các thao tác thay đổi dữ liệu.

## 4. QUY TẮC GIAO DIỆN

- Giữ phong cách sang trọng, hiện đại, phù hợp với thương hiệu spa.
- Ưu tiên màu sắc và bố cục thống nhất giữa các trang.
- Tái sử dụng base template và component hiện có.
- Không tự ý thay đổi giao diện các trang không liên quan.
- Đảm bảo giao diện hoạt động trên máy tính và điện thoại.

## 5. QUY TẮC CƠ SỞ DỮ LIỆU

- Phải kiểm tra model hiện tại trước khi thêm hoặc sửa trường.
- Không tự ý xóa dữ liệu.
- Không tự ý xóa database.
- Không chạy migration có khả năng làm mất dữ liệu khi chưa được phê duyệt.
- Kiểm tra quan hệ ForeignKey và OneToOneField.
- Ưu tiên bảo vệ dữ liệu liên quan bằng on_delete phù hợp với nghiệp vụ.

## 6. QUY TRÌNH LÀM VIỆC

Khi nhận yêu cầu mới:

1. Đọc các file liên quan.
2. Giải thích cách chức năng hiện tại đang hoạt động.
3. Xác định những file cần chỉnh sửa.
4. Đưa ra kế hoạch thực hiện.
5. Thực hiện đúng phạm vi yêu cầu.
6. Kiểm tra lỗi và chạy Django system check.
7. Kiểm tra các chức năng liên quan để tránh phát sinh lỗi.
8. Báo cáo những file đã thêm, sửa và kết quả kiểm tra.

## 7. NGUYÊN TẮC QUAN TRỌNG

- Không tự ý viết lại toàn bộ dự án.
- Không sửa những phần không được yêu cầu.
- Không tạo dữ liệu giả trong database thật.
- Không ghi đè file cấu hình môi trường hoặc thông tin bí mật.
- Không tự ý thay đổi kiến trúc đã được thống nhất.
- Khi thiếu thông tin, phải hỏi lại thay vì tự suy đoán.
- Code phải dễ đọc, dễ hiểu và phù hợp với trình độ sinh viên.