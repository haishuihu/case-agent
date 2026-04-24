import { useState } from "react";
import {
  Button,
  Card,
  Input,
  Result,
  Space,
  Spin,
  Steps,
  Table,
  Tag,
  Typography,
  message,
  Divider,
} from "antd";
import { ThunderboltOutlined, PlusOutlined } from "@ant-design/icons";
import {
  appendGenerateCases,
  type AppendedCase,
} from "../../services/api";

interface AppendGenerateProps {
  modelKey?: string;
  requirementText?: string;
  onAppended?: (cases: AppendedCase[]) => void;
}

type Phase = "input" | "generating" | "done" | "error";

const CATEGORY_COLORS: Record<string, string> = {
  "正常流程": "green",
  "异常场景": "red",
  "边界条件": "orange",
  "并发测试": "purple",
  "安全测试": "magenta",
  "性能测试": "geekblue",
};

const PRIORITY_COLORS: Record<string, string> = {
  P0: "red",
  P1: "orange",
  P2: "blue",
};

export function AppendGenerate({ modelKey, requirementText = "", onAppended }: AppendGenerateProps) {
  const [phase, setPhase] = useState<Phase>("input");
  const [existingCases, setExistingCases] = useState("");
  const [requirement, setRequirement] = useState(requirementText);
  const [appendedCases, setAppendedCases] = useState<AppendedCase[]>([]);
  const [summary, setSummary] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [model, setModel] = useState("");

  const handleGenerate = async () => {
    if (!existingCases.trim()) {
      message.warning("请先粘贴已有用例内容");
      return;
    }
    if (!requirement.trim()) {
      message.warning("请填写需求描述");
      return;
    }

    setPhase("generating");
    setErrorMessage("");
    try {
      const result = await appendGenerateCases(existingCases, requirement, modelKey);
      setAppendedCases(result.appendedCases);
      setSummary(result.summary);
      setPhase("done");
      if (onAppended) {
        onAppended(result.appendedCases);
      }
    } catch (e) {
      setErrorMessage(e instanceof Error ? e.message : "追加生成失败，请稍后重试。");
      setPhase("error");
    }
  };

  const handleReset = () => {
    setPhase("input");
    setAppendedCases([]);
    setSummary("");
    setErrorMessage("");
  };

  const columns = [
    {
      title: "用例标题",
      dataIndex: "title",
      key: "title",
      render: (v: string) => <Typography.Text strong>{v}</Typography.Text>,
    },
    {
      title: "模块",
      dataIndex: "module",
      key: "module",
      width: 120,
    },
    {
      title: "分类",
      dataIndex: "category",
      key: "category",
      width: 120,
      render: (v: string) => (
        <Tag color={CATEGORY_COLORS[v] ?? "default"}>{v}</Tag>
      ),
    },
    {
      title: "优先级",
      dataIndex: "priority",
      key: "priority",
      width: 80,
      render: (v: string) => (
        <Tag color={PRIORITY_COLORS[v] ?? "default"}>{v}</Tag>
      ),
    },
    {
      title: "遗漏原因",
      dataIndex: "missing_reason",
      key: "missing_reason",
      render: (v: string) => (
        <Typography.Text type="secondary" style={{ fontSize: 12 }}>
          {v}
        </Typography.Text>
      ),
    },
  ];

  // Input phase
  if (phase === "input") {
    return (
      <Card size="small" title={<><PlusOutlined style={{ marginRight: 6 }} />追加生成</>}>
        <Typography.Paragraph type="secondary" style={{ fontSize: 13 }}>
          粘贴已有用例，AI 分析遗漏场景并补充用例。适合已有用例需要补充的场景。
        </Typography.Paragraph>
        <div style={{ marginBottom: 12 }}>
          <Typography.Text strong style={{ fontSize: 13 }}>需求描述</Typography.Text>
          <Input.TextArea
            placeholder="请输入需求描述"
            rows={3}
            value={requirement}
            onChange={(e) => setRequirement(e.target.value)}
            style={{ marginTop: 6 }}
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <Typography.Text strong style={{ fontSize: 13 }}>已有用例内容</Typography.Text>
          <Input.TextArea
            placeholder="请粘贴已有的测试用例内容（Markdown 格式）..."
            rows={8}
            value={existingCases}
            onChange={(e) => setExistingCases(e.target.value)}
            style={{ marginTop: 6, fontFamily: "monospace", fontSize: 12 }}
          />
        </div>
        <Button
          type="primary"
          icon={<ThunderboltOutlined />}
          onClick={() => void handleGenerate()}
          disabled={!existingCases.trim() || !requirement.trim()}
        >
          分析遗漏场景并补充
        </Button>
      </Card>
    );
  }

  // Generating phase
  if (phase === "generating") {
    return (
      <Card size="small" title={<><PlusOutlined style={{ marginRight: 6 }} />追加生成</>}>
        <Space style={{ width: "100%", justifyContent: "center" }} direction="vertical" align="center">
          <Spin size="large" />
          <Typography.Text type="secondary">AI 正在分析已有用例的覆盖情况，补充遗漏场景...</Typography.Text>
        </Space>
      </Card>
    );
  }

  // Error phase
  if (phase === "error") {
    return (
      <Card size="small" title={<><PlusOutlined style={{ marginRight: 6 }} />追加生成</>}>
        <Result
          status="error"
          title="追加生成失败"
          subTitle={errorMessage}
          extra={
            <Button type="primary" onClick={() => void handleGenerate()}>
              重试
            </Button>
          }
        />
      </Card>
    );
  }

  // Done phase
  return (
    <Card
      size="small"
      title={<><PlusOutlined style={{ marginRight: 6 }} />追加生成结果</>}
      extra={
        <Button size="small" onClick={() => void handleReset()}>
          重新追加
        </Button>
      }
    >
      <Steps
        current={2}
        size="small"
        items={[
          { title: "粘贴已有用例" },
          { title: "AI 分析遗漏" },
          { title: `补充 ${appendedCases.length} 个场景` },
        ]}
        style={{ marginBottom: 16 }}
      />
      {summary && (
        <Alert
          type="info"
          message="补充说明"
          description={summary}
          style={{ marginBottom: 12 }}
        />
      )}
      <Table
        dataSource={appendedCases}
        columns={columns}
        rowKey={(_, i) => String(i)}
        size="small"
        pagination={false}
        scroll={{ y: 400 }}
      />
    </Card>
  );
}
