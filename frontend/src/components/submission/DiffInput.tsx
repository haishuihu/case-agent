import { useState, useCallback, useMemo } from "react";
import { Alert, Button, Space, Spin, Typography } from "antd";
import { RadarChartOutlined } from "@ant-design/icons";

interface DiffInputProps {
  value: string;
  onChange: (value: string) => void;
  onAnalyze: () => Promise<void>;
  loading?: boolean;
  error?: string;
  defaultDiff?: string;
}

export function DiffInput({ value, onChange, onAnalyze, loading, error, defaultDiff }: DiffInputProps) {
  const [internalValue, setInternalValue] = useState(value || defaultDiff || "");

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      const v = e.target.value;
      setInternalValue(v);
      onChange(v);
    },
    [onChange]
  );

  const stats = useMemo(() => {
    const lines = internalValue.split("\n");
    const added = lines.filter((l) => l.startsWith("+") && !l.startsWith("+++")).length;
    const deleted = lines.filter((l) => l.startsWith("-") && !l.startsWith("---")).length;
    return { added, deleted };
  }, [internalValue]);

  const canAnalyze = internalValue.trim().length > 0 && !loading;

  return (
    <div className="diff-input">
      <div className="diff-input-header">
        <div>
          <Typography.Text strong style={{ fontSize: 14 }}>
            粘贴 Git Diff
          </Typography.Text>
          <Typography.Text type="secondary" style={{ fontSize: 12, marginLeft: 8 }}>
            支持 unified diff 格式
          </Typography.Text>
        </div>
        <Space size={8}>
          {internalValue.length > 0 && (
            <>
              <Typography.Text type="success" style={{ fontSize: 12 }}>
                +{stats.added}
              </Typography.Text>
              <Typography.Text type="danger" style={{ fontSize: 12 }}>
                -{stats.deleted}
              </Typography.Text>
            </>
          )}
        </Space>
      </div>

      <textarea
        className="diff-input-textarea"
        value={internalValue}
        onChange={handleChange}
        placeholder={"粘贴 Git Diff 内容，例如：\n\ndiff --git a/src/user.py b/src/user.py\n--- a/src/user.py\n+++ b/src/user.py\n@@ -1,3 +1,4 @@\n def get_user():\n+    new_code\n     return user"}
        rows={10}
        disabled={loading}
      />

      {error && (
        <Alert type="error" message={error} showIcon style={{ marginTop: 8 }} />
      )}

      <div className="diff-input-actions">
        <Button
          type="primary"
          icon={<RadarChartOutlined />}
          onClick={() => void onAnalyze()}
          loading={loading}
          disabled={!canAnalyze}
        >
          {loading ? "分析中..." : "开始影响分析"}
        </Button>
        {loading && (
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            正在解析代码变更，请稍候...
          </Typography.Text>
        )}
      </div>
    </div>
  );
}
