import { useState } from "react";
import {
  Button,
  Card,
  DatePicker,
  InputNumber,
  Radio,
  Space,
  Typography,
} from "antd";
import dayjs, { type Dayjs } from "dayjs";

const WEEKDAY_NAMES = ["星期日", "星期一", "星期二", "星期三", "星期四", "星期五", "星期六"];

function formatResult(d: Dayjs): string {
  const weekday = WEEKDAY_NAMES[d.day()];
  return `${d.format("YYYY年M月D日")} ${weekday}`;
}

export function DateCalculator() {
  const [baseDate, setBaseDate] = useState<Dayjs | null>(null);
  const [mode, setMode] = useState<"add" | "subtract">("add");
  const [days, setDays] = useState<number | null>(null);
  const [result, setResult] = useState<string | null>(null);

  const handleCompute = () => {
    if (!baseDate || !days || days < 1) return;
    const delta = days - 1;
    const target =
      mode === "add"
        ? baseDate.add(delta, "day")
        : baseDate.subtract(delta, "day");
    setResult(formatResult(target));
  };

  return (
    <div className="date-calculator">
      <Card>
        <Typography.Title level={5} style={{ marginBottom: 20 }}>
          日期计算器
        </Typography.Title>

        <Space direction="vertical" size="middle" style={{ width: "100%" }}>
          <div>
            <Typography.Text
              type="secondary"
              style={{ fontSize: 12, marginBottom: 6, display: "block" }}
            >
              基准日期
            </Typography.Text>
            <DatePicker
              value={baseDate}
              onChange={(d) => setBaseDate(d)}
              placeholder="选择日期"
              style={{ width: "100%" }}
              format="YYYY-MM-DD"
            />
          </div>

          <div>
            <Typography.Text
              type="secondary"
              style={{ fontSize: 12, marginBottom: 6, display: "block" }}
            >
              计算方式
            </Typography.Text>
            <Radio.Group
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              optionType="button"
              buttonStyle="solid"
            >
              <Radio.Button value="add">加天数</Radio.Button>
              <Radio.Button value="subtract">减天数</Radio.Button>
            </Radio.Group>
          </div>

          <div>
            <Typography.Text
              type="secondary"
              style={{ fontSize: 12, marginBottom: 6, display: "block" }}
            >
              天数
            </Typography.Text>
            <InputNumber
              value={days}
              onChange={(v) => setDays(v)}
              placeholder="输入正整数天数"
              min={1}
              precision={0}
              style={{ width: "100%" }}
              addonAfter="天"
            />
          </div>

          <Button
            type="primary"
            block
            disabled={!baseDate || !days || days < 1}
            onClick={handleCompute}
          >
            计算
          </Button>
        </Space>

        {result && (
          <div className="date-calculator-result">
            <Typography.Text
              strong
              style={{ fontSize: 16 }}
            >
              {result}
            </Typography.Text>
          </div>
        )}
      </Card>
    </div>
  );
}
