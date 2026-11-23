## Đánh giá chất lượng báo cáo chẩn đoán (`n = 30` / 30)

- Mẫu tiền tố hợp lệ (`sample_no = 1..30`): **Có**

| Tiêu chí (thang 0–2) | `n` | Trung bình ± SD | CI95 bootstrap | Phân bố `0 / 1 / 2` |
|---|---:|---:|---|---|
| Đúng root cause | 30 | 0,900 ± 0,845 | [0,600; 1,200] | 12 / 9 / 9 |
| Bằng chứng hợp lệ | 30 | 1,133 ± 0,937 | [0,800; 1,500] | 11 / 4 / 15 |
| Gợi ý xử lý dùng được | 30 | 1,167 ± 0,379 | [1,033; 1,300] | 0 / 25 / 5 |

### Theo trạng thái nhãn thật (`.key.csv`)

| Nhóm | `n` | Root cause | Bằng chứng | Gợi ý xử lý |
|---|---:|---:|---:|---:|
| `labelled` | 15 | 1,000 | 1,200 | 1,133 |
| `no_fault` | 13 | 0,692 | 0,923 | 1,077 |
| `ambiguous` | 2 | 1,500 | 2,000 | 2,000 |

- Đối chiếu `root_cause_score` người chấm vs thang đồ thị khách quan (`n_labelled = 15`): người `1,000` vs khách quan `1,333`, trùng khớp `8/15` (0,533).
