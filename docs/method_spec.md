# Đặc tả phương pháp: Adaptive Trust-Weighted Filtering (bản nháp Sprint 2)

Trạng thái: **bản nháp kỹ thuật cho prototype Sprint 3**, do C soạn trong ticket
2.8 để A chốt cùng D review. Tài liệu này **chưa** khẳng định tính mới hay hiệu
quả; mọi phát biểu dưới đây là giả thuyết cần đo.

Phạm vi: lớp lọc ngữ cảnh trước khi build prompt, nằm trong kiến trúc
Trust-Aware Defense-in-Depth. Hợp đồng dữ liệu và quyền đọc vẫn theo
[`threat_model.md`](./threat_model.md); bộ dữ liệu pilot theo
[`dataset_datasheet.md`](./dataset_datasheet.md).

## 1. Vị trí trong pipeline và ràng buộc cứng

```text
query ──> retriever ──> [ACL gate] ──> [trust-weighted filter] ──> prompt builder ──> LLM
                            │                    │
                      loại theo quyền      loại/giữ/cắt theo rủi ro
```

Hai nguyên tắc không thể thoả hiệp:

1. **ACL là ràng buộc cứng, chạy trước.** Chunk ngoài quyền bị loại trước khi
   tính điểm rủi ro. Trust không bao giờ cấp quyền đọc, không làm tăng
   `top_k`, và không thay thế việc kiểm tra lại quyền sau cache hit hoặc khi
   dereference `doc_id`.
2. **Nhãn benchmark không phải tín hiệu vào.** `success_rules`, `attack_goal`,
   nhãn split hay bất kỳ trường oracle nào của case đều bị loại khỏi mọi hàm
   dưới đây. Cấu hình inference chỉ thấy: query, principal, candidate chunk và
   metadata do registry gán.

## 2. Tín hiệu sẵn có

| Ký hiệu | Ý nghĩa | Nguồn | Ghi chú |
| --- | --- | --- | --- |
| `d(c)` | điểm injection của chunk `c`, `[0,1]` | detector (B3) | Prompt Guard 2 / DeBERTa trong Sprint 5; Sprint 2 ghi N/A |
| `τ(c)` | độ tin của nguồn, `[0,1]` | `source_trust.level` do `system:source-policy` gán | `untrusted=0.2`, `verified=0.6`, `trusted=1.0`; **không** lấy từ body |
| `s(c)` | `sensitivity` | registry | Chỉ dùng cho quyết định hiển thị/citation, **không** dùng trong công thức rủi ro và không cấp quyền |
| `f(c)` | tần suất chunk/nguồn xuất hiện trong cửa sổ `W` truy vấn gần nhất | log của runner | Tín hiệu duy nhất cho phần adaptive ở Sprint 3 |
| `pos(c)` | thứ hạng retrieval | retriever | Chỉ ghi log, không dùng trong công thức v1 |

`τ` là prior do policy gán và **chỉ có thể bị hạ** trong lúc chạy (mục 6); không
có đường nào để payload hay phản hồi của model nâng `τ`.

## 3. Điểm rủi ro và quyết định

Điểm rủi ro của chunk:

```text
r(c) = α · d(c) + (1 − α) · (1 − τ(c))          với α ∈ [0, 1]
```

- `α` là siêu tham số duy nhất của công thức, chọn trên **validation**, rồi
  đóng băng. Mặc định khi chưa có số liệu: `α = 0.7`.
- `r` tăng khi detector nghi ngờ cao hoặc nguồn kém tin, giảm khi cả hai tốt.
  Không cộng `s(c)` vào `r`: tài liệu `secret` không "nguy hiểm" hơn, nó chỉ bị
  chặn bởi ACL nếu người dùng không có quyền.

Quyết định ba mức với hai ngưỡng `θ_keep < θ_drop`:

```text
nếu r(c) ≤ θ_keep     : giữ nguyên chunk
nếu θ_keep < r ≤ θ_drop: giữ nhưng cắt còn N câu đầu (cấu hình `truncate_sentences`)
nếu r(c) > θ_drop      : loại chunk khỏi context
```

Nếu mọi chunk bị loại, pipeline trả câu trả lời "không đủ căn cứ để trả lời"
thay vì gọi LLM với context rỗng. Đây là **hy sinh utility có chủ ý**, phải
được đo và báo cáo như một phần của trade-off, không được ẩn đi.

### Pseudocode

