import { useCallback, useEffect, useRef, useState } from "react";
import {
  Button,
  Card,
  Col,
  DatePicker,
  Input,
  Radio,
  Row,
  Select,
  Space,
  Typography,
  message,
} from "antd";
import { CopyOutlined } from "@ant-design/icons";
import dayjs from "dayjs";

type Timezone = "local" | "utc";
type TimestampPrecision = "s" | "ms";

const LANG_SNIPPETS: Record<string, string> = {
  JavaScript: `Math.round(new Date().getTime() / 1000)`,
  Python: `import time\ntime.time()`,
  Go: `import "time"\ntime.Now().Unix()`,
  Java: `System.currentTimeMillis() / 1000`,
  PHP: `time()`,
  MySQL: `UNIX_TIMESTAMP(NOW())`,
  SQLite: `strftime('%s', 'now')`,
  "C#": `DateTimeOffset.UtcNow.ToUnixTimeSeconds()`,
};

interface ResultBlockProps {
  label: string;
  value: string;
  editable?: boolean;
  onChange?: (val: string) => void;
  onCopy: () => void;
}

function ResultBlock({ label, value, editable, onChange, onCopy }: ResultBlockProps) {
  return (
    <div
      style={{
        background: "var(--bg-inset)",
        border: "1px solid var(--border-card)",
        borderRadius: "var(--radius-md)",
        padding: "12px 16px",
      }}
    >
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        {label}
      </Typography.Text>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          marginTop: 4,
        }}
      >
        {editable ? (
          <Input
            value={value}
            onChange={(e) => onChange?.(e.target.value)}
            placeholder="—"
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 15,
              background: "transparent",
              border: "none",
              padding: 0,
            }}
            variant="borderless"
          />
        ) : (
          <Typography.Text
            strong
            style={{
              fontFamily: "var(--font-mono)",
              fontSize: 15,
              wordBreak: "break-all",
            }}
          >
            {value || "—"}
          </Typography.Text>
        )}
        <Button
          type="text"
          size="small"
          icon={<CopyOutlined />}
          onClick={onCopy}
          style={{ flexShrink: 0, marginLeft: 8 }}
        />
      </div>
    </div>
  );
}

