# Chuyển bộ kiểm và skill sang máy mới

1. Cài Git và Python 3.9 trở lên.
2. Clone repo public `htgroup-skills-qa`; chạy `python3 -m unittest discover -s tests -v`.
3. Chép riêng các folder skill **private** (`SKILL.md`, `scripts/`, `references/`, `tests/`, các lock/provenance cần thiết) từ máy cũ. Không đẩy chúng vào repo public nếu chưa rà soát/cho phép công khai.
4. Kiểm tra cả 31 tiêu chí bằng `python3 qa.py rubric --stage 3`, xác nhận hash hợp đồng trước khi bắt đầu sáng tác.
5. Với skill bước 3–4 hiện tại, phải dùng bộ script native đi kèm chính skill; bộ kiểm public chỉ kiểm dữ liệu đầu vào dạng normalized. Không thay thế checker gốc bằng bộ mẫu nếu chưa tích hợp và thử nghiệm.
6. Bước 5–8: thu thập **metadata** theo `NORMALIZED_SCHEMAS.md` và kiểm bằng `qa.py`, không gửi dữ liệu phim riêng tư lên GitHub Actions.
7. Nếu thiếu native repo, reviewer, hoặc dữ liệu có thể chứng minh một tiêu chí, giữ trạng thái `NOT_RUN`; tuyệt đối không suy ra `Native PASS` hay `Reviewer PASS`.

Trong dự án riêng, pin commit hash/tag của repo này thay vì tự động lấy `main` mỗi lần chạy. Khi AI đang viết phim, không cập nhật checker giữa phiên; kiểm phiên bản ở đầu và lưu checkpoint cho cả stage.
