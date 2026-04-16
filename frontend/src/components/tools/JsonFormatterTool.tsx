import { useCallback, useState } from "react";
import {
  Alert,
  Button,
  Card,
  Col,
  Input,
  Row,
  Space,
  Switch,
  Typography,
  message,
} from "antd";

const { TextArea } = Input;

export function JsonFormatterTool() {
  const [input, setInput] = useState("");
  const [output, setOutput] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [preserveEscape, setPreserveEscape] = useState(false);

  const getStats = (text: string) => {
    const chars = text.length;
    const lines = text ? text.split("\n").length : 0;
    return { chars, lines };
  };

  const process = useCallback(
    (raw: string, action: "format" | "minify") => {
      if (!raw.trim()) {
        setOutput("");
        setError(null);
        return;
      }

      let processed = raw;
      if (!preserveEscape) {
        try {
          const parsed = JSON.parse(raw);
          processed = JSON.stringify(parsed);
        } catch {
          processed = raw;
        }
      }

      try {
        const parsed = JSON.parse(preserveEscape ? JSON.parse(`"${processed}"`) : processed);
        let result: string;
        if (action === "format") {
          result = JSON.stringify(parsed, null, 2);
        } else {
          result = JSON.stringify(parsed);
        }
        setOutput(result);
        setError(null);
      } catch (e: unknown) {
        const err = e as SyntaxError;
        let errMsg = err.message;
        const match = err.message.match(/position (\d+)/);
        if (match) {
          const pos = Number(match[1]);
          const lines = raw.substring(0, pos).split("\n");
          const line = lines.length;
          const col = lines[lines.length - 1].length + 1;
          errMsg = `${err.message}（第 ${line} 行，第 ${col} 列）`;
        }
        setError(errMsg);
        setOutput("");
      }
    },
    [preserveEscape]
  );

  const handleFormat = () => process(input, "format");
  const handleMinify = () => process(input, "minify");

  const handleCopy = () => {
    if (!output) {
      message.warning("没有可复制的内容");
      return;
    }
    navigator.clipboard.writeText(output).then(() => message.success("已复制到剪贴板"));
  };

  const handleClear = () => {
    setInput("");
    setOutput("");
    setError(null);
  };

  const inputStats = getStats(input);
  const outputStats = getStats(output);

  return (
    <div className="json-formatter-tool">
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col flex="none">
          <Space>
            <Button type="primary" onClick={handleFormat} icon={<span>格式化</span>}>
              格式化
            </Button>
            <Button onClick={handleMinify}>压缩</Button>
            <Button onClick={handleCopy}>复制</Button>
            <Button onClick={handleClear}>清除</Button>
          </Space>
        </Col>
        <Col flex="auto">
          <Space>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              保留转义
            </Typography.Text>
            <Switch
              size="small"
              checked={preserveEscape}
              onChange={(checked) => {
                setPreserveEscape(checked);
                if (input) process(input, "format");
              }}
            />
          </Space>
        </Col>
        <Col flex="none">
          <Typography.Text type="secondary" style={{ fontSize: 12 }}>
            {inputStats.chars} 字符 · {inputStats.lines} 行
          </Typography.Text>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <div style={{ marginBottom: 8, fontSize: 12, color: "var(--text-secondary)", fontWeight: 500 }}>
            输入
          </div>
          <TextArea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="输入 JSON 内容..."
            autoSize={{ minRows: 16, maxRows: 24 }}
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 13,
              resize: "vertical",
            }}
            onKeyDown={(e) => {
              if (e.key === "Tab") {
                e.preventDefault();
                const start = e.currentTarget.selectionStart;
                const end = e.currentTarget.selectionEnd;
                const newVal = input.substring(0, start) + "  " + input.substring(end);
                setInput(newVal);
                requestAnimationFrame(() => {
                  (e.target as HTMLTextAreaElement).selectionStart = start + 2;
                  (e.target as HTMLTextAreaElement).selectionEnd = start + 2;
                });
              }
            }}
          />
        </Col>
        <Col span={12}>
          <div style={{ marginBottom: 8, fontSize: 12, color: "var(--text-secondary)", fontWeight: 500 }}>
            输出
          </div>
          {error ? (
            <Alert message={error} type="error" showIcon />
          ) : (
            <TextArea
              value={output}
              readOnly
              placeholder="格式化结果..."
              autoSize={{ minRows: 16, maxRows: 24 }}
              style={{
                fontFamily: "var(--font-mono)",
                fontSize: 13,
                background: "var(--bg-inset)",
                resize: "vertical",
              }}
            />
          )}
        </Col>
      </Row>

      {output && (
        <Row style={{ marginTop: 12 }}>
          <Col>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              输出：{outputStats.chars} 字符 · {outputStats.lines} 行
            </Typography.Text>
          </Col>
        </Row>
      )}
    </div>
  );
}
