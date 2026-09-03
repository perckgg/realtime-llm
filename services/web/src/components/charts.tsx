import type { ReactNode } from "react";
import { ink } from "@/theme/tokens";

/**
 * Vỏ tooltip dùng chung. Recharts vẽ tooltip mặc định khá xấu và không theo
 * token của chúng ta, nên mọi biểu đồ đều truyền `content={<VizTooltip .../>}`.
 */
export function TooltipShell({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div
      className="pointer-events-none rounded-md border px-3 py-2 shadow-sm"
      style={{
        borderColor: "var(--color-hairline)",
        background: ink.surface,
        minWidth: 168,
      }}
    >
      <div className="mb-1.5 text-[11px] font-semibold text-ink">{title}</div>
      <div className="space-y-1">{children}</div>
    </div>
  );
}

export function TooltipRow({
  color,
  label,
  value,
  glyph,
}: {
  color?: string;
  label: string;
  value: string;
  glyph?: string;
}) {
  return (
    <div className="flex items-center justify-between gap-4 text-[11.5px]">
      <span className="flex items-center gap-1.5 text-ink-2">
        {color && (
          <span aria-hidden style={{ color }}>
            {glyph ?? "■"}
          </span>
        )}
        {label}
      </span>
      <span className="tabular-nums text-ink">{value}</span>
    </div>
  );
}

/**
 * Legend luôn hiện khi có từ hai series trở lên (một series thì tiêu đề biểu đồ
 * đã gọi tên nó rồi). Mỗi mục có ký hiệu riêng nên danh tính không phụ thuộc màu.
 */
export function Legend({
  items,
  active,
  onToggle,
}: {
  items: { key: string; label: string; color: string; glyph?: string }[];
  active?: Set<string>;
  onToggle?: (key: string) => void;
}) {
  return (
    <ul className="flex flex-wrap items-center gap-x-4 gap-y-1.5">
      {items.map((it) => {
        const on = !active || active.has(it.key);
        const Tag = onToggle ? "button" : "span";
        return (
          <li key={it.key}>
            <Tag
              {...(onToggle ? { type: "button" as const, onClick: () => onToggle(it.key) } : {})}
              className="flex items-center gap-1.5 text-[11.5px] transition-opacity"
              style={{ opacity: on ? 1 : 0.35, color: "var(--color-ink-2)" }}
            >
              <span aria-hidden style={{ color: it.color }}>
                {it.glyph ?? "■"}
              </span>
              {it.label}
            </Tag>
          </li>
        );
      })}
    </ul>
  );
}

export const axisProps = {
  tick: { fill: ink.muted, fontSize: 11 },
  tickLine: false,
  axisLine: { stroke: ink.axis },
} as const;