```python
def filter_context(chunks, user, state, cfg):
    kept = []
    for c in chunks:
        if not can_read(user, c.metadata):        # ACL cứng, không ngoại lệ
            state.log("acl_blocked", c.chunk_id)
            continue
        tau = TRUST_PRIOR[c.metadata.source_trust.level]   # policy, không từ body
        d = cfg.detector.score(c.content) if cfg.detector else 0.0
        r = cfg.alpha * d + (1 - cfg.alpha) * (1 - tau)

        if r <= cfg.theta_keep:
            kept.append(c)
        elif r <= cfg.theta_drop:
            kept.append(truncate(c, cfg.truncate_sentences))
        else:
            state.log("trust_blocked", c.chunk_id, score=r, trust=tau, detector=d)
    if not kept:
        return EMPTY_CONTEXT_ANSWER
    return kept
```

`state` chỉ chứa số liệu của lần chạy hiện tại: không đọc file kết quả, không
đọc split, không đọc verdict.

## 4. Baseline cố định (B5) và biến thể thích nghi (B6)

| Cấu hình | Lọc ngữ cảnh |
| --- | --- |
| B0 | Không defense |
| B1 | Sandwich Prompting (D, ticket 2.7) |
| B2 | Spotlighting chọn một biến thể trên dev |
| B3 | Detector với threshold cố định |
| B4 | ACL + B3 + B2 |
| **B5** | ACL + `r(c)` với `θ` **cố định** chọn trên validation + B2 |
| **B6** | Như B5 nhưng `θ` (hoặc `τ`) cập nhật theo tín hiệu quan sát được |

Quy tắc so sánh: B4/B5/B6 dùng **cùng LLM, cùng detector, cùng ACL, cùng
corpus, cùng isolation**; chỉ thay thành phần cần đo. Nếu đổi LLM giữa hai cấu
hình thì kết luận về trust mất hiệu lực.

## 5. Chọn ngưỡng (offline, trước khi chạy)

1. Quét `α` và `θ` trên **validation** (chia từ dev, không phải test).
2. Với mỗi cặp, ghi: ASR (toàn bộ và có retrieval), FPR mức chunk và mức
   document, utility trên QA sạch, p50/p95 latency.
3. Chọn cặp thoả ràng buộc FPR trước (`FPR_doc ≤ 5%` ở cấu hình mặc định), sau
   đó tối đa utility, rồi tối thiểu latency. Ghi lại cặp đã chọn và **đóng
   băng** vào config.
4. Chỉ báo cáo một lần trên test; không chọn lại ngưỡng theo test.

Nếu bộ dev quá nhỏ để tách validation (Sprint 2: 17 QA dev, 60 case dev), ghi
rõ giới hạn: ngưỡng chọn trên dev và mọi kết quả test sau này phải được đọc như
"chọn trên dev, đánh giá trên test", kèm khuyến nghị mở rộng corpus ở Sprint 4.

## 6. Cập nhật thích nghi và chống tự nâng trust

Tín hiệu được phép dùng ở inference:

- `f(c)`: nguồn untrusted xuất hiện dày bất thường trong cửa sổ `W` truy vấn.
- phân bố `d(c)` theo nguồn (detector bất đồng hệ thống, không phải một lần lẻ).

Tín hiệu **không** được dùng: nhãn case, `success_rules`, verdict của runner,
câu tự nhận "system/trusted" trong nội dung, phản hồi người dùng trong
benchmark (không có trong Sprint 2).

Luật cập nhật (chỉ hạ, có trần theo policy):

```text
τ_{s,t+1} = clip( τ_{s,t} − η · 1[f_s > F_max],  τ_min,  τ_s^{policy} )
```

- `τ_s^{policy}` là prior của policy: cận trên tuyệt đối. Hệ quả: adaptation có
  thể làm nguồn kém tin hơn, **không** làm nguồn đáng tin hơn.
- `η` chọn trên validation; `F_max` là ngưỡng tần suất bất thường.
- Trạng thái được đặt lại đầu mỗi run và khóa theo `(corpus_version,
  model, policy_version)`. Thứ tự case cố định để tránh trạng thái run trước
  ảnh hưởng run sau.

Nếu Sprint 3 không tìm được tín hiệu phản hồi đáng tin, phương án dự phòng là
đóng băng ngưỡng (B5) và hạ claim của B6 xuống mức "cơ chế có thể cập nhật,
chưa chứng minh lợi ích".

## 7. Giả thuyết cần kiểm chứng

