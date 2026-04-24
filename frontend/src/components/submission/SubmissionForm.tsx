import { useState } from "react";
import {
  Alert,
  Button,
  Card,
  Checkbox,
  Col,
  Form,
  Input,
  InputNumber,
  Row,
  Select,
  Space,
  Typography,
  Divider,
} from "antd";
import {
  RobotOutlined,
  SendOutlined,
  CloseOutlined,
} from "@ant-design/icons";
import type { CreateSubmissionPayload, GenerateChecklistResponse } from "../../services/submission";

const { TextArea } = Input;
const { Option } = Select;

interface SubmissionFormProps {
  onSubmit: (values: CreateSubmissionPayload) => Promise<void>;
  onCancel: () => void;
  initialValues?: Partial<CreateSubmissionPayload>;
  loading?: boolean;
  onGenerateChecklist?: (
    changeDescription: string,
    affectedModules: string[]
  ) => Promise<GenerateChecklistResponse>;
}

const SUBMISSION_TYPE_OPTIONS = [
  { value: "feature", label: "功能开发" },
  { value: "bugfix", label: "Bug修复" },
  { value: "urgent", label: "紧急提测" },
];

const CHANGE_TYPE_OPTIONS = [
  { value: "added", label: "新增" },
  { value: "modified", label: "修改" },
  { value: "deleted", label: "删除" },
];