export function TimestampTool() {
  const [tz, setTz] = useState<Timezone>("local");
  const [precision, setPrecision] = useState<TimestampPrecision>("s");

  const nowSeconds = Math.floor(Date.now() / 1000);
  const nowMillis = Date.now();

  const [stampInput, setStampInput] = useState(String(nowSeconds));
  const [stampResult, setStampResult] = useState(() => dayjs(nowSeconds * 1000).format("YYYY-MM-DD HH:mm:ss"));

  const [dateValue, setDateValue] = useState<dayjs.Dayjs>(dayjs());
  const [dateText, setDateText] = useState(dayjs().format("YYYY-MM-DD HH:mm:ss"));
  const [dateResult, setDateResult] = useState(String(nowSeconds));

  const [nowLiveSeconds, setNowLiveSeconds] = useState(nowSeconds);
  const [nowLiveMillis, setNowLiveMillis] = useState(nowMillis);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    intervalRef.current = setInterval(() => {
      setNowLiveSeconds(Math.floor(Date.now() / 1000));
      setNowLiveMillis(Date.now());
    }, 1000);
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, []);

  const syncStampToDate = useCallback(
    (stampStr: string, p: TimestampPrecision, t: Timezone) => {
      if (!stampStr.trim()) {
        setStampResult("");
        return;
      }
      const raw = Number(stampStr.trim());
      if (Number.isNaN(raw)) {
        setStampResult("");
        return;
      }
      const normalized = raw > 1e11 ? Math.floor(raw / 1000) : raw;
      const d = dayjs(normalized * 1000);
      setStampResult(d.format("YYYY-MM-DD HH:mm:ss"));
    },
    []
  );

  const syncDateToStamp = useCallback((m: dayjs.Dayjs | null, p: TimestampPrecision) => {
    if (!m || !m.isValid()) {
      setDateResult("");
      return;
    }
    const ms = m.valueOf();
    setDateResult(p === "ms" ? String(ms) : String(Math.floor(ms / 1000)));
  }, []);

  const handleStampChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const val = e.target.value;
    setStampInput(val);
    syncStampToDate(val, precision, tz);
  };

  const handlePrecisionChange = (p: TimestampPrecision) => {
    setPrecision(p);
    syncStampToDate(stampInput, p, tz);
    syncDateToStamp(dateValue, p);
  };

  const handleTzChange = (t: Timezone) => {
    setTz(t);
    syncStampToDate(stampInput, precision, t);
  };

  const handleDateChange = (m: dayjs.Dayjs | null) => {
    if (!m) return;
    setDateValue(m);
    setDateText(m.format("YYYY-MM-DD HH:mm:ss"));
    syncDateToStamp(m, precision);
  };

  const handleStampResultEdit = (val: string) => {
    setStampResult(val);
    if (!val.trim()) {
      setDateResult("");
      return;
    }
    const parsed = dayjs(val, "YYYY-MM-DD HH:mm:ss", true);
    if (!parsed.isValid()) {
      setDateResult("");
      return;
    }
    setDateValue(parsed);
    const ms = parsed.valueOf();
    setDateResult(precision === "ms" ? String(ms) : String(Math.floor(ms / 1000)));
  };

  const handleDateResultEdit = (val: string) => {
    setDateResult(val);
    if (!val.trim()) {
      setStampResult("");
      return;
    }
    const raw = Number(val.trim());
    if (Number.isNaN(raw)) {
      setStampResult("");
      return;
    }
    const normalized = raw > 1e11 ? Math.floor(raw / 1000) : raw;
    const d = dayjs(normalized * 1000);
    if (!d.isValid()) {
      setStampResult("");
      return;
    }
    setDateValue(d);
    setStampInput(precision === "ms" ? String(raw) : String(normalized));
    setStampResult(d.format("YY-MM-DD HH:mm:ss"));
  };

  const copyValue = (val: string) => {
    if (!val) return;
    navigator.clipboard.writeText(val).then(() => message.success("已复制"));
  };

  const copySnippet = (code: string) => {
    navigator.clipboard.writeText(code).then(() => message.success("已复制"));
  };

  return (
    <div className="timestamp-tool">
      {/* Current time bar */}
      <Card size="small" style={{ marginBottom: 16 }}>
        <Row gutter={24} align="middle">
          <Col>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              当前时间戳（秒）
            </Typography.Text>
            <Typography.Text
              strong
              style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: 16 }}
            >
              {nowLiveSeconds}
            </Typography.Text>
          </Col>
          <Col>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              当前时间戳（毫秒）
            </Typography.Text>
            <Typography.Text
              strong
              style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: 16 }}
            >
              {nowLiveMillis}
            </Typography.Text>
          </Col>
          <Col>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              当前北京时间
            </Typography.Text>
            <Typography.Text
              strong
              style={{ display: "block", fontFamily: "var(--font-mono)", fontSize: 16 }}
            >
              {dayjs().format("YYYY-MM-DD HH:mm:ss")}
            </Typography.Text>
          </Col>
          <Col style={{ marginLeft: "auto" }}>
            <Select
              value={tz}
              onChange={handleTzChange}
              options={[
                { value: "local", label: "北京时间" },
                { value: "utc", label: "UTC" },
              ]}
              style={{ width: 100 }}
              size="small"
            />
          </Col>
        </Row>
      </Card>

      {/* Dual converter */}
      <Row gutter={24} style={{ marginBottom: 16 }} align="stretch">
        {/* Left: timestamp -> date */}
        <Col span={12}>
          <Card title="时间戳 → 日期" bodyStyle={{ padding: "16px 20px" }}>
            <Space direction="vertical" style={{ width: "100%" }} size="middle">
              <Input.TextArea
                value={stampInput}
                onChange={handleStampChange}
                placeholder="输入时间戳"
                autoSize={{ minRows: 1, maxRows: 2 }}
                style={{ fontFamily: "var(--font-mono)", width: "50%" }}
              />
              <Radio.Group
                value={precision}
                onChange={(e) => handlePrecisionChange(e.target.value)}
              >
                <Radio.Button value="s">秒级</Radio.Button>
                <Radio.Button value="ms">毫秒级</Radio.Button>
              </Radio.Group>
              <div style={{ width: "50%" }}>
                <ResultBlock
                  label="转换结果"
                  value={stampResult}
                  editable
                  onChange={handleStampResultEdit}
                  onCopy={() => copyValue(stampResult)}
                />
              </div>
              <Button
                type="primary"
                style={{ width: "50%" }}
                onClick={() => syncStampToDate(stampInput, precision, tz)}
              >
                转换
              </Button>
            </Space>
          </Card>
        </Col>

        {/* Right: date -> timestamp */}
        <Col span={12}>
          <Card title="日期 → 时间戳" bodyStyle={{ padding: "16px 20px" }}>
            <Space direction="vertical" style={{ width: "100%" }} size="middle">
              <Input.TextArea
                value={dateText}
                onChange={(e) => {
                  const val = e.target.value;
                  setDateText(val);
                  if (!val.trim()) {
                    setDateValue(dayjs());
                    setDateResult("");
                    return;
                  }
                  const parsed = dayjs(val, "YYYY-MM-DD HH:mm:ss", true);
                  if (parsed.isValid()) {
                    setDateValue(parsed);
                    syncDateToStamp(parsed, precision);
                  }
                }}
                placeholder="YYYY-MM-DD HH:mm:ss"
                autoSize={{ minRows: 1, maxRows: 2 }}
                style={{ fontFamily: "var(--font-mono)", width: "50%" }}
              />
              <Radio.Group
                value={precision}
                onChange={(e) => handlePrecisionChange(e.target.value)}
              >
                <Radio.Button value="s">秒级</Radio.Button>
                <Radio.Button value="ms">毫秒级</Radio.Button>
              </Radio.Group>
              <div style={{ width: "50%" }}>
                <ResultBlock
                  label="转换结果"
                  value={dateResult}
                  editable
                  onChange={handleDateResultEdit}
                  onCopy={() => copyValue(dateResult)}
                />
              </div>
              <Button
                type="primary"
                style={{ width: "50%" }}
                onClick={() => syncDateToStamp(dateValue, precision)}
              >
                转换
              </Button>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Code snippets */}
      <Card title="常用语言获取当前时间戳" size="small">
        <Row gutter={[12, 8]}>
          {Object.entries(LANG_SNIPPETS).map(([lang, code]) => (
            <Col key={lang} xs={24} sm={12}>
              <Card size="small" bodyStyle={{ padding: "8px 12px" }}>
                <Space style={{ width: "100%", justifyContent: "space-between" }}>
                  <Typography.Text strong style={{ fontSize: 13 }}>
                    {lang}
                  </Typography.Text>
                  <Button
                    type="text"
                    size="small"
                    onClick={() => copySnippet(code)}
                    style={{ fontSize: 11, padding: "0 4px" }}
                  >
                    复制
                  </Button>
                </Space>
                <Typography.Text
                  type="secondary"
                  style={{
                    display: "block",
                    fontFamily: "var(--font-mono)",
                    fontSize: 11,
                    whiteSpace: "pre-wrap",
                    wordBreak: "break-all",
                  }}
                >
                  {code}
                </Typography.Text>
              </Card>
            </Col>
          ))}
        </Row>
      </Card>
    </div>
  );
}