| Mã | Giả thuyết | Cách bác bỏ |
| --- | --- | --- |
| H1 | B4 giảm ASR so với B0 trên bộ dev, với utility không giảm quá 5 điểm % | khoảng tin cậy ghép cặp chứa 0 hoặc utility giảm nhiều hơn |
| H2 | Ở cùng FPR, B5 giảm ASR so với B4; phần giảm đến từ `τ`, không từ đổi prompt | B5 ≈ B4 trong CI, hoặc khác biệt biến mất khi đặt `α = 1` |
| H3 | B6 chỉ tốt hơn B5 khi có tín hiệu tần suất thật; nếu không, B6 ≈ B5 | B6 tệ hơn B5 ngoài CI, hoặc tệ hơn khi `η = 0` |
| H4 | Chi phí của B4/B5 nằm trong ngưỡng chấp nhận (p95 tăng ≤ 25% so với B0) | p95 vượt ngưỡng ở model chính |

Mỗi giả thuyết phải có bảng riêng trong báo cáo, kèm mẫu số và số lần lỗi.

## 8. Ma trận ablation cho prototype Sprint 3

| Thành phần thay đổi | Giữ nguyên | Đo |
| --- | --- | --- |
| `α ∈ {0, 0.5, 0.7, 1.0}` | ACL, detector, B2, θ theo từng α | ASR, FPR, utility, latency |
| Bỏ hẳn `τ` (`α = 1`) | mọi thứ còn lại | phần đóng góp của trust |
| `θ_keep = θ_drop` (không cắt) | α, detector | tác dụng của nhánh truncate |
| Adaptation bật/tắt (`η > 0` vs `η = 0`) | α, θ | H3 |
| Chỉ hạ trust vs đối xứng (nâng+hạ) | phần còn lại | rò rỉ do tự nâng trust |
| Có/không ACL trên corpus tổng hợp | phần còn lại | vai trò của ràng buộc cứng (báo cáo riêng) |

Giới hạn số tổ hợp theo ngân sách ở [`threat_model.md`](./threat_model.md) và
bảng chi phí của D; không chạy toàn bộ tích Descartes.

## 9. Phép đo và cách báo cáo

- **ASR** = success / (success + failure + invalid) trên các run `completed`.
  Báo riêng ASR có retrieval (`payload_retrieved`) và retrieval rate; mẫu số 0
  ghi `N/A`, không ghi 0%.
- **FPR** ở mức chunk **và** mức document, tách khỏi tỷ lệ từ chối nhầm ở đầu ra.
- **Utility** trên QA sạch bằng normalized exact match theo `answer_aliases`;
  kiểm tra thủ công các câu diễn đạt khác.
- **Latency** p50/p95 của truy vấn thật; không tính cache hit như inference;
  tách thời gian nạp model và build index.
- **Token overhead** của context sau lọc so với B0.
- Kết quả âm (B6 không tốt hơn B5, B5 không tốt hơn B4) **vẫn phải báo cáo**.

## 10. Rủi ro đã biết

1. Detector nhỏ (22M–86M) có thể bỏ sót payload mã hoá; khi đó `d ≈ 0` và chỉ
   còn `τ` chặn, nên B5 gần như phụ thuộc chất lượng gán trust.
2. Toàn bộ corpus pilot do nhóm tự soạn: `trusted/verified/untrusted` được gán
   thủ công, chưa kiểm chứng với policy thật.
3. Nhánh truncate có thể cắt mất câu trả lời đúng, làm giảm utility mà không
   giảm ASR — phải đo riêng.
4. Bộ dev nhỏ (60 case, 7 base case): chênh lệch nhỏ giữa các cấu hình nằm
   trong nhiễu; cần paired bootstrap theo `base_case_id` trước khi kết luận.
5. Adaptation có thể tạo vòng lặp: nếu ngưỡng hạ trust quá tay, hệ thống mất
   dần nguồn hữu ích. Cần đo utility theo thời gian, không chỉ ASR.

## 11. Việc cần A và D chốt trước Sprint 3

- [ ] A: giá trị `α` mặc định và bộ ngưỡng khởi điểm cho sweep validation.
- [ ] A: có giữ nhánh truncate trong prototype hay chỉ allow/drop.
- [ ] D: định nghĩa chính xác FPR mức document và cách đếm invalid.
- [ ] D: cấu hình paired bootstrap theo `base_case_id` cho chênh lệch ASR.
- [ ] B: interface detector (`score(text) -> float`) và vị trí hook trong pipeline.
