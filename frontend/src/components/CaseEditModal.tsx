import { useEffect, useState } from "react";
import { Input, Modal, Select } from "antd";
import type { TestCaseItem } from "../services/api";

const { TextArea } = Input;

interface CaseEditModalProps {
  open: boolean;
  mode: "create" | "edit";
  initialData?: TestCaseItem;
  defaultModule?: string;
  onCancel: () => void;
  onSave: (data: {
    summary: string;
    priority: string;
    module: string;
    category: string;
  }) => void;
  saving?: boolean;
}

export function CaseEditModal({
  open,
  mode,
  initialData,
  defaultModule,
  onCancel,
  onSave,
  saving,
}: CaseEditModalProps) {
  const [summary, setSummary] = useState("");
  const [priority, setPriority] = useState("P2");
  const [module, setModule] = useState("");
  const [category, setCategory] = useState("");

  useEffect(() => {
    if (open) {
      if (mode === "edit" && initialData) {
        setSummary(initialData.summary);
        setPriority(initialData.priority);
        setModule(initialData.module);
        setCategory(initialData.category);
      } else {
        setSummary("用例标题：\n前置条件：\n操作步骤：\n预期结果：");
        setPriority("P2");
        setModule(defaultModule ?? "");
        setCategory("");
      }
    }
  }, [open, mode, initialData, defaultModule]);

  const handleSave = () => {
    if (!summary.trim()) return;
    onSave({
      summary: summary.trim(),
      priority,
      module: module.trim(),
      category: category.trim(),
    });
  };

  return (
    <Modal
      title={mode === "edit" ? "编辑用例" : "新增用例"}
      open={open}
      onCancel={onCancel}
      onOk={handleSave}
      confirmLoading={saving}
      okText={mode === "edit" ? "保存修改" : "添加用例"}
      cancelText="取消"
      width={580}
      destroyOnClose
    >
      <div style={{ display: "flex", flexDirection: "column", gap: 16, paddingTop: 8 }}>
        <div style={{ display: "flex", gap: 12 }}>
          <div style={{ flex: "0 0 100px" }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 4 }}>
              优先级
            </div>
            <Select
              value={priority}
              onChange={setPriority}
              style={{ width: "100%" }}
              options={[
                { value: "P0", label: "P0" },
                { value: "P1", label: "P1" },
                { value: "P2", label: "P2" },
                { value: "P3", label: "P3" },
              ]}
            />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 4 }}>
              所属模块
            </div>
            <Input value={module} onChange={(e) => setModule(e.target.value)} placeholder="模块名称" />
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 4 }}>
              分类
            </div>
            <Input value={category} onChange={(e) => setCategory(e.target.value)} placeholder="用例分类" />
          </div>
        </div>
        <div>
          <div style={{ fontSize: 12, fontWeight: 600, color: "#374151", marginBottom: 4 }}>
            用例摘要
          </div>
          <TextArea
            value={summary}
            onChange={(e) => setSummary(e.target.value)}
            rows={10}
          />
          <div style={{ fontSize: 11, color: "#9CA3AF", marginTop: 4 }}>
            格式：标题 + 前置条件 + 操作步骤 + 预期结果
          </div>
        </div>
      </div>
    </Modal>
  );
}
