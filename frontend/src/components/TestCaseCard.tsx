import { useState } from "react";
import { Tag } from "antd";
import { DownOutlined } from "@ant-design/icons";
import type { TestCaseItem } from "../services/api";
import "./TestCaseCard.css";

interface TestCaseCardProps {
  cases: TestCaseItem[];
  searchText?: string;
  // Edit mode props
  editable?: boolean;
  selectedIds?: Set<string>;
  onToggleSelect?: (caseId: string) => void;
  onEdit?: (tc: TestCaseItem) => void;
  onDelete?: (tc: TestCaseItem) => void;
}

interface ParsedSegment {
  label: "前置" | "操作" | "预期";
  text: string;
  isError: boolean;
}

function parseSummary(summary: string): { title: string; segments: ParsedSegment[] } {
  const colonIdx = summary.indexOf("：");
  const title = colonIdx > -1 ? summary.slice(0, colonIdx) : summary.slice(0, 60);
  const body = colonIdx > -1 ? summary.slice(colonIdx + 1) : "";

  const parts = body.split(" → ");
  const labels: Array<"前置" | "操作" | "预期"> = ["前置", "操作", "预期"];
  const segments: ParsedSegment[] = parts.map((text, i) => ({
    label: labels[i] ?? "操作",
    text: text.trim(),
    isError:
      i === 2 &&
      (text.includes("错误") ||
        text.includes("失败") ||
        text.includes("异常") ||
        text.includes("提示")),
  }));

  return { title, segments };
}

function highlightText(text: string, query: string): React.ReactNode {
  if (!query) return text;
  const idx = text.toLowerCase().indexOf(query.toLowerCase());
  if (idx === -1) return text;
  return (
    <>
      {text.slice(0, idx)}
      <mark>{text.slice(idx, idx + query.length)}</mark>
      {text.slice(idx + query.length)}
    </>
  );
}

const PRIORITY_CLASS: Record<string, string> = {
  P0: "p0",
  P1: "p1",
  P2: "p2",
  P3: "p3",
};

export function TestCaseCard({
  cases,
  searchText,
  editable = false,
  selectedIds,
  onToggleSelect,
  onEdit,
  onDelete,
}: TestCaseCardProps) {
  const [expandedIndex, setExpandedIndex] = useState<number | null>(null);

  return (
    <div className="testcase-card-list">
      {cases.map((tc, i) => {
        const { title, segments } = parseSummary(tc.summary);
        const isExpanded = expandedIndex === i;

        return (
          <div key={`${tc.summary}-${i}`}>
            <div
              className={`testcase-card-row${isExpanded ? " expanded" : ""}`}
              onClick={() => setExpandedIndex(isExpanded ? null : i)}
            >
              {editable && (
                <div className="tc-checkbox" onClick={(e) => e.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selectedIds?.has(tc.id) ?? false}
                    onChange={() => onToggleSelect?.(tc.id)}
                  />
                </div>
              )}
              <div
                className={`testcase-card-priority ${PRIORITY_CLASS[tc.priority] ?? "p3"}`}
              />
              <span className="testcase-card-index">
                TC-{String(i + 1).padStart(3, "0")}
              </span>
              <div className="testcase-card-summary">
                <span className="testcase-card-title">
                  {highlightText(title, searchText ?? "")}
                </span>
                {segments.map((seg, j) => (
                  <span
                    key={j}
                    style={{ display: "flex", alignItems: "center", gap: 4 }}
                  >
                    <span className="segment-arrow">→</span>
                    <span className="testcase-card-segment">
                      <span
                        className={`segment-label ${
                          seg.label === "前置"
                            ? "precondition"
                            : seg.label === "操作"
                              ? "action"
                              : seg.isError
                                ? "expected-error"
                                : "expected"
                        }`}
                      >
                        {seg.label}
                      </span>
                      <span
                        className={`segment-text${seg.label === "前置" ? " muted" : ""}`}
                      >
                        {highlightText(seg.text, searchText ?? "")}
                      </span>
                    </span>
                  </span>
                ))}
              </div>
              <span
                className={`testcase-card-priority-tag priority-tag-${tc.priority.toLowerCase()}`}
              >
                {tc.priority}
              </span>
              {tc.source === "user" ? (
                <span className="tc-user-added-badge">用户添加</span>
              ) : tc.updatedAt ? (
                <span className="tc-edited-badge">已修改</span>
              ) : null}
              <DownOutlined className="testcase-card-expand" />
              {editable && (
                <div className="tc-actions" onClick={(e) => e.stopPropagation()}>
                  <span className="tc-act-btn" onClick={() => onEdit?.(tc)} title="编辑">✎</span>
                  <span className="tc-act-btn del" onClick={() => onDelete?.(tc)} title="删除">✕</span>
                </div>
              )}
            </div>
            {isExpanded && (
              <div className="testcase-card-detail">
                <Tag color="purple" className="detail-tag">
                  {tc.module}
                </Tag>
                <Tag className="detail-tag">{tc.category}</Tag>
                {tc.confirmationNote && (
                  <span className="confirmation-badge">
                    ⚠ 待确认：{tc.confirmationNote}
                  </span>
                )}
                <div className="detail-full-summary">{tc.summary}</div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
