# Hình của luận văn

Mỗi hình có ba file cùng tên:

| File | Dùng khi |
|---|---|
| `fig-*.pdf` | **Mặc định.** `\includegraphics` thẳng, không cần TikZ trong preamble. Vector, font Latin Modern. |
| `fig-*.tex` | Muốn hình dùng đúng font của luận văn hoặc cần sửa nội dung: `\input` mã TikZ. |
| `preview-fig-*.png` | Chỉ để xem nhanh trên GitHub; không đưa vào luận văn. |

## Chương 1

| Hình | File | Đặt ở | Label đề xuất |
|---|---|---|---|
| 1.1 Tổng quan hệ thống và khoảng trống ngữ nghĩa | `ch1/fig-tong-quan` | cuối 1.1.1 | `fig:ch1-tong-quan` |

## Chương 4

| Hình | File | Đặt ở | Label đề xuất |
|---|---|---|---|
| Đánh đổi của mở rộng ngữ cảnh theo đồ thị | `ch4/fig-danh-doi` | 4.4.3, trước 4.4.4 | `fig:ch4-danh-doi` |

Cách 1 — dùng PDF:

```latex
\begin{figure}[htbp]
  \centering
  \includegraphics[width=\linewidth]{figures/ch1/fig-tong-quan.pdf}
  \caption{Tổng quan hệ thống: từ cảnh báo của bộ phát hiện bất thường đến dịch vụ gốc.
           Tầng thẩm định CTAV thu hẹp khoảng trống ngữ nghĩa giữa điểm bất thường và sự cố thật.}
  \label{fig:ch1-tong-quan}
\end{figure}

\begin{figure}[htbp]
  \centering
  \includegraphics[width=0.85\linewidth]{figures/ch4/fig-danh-doi.pdf}
  \caption{Đánh đổi khi mở rộng ngữ cảnh theo đồ thị phụ thuộc: (a) truy xuất cục bộ dễ bỏ sót
           sự cố lan truyền; (b) mở rộng 2-hop bắt thêm sự cố nhưng làm judge dễ xác nhận nhầm
           cửa sổ bình thường.}
  \label{fig:ch4-danh-doi}
\end{figure}
```

Cách 2 — dùng mã TikZ (font theo luận văn): thêm vào preamble

```latex
\usepackage{tikz}
\usetikzlibrary{positioning,arrows.meta,fit,backgrounds,calc,decorations.pathreplacing}
```

rồi thay `\includegraphics[...]{...pdf}` bằng `\resizebox{\linewidth}{!}{\input{figures/ch1/fig-tong-quan}}`.

## Dựng lại PDF sau khi sửa `.tex`

```bash
# chạy trong thư mục chứa file .tex (ch1 hoặc ch4)
for f in tong-quan danh-doi; do
  [ -f fig-$f.tex ] || continue
  printf '%s\n' '\documentclass[border=3pt]{standalone}' '\usepackage{fontspec}\setmainfont{Latin Modern Roman}' \
    '\usepackage{tikz}\usetikzlibrary{positioning,arrows.meta,fit,backgrounds,calc,decorations.pathreplacing}' \
    "\\begin{document}\\input{fig-$f}\\end{document}" > _build-$f.tex
  xelatex -interaction=nonstopmode _build-$f.tex && mv _build-$f.pdf fig-$f.pdf
  pdftoppm -png -r 200 -singlefile fig-$f.pdf preview-fig-$f
  rm -f _build-$f.*
done
```