export function SubmissionForm({
  onSubmit,
  onCancel,
  initialValues,
  loading,
  onGenerateChecklist,
}: SubmissionFormProps) {
  const [form] = Form.useForm<CreateSubmissionPayload>();
  const [generatingChecklist, setGeneratingChecklist] = useState(false);
  const [checklistHint, setChecklistHint] = useState<string | null>(null);
  const [checklistWarning, setChecklistWarning] = useState<string | null>(null);

  const handleGenerateChecklist = async () => {
    const values = form.getFieldsValue();
    if (!values.changeDescription) {
      setChecklistWarning("请先填写变更描述");
      return;
    }
    setChecklistWarning(null);
    setGeneratingChecklist(true);
    try {
      if (onGenerateChecklist) {
        const result = await onGenerateChecklist(
          values.changeDescription,
          values.affectedModules ?? []
        );
        setChecklistHint(
          `已生成 ${result.checklists.length} 条检查项：高风险 ${result.checklists.filter((c) => c.risk_level === "high").length} 项，` +
          `建议：${result.suggestions.slice(0, 2).join("；")}`
        );
      }
    } catch {
      setChecklistWarning("生成检查清单失败，请稍后重试");
    } finally {
      setGeneratingChecklist(false);
    }
  };

  const handleFinish = async (values: CreateSubmissionPayload) => {
    await onSubmit(values);
  };

  return (
    <div className="submission-form">
      <Card className="workspace-card">
        <Form
          form={form}
          layout="vertical"
          initialValues={initialValues}
          onFinish={handleFinish}
          requiredMark="optional"
        >
          <Row gutter={24}>
            <Col xs={24} md={12}>
              <Form.Item
                name="version"
                label={<Typography.Text strong>版本号</Typography.Text>}
                rules={[{ required: true, message: "请输入提测版本号" }]}
              >
                <Input placeholder="例如：v1.0.0" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="submissionType"
                label={<Typography.Text strong>提测类型</Typography.Text>}
                initialValue="feature"
                rules={[{ required: true, message: "请选择提测类型" }]}
              >
                <Select>
                  {SUBMISSION_TYPE_OPTIONS.map((opt) => (
                    <Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="changeDescription"
            label={<Typography.Text strong>变更描述</Typography.Text>}
            rules={[{ required: true, message: "请输入变更描述" }]}
          >
            <TextArea
              rows={4}
              placeholder="详细描述本次变更的内容、目的和影响"
              showCount
              maxLength={2000}
            />
          </Form.Item>

          <Row gutter={24}>
            <Col xs={24} md={12}>
              <Form.Item
                name="affectedModules"
                label={<Typography.Text strong>影响模块</Typography.Text>}
              >
                <Select mode="tags" placeholder="输入模块名后按回车添加" allowClear>
                  <Option value="用户模块">用户模块</Option>
                  <Option value="登录模块">登录模块</Option>
                  <Option value="订单模块">订单模块</Option>
                  <Option value="支付模块">支付模块</Option>
                  <Option value="商品模块">商品模块</Option>
                  <Option value="搜索模块">搜索模块</Option>
                  <Option value="消息模块">消息模块</Option>
                  <Option value="权限模块">权限模块</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item
                name="changeType"
                label={<Typography.Text strong>变更类型</Typography.Text>}
                initialValue="modified"
              >
                <Select>
                  {CHANGE_TYPE_OPTIONS.map((opt) => (
                    <Option key={opt.value} value={opt.value}>
                      {opt.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">关联需求</Divider>

          <Row gutter={24}>
            <Col xs={24} md={12}>
              <Form.Item name="requirementId" label="需求ID">
                <Input placeholder="例如：REQ-2024-001" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="requirementLink" label="需求链接">
                <Input placeholder="https://..." />
              </Form.Item>
            </Col>
          </Row>

          <Divider orientation="left">自测信息</Divider>

          <Form.Item name="selfTestPassed" valuePropName="checked" initialValue={false}>
            <Checkbox>自测已通过</Checkbox>
          </Form.Item>

          <Row gutter={24}>
            <Col xs={24} md={8}>
              <Form.Item name="selfTestCaseCount" label="自测用例数">
                <InputNumber min={0} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="selfTestCoverage" label="覆盖率 (%)">
                <InputNumber min={0} max={100} style={{ width: "100%" }} />
              </Form.Item>
            </Col>
            <Col xs={24} md={8}>
              <Form.Item name="smokeTestResult" label="冒烟测试" initialValue="not_executed">
                <Select>
                  <Option value="passed">通过</Option>
                  <Option value="failed">失败</Option>
                  <Option value="not_executed">未执行</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="selfTestConclusion" label="自测结论">
            <Input placeholder="简要说明自测结论" />
          </Form.Item>

          <Divider orientation="left">Git 信息</Divider>

          <Row gutter={24}>
            <Col xs={24} md={12}>
              <Form.Item name="branchName" label="分支名">
                <Input placeholder="例如：feature/login-optimization" />
              </Form.Item>
            </Col>
            <Col xs={24} md={12}>
              <Form.Item name="gitCommitHash" label="Commit Hash">
                <Input placeholder="例如：a1b2c3d4" />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item name="gitDiff" label="Git Diff">
            <TextArea
              rows={6}
              placeholder="粘贴 Git Diff 内容（可选），AI 将根据变更内容生成更准确的检查清单"
              style={{ fontFamily: "var(--font-mono)", fontSize: 12 }}
            />
          </Form.Item>

          {checklistWarning && (
            <Alert type="warning" message={checklistWarning} showIcon style={{ marginBottom: 16 }} />
          )}

          {checklistHint && (
            <Alert
              type="info"
              message={
                <Space>
                  <RobotOutlined />
                  <span>{checklistHint}</span>
                </Space>
              }
              showIcon
              style={{ marginBottom: 16 }}
            />
          )}

          {onGenerateChecklist && (
            <Button
              icon={<RobotOutlined />}
              onClick={handleGenerateChecklist}
              loading={generatingChecklist}
              style={{ marginBottom: 16 }}
            >
              AI 生成检查清单
            </Button>
          )}

          <Divider />

          <Form.Item name="submitter" label="提交人">
            <Input placeholder="填写你的名字" />
          </Form.Item>

          <Form.Item style={{ marginBottom: 0 }}>
            <Space style={{ width: "100%", justifyContent: "flex-end" }}>
              <Button
                icon={<CloseOutlined />}
                onClick={onCancel}
                disabled={loading}
              >
                取消
              </Button>
              <Button
                type="primary"
                icon={<SendOutlined />}
                htmlType="submit"
                loading={loading}
              >
                提交提测
              </Button>
            </Space>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}
