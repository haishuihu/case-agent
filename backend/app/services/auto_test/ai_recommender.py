from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.auto_test import TestCase, TestExecution, TestResult
from app.schemas.auto_test import RegressionRecommendItem

logger = logging.getLogger(__name__)


@dataclass
class ModuleInfo:
    """模块信息"""
    name: str
    type: str  # api, ui, service, model
    related_keywords: list[str]


class AIRecommender:
    """AI 回归推荐引擎
    
    基于代码变更分析，推荐需要执行的测试用例。
    
    评分公式:
    Score = α × Priority + β × ImpactFactor + γ × FailureRate + δ × Recency
    
    参数权重:
    - α (Priority): 0.3 - 用例优先级
    - β (ImpactFactor): 0.35 - 变更影响因子
    - γ (FailureRate): 0.2 - 历史失败率
    - δ (Recency): 0.15 - 最近执行衰减
    """
    
    WEIGHTS = {
        "priority": 0.30,
        "impact": 0.35,
        "failure_rate": 0.20,
        "recency": 0.15,
    }
    
    # 模块关键词映射
    MODULE_KEYWORDS = {
        "api": ["endpoint", "route", "handler", "controller", "/api", "router"],
        "auth": ["auth", "login", "token", "jwt", "permission", "role"],
        "user": ["user", "profile", "account", "member"],
        "order": ["order", "cart", "checkout", "payment", "transaction"],
        "product": ["product", "sku", "item", "catalog"],
        "notification": ["notification", "email", "sms", "push", "message"],
        "admin": ["admin", "dashboard", "manage", "setting"],
        "database": ["db", "sql", "query", "migration"],
        "file": ["file", "upload", "download", "storage", "s3"],
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_changed_modules(self, changed_files: list[str]) -> list[str]:
        """分析变更影响的模块"""
        modules = set()
        
        for file_path in changed_files:
            file_path_lower = file_path.lower()
            
            # 根据文件路径判断模块
            if "/api/" in file_path_lower or "/routes/" in file_path_lower:
                modules.add("api")
            if "/auth/" in file_path_lower or "/middleware/auth" in file_path_lower:
                modules.add("auth")
            if "/user/" in file_path_lower or "/account/" in file_path_lower:
                modules.add("user")
            if "/order/" in file_path_lower or "/cart/" in file_path_lower:
                modules.add("order")
            if "/product/" in file_path_lower or "/item/" in file_path_lower:
                modules.add("product")
            if "/notification/" in file_path_lower or "/message/" in file_path_lower:
                modules.add("notification")
            if "/admin/" in file_path_lower or "/dashboard/" in file_path_lower:
                modules.add("admin")
            if "/db/" in file_path_lower or "/model/" in file_path_lower:
                modules.add("database")
            if "/file/" in file_path_lower or "/upload/" in file_path_lower:
                modules.add("file")
            
            # 根据文件名关键词判断
            for module, keywords in self.MODULE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in file_path_lower:
                        modules.add(module)
                        break
        
        return list(modules)
    
    def parse_diff_for_modules(self, diff_content: str) -> list[str]:
        """从 diff 内容解析模块信息"""
        modules = set()
        
        # 提取变更的函数名
        function_pattern = r'def\s+(\w+)|class\s+(\w+)|async\s+def\s+(\w+)'
        functions = re.findall(function_pattern, diff_content)
        
        for func_match in functions:
            func_name = next(f for f in func_match if f)
            func_lower = func_name.lower()
            
            for module, keywords in self.MODULE_KEYWORDS.items():
                for keyword in keywords:
                    if keyword in func_lower:
                        modules.add(module)
                        break
        
        # 提取 API 路径
        api_pattern = r'["\']?(/[a-zA-Z0-9_/-]+)["\']?'
        api_paths = re.findall(api_pattern, diff_content)
        for path in api_paths:
            if len(path) > 2 and path.count('/') >= 2:
                modules.add("api")
                break
        
        return list(modules)
    
    def calculate_failure_rate(self, case_id: str) -> float:
        """计算用例历史失败率"""
        results = (
            self.db.query(TestResult)
            .filter(TestResult.case_id == case_id)
            .order_by(TestResult.created_at.desc())
            .limit(20)
            .all()
        )
        
        if not results:
            return 0.0
        
        failed_count = sum(1 for r in results if r.result == "fail")
        return failed_count / len(results)
    
    def calculate_recency_score(self, case_id: str) -> float:
        """计算最近执行衰减分数 (越久没执行分数越低)"""
        last_result = (
            self.db.query(TestResult)
            .filter(TestResult.case_id == case_id)
            .order_by(TestResult.executed_at.desc())
            .first()
        )
        
        if not last_result or not last_result.executed_at:
            return 1.0  # 从未执行过，给满分
        
        from datetime import datetime, timezone
        days_since = (datetime.now(timezone.utc) - last_result.executed_at).days
        
        # 30天内线性衰减
        if days_since <= 30:
            return 1.0 - (days_since / 30) * 0.5
        return 0.5
    
    def calculate_impact_factor(
        self,
        case: TestCase,
        changed_modules: list[str],
    ) -> float:
        """计算影响因子"""
        if not changed_modules:
            return 0.5  # 无变更信息，给中间值
        
        case_tags = json.loads(case.tags) if case.tags else []
        case_title_lower = case.title.lower()
        case_endpoint = (case.endpoint or "").lower()
        
        score = 0.0
        matched_modules = set()
        
        # 检查用例标签
        for module in changed_modules:
            if module in case_tags:
                score += 0.4
                matched_modules.add(module)
        
        # 检查用例标题
        for module in changed_modules:
            if module in case_title_lower:
                score += 0.3
                matched_modules.add(module)
        
        # 检查 API 端点
        for module in changed_modules:
            if module in case_endpoint:
                score += 0.3
                matched_modules.add(module)
        
        # 归一化
        if matched_modules:
            score = min(score, 1.0) * (len(matched_modules) / len(changed_modules))
        
        return score
    
    def recommend(
        self,
        changed_files: Optional[list[str]] = None,
        diff_content: Optional[str] = None,
        module_names: Optional[list[str]] = None,
        max_cases: int = 50,
        suite_id: Optional[str] = None,
    ) -> tuple[list[RegressionRecommendItem], str]:
        """生成回归推荐
        
        Returns:
            tuple: (推荐列表, 摘要)
        """
        # 分析受影响的模块
        affected_modules = set()
        
        if module_names:
            affected_modules.update(module_names)
        
        if changed_files:
            affected_modules.update(self.analyze_changed_modules(changed_files))
        
        if diff_content:
            affected_modules.update(self.parse_diff_for_modules(diff_content))
        
        affected_modules = list(affected_modules)
        
        # 查询候选用例
        query = self.db.query(TestCase).filter(TestCase.status == "active")
        
        if suite_id:
            query = query.filter(TestCase.suite_id == suite_id)
        
        if affected_modules:
            tag_filters = [TestCase.tags.ilike(f"%{m}%") for m in affected_modules]
            query = query.filter(*tag_filters)
        
        candidates = query.order_by(TestCase.priority.desc()).limit(max_cases * 2).all()
        
        # 计算评分
        scored_cases = []
        for case in candidates:
            priority_score = (case.priority / 5.0) * self.WEIGHTS["priority"]
            impact_score = self.calculate_impact_factor(case, affected_modules) * self.WEIGHTS["impact"]
            failure_score = self.calculate_failure_rate(case.id) * self.WEIGHTS["failure_rate"]
            recency_score = self.calculate_recency_score(case.id) * self.WEIGHTS["recency"]
            
            total_score = priority_score + impact_score + failure_score + recency_score
            
            # 生成推荐理由
            reasons = []
            if case.priority >= 4:
                reasons.append(f"高优先级({case.priority})")
            if impact_score > 0.3:
                reasons.append("变更影响")
            if self.calculate_failure_rate(case.id) > 0.2:
                reasons.append("历史失败率较高")
            
            reason = ", ".join(reasons) if reasons else f"用例优先级 {case.priority}"
            
            scored_cases.append({
                "case": case,
                "score": total_score,
                "reason": reason,
            })
        
        # 按分数排序
        scored_cases.sort(key=lambda x: x["score"], reverse=True)
        
        # 取前 max_cases 个
        recommendations = []
        for item in scored_cases[:max_cases]:
            case = item["case"]
            recommendations.append(
                RegressionRecommendItem(
                    case_id=case.id,
                    case_title=case.title,
                    priority=case.priority,
                    score=round(item["score"], 3),
                    reason=item["reason"],
                    estimated_duration_ms=1000,  # 默认1秒
                )
            )
        
        # 生成摘要
        if affected_modules:
            summary = f"检测到 {len(affected_modules)} 个模块受影响: {', '.join(affected_modules[:5])}"
            if len(affected_modules) > 5:
                summary += f" 等"
        else:
            summary = "未检测到具体模块变更，基于优先级推荐"
        
        summary += f"，共推荐 {len(recommendations)} 个测试用例"
        
        return recommendations, summary
    
    def get_ai_reasoning(
        self,
        case: TestCase,
        changed_modules: list[str],
    ) -> str:
        """生成 AI 推荐理由 (模拟 AI 分析)"""
        parts = []
        
        if changed_modules:
            matched = []
            case_tags = json.loads(case.tags) if case.tags else []
            for module in changed_modules:
                if module in case_tags or module in case.title.lower():
                    matched.append(module)
            
            if matched:
                parts.append(f"该用例与变更模块 {', '.join(matched)} 相关")
        
        failure_rate = self.calculate_failure_rate(case.id)
        if failure_rate > 0.3:
            parts.append(f"历史失败率 {failure_rate:.0%}，建议重点验证")
        elif failure_rate > 0:
            parts.append(f"历史失败率 {failure_rate:.0%}")
        
        recency = self.calculate_recency_score(case.id)
        if recency < 0.7:
            parts.append(f"已 {int((1 - recency) * 30)} 天未执行，建议回归")
        
        if not parts:
            parts.append(f"用例优先级 {case.priority}，建议执行")
        
        return "；".join(parts)


class AIAnalyzer:
    """AI 结果分析引擎
    
    分析测试执行结果，生成失败原因推测和改进建议。
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    def analyze_failure(
        self,
        result_id: str,
    ) -> dict:
        """分析单个失败用例"""
        result = self.db.query(TestResult).filter(TestResult.id == result_id).first()
        if not result:
            return {"error": "Result not found"}
        
        case = self.db.query(TestCase).filter(TestCase.id == result.case_id).first()
        
        analysis = {
            "case_id": result.case_id,
            "case_title": case.title if case else "Unknown",
            "error_message": result.error_message,
            "likely_root_cause": None,
            "suggestions": [],
        }
        
        error_msg = result.error_message or ""
        
        # 模式匹配分析
        if "timeout" in error_msg.lower():
            analysis["likely_root_cause"] = "请求超时"
            analysis["suggestions"].extend([
                "检查服务端响应时间",
                "考虑增加超时时间",
                "检查网络连接",
            ])
        
        if "connection" in error_msg.lower():
            analysis["likely_root_cause"] = "连接失败"
            analysis["suggestions"].extend([
                "检查服务端是否正常运行",
                "检查网络连通性",
                "确认端口和防火墙配置",
            ])
        
        if "500" in error_msg or "Internal Server Error" in error_msg:
            analysis["likely_root_cause"] = "服务端内部错误"
            analysis["suggestions"].extend([
                "检查服务端日志",
                "确认业务逻辑正确性",
                "查看堆栈信息",
            ])
        
        if "401" in error_msg or "403" in error_msg:
            analysis["likely_root_cause"] = "权限认证问题"
            analysis["suggestions"].extend([
                "检查 Token 是否有效",
                "确认用户权限",
                "验证接口访问权限",
            ])
        
        if "404" in error_msg or "Not Found" in error_msg:
            analysis["likely_root_cause"] = "资源不存在"
            analysis["suggestions"].extend([
                "检查接口路径是否正确",
                "确认资源是否已创建",
                "验证 ID 参数",
            ])
        
        if "validation" in error_msg.lower() or "invalid" in error_msg.lower():
            analysis["likely_root_cause"] = "参数校验失败"
            analysis["suggestions"].extend([
                "检查请求参数格式",
                "确认必填参数",
                "验证参数类型和范围",
            ])
        
        if not analysis["likely_root_cause"]:
            analysis["likely_root_cause"] = "未知错误"
            analysis["suggestions"].append("需要进一步调查")
        
        return analysis
    
    def generate_execution_summary(
        self,
        execution_id: str,
    ) -> tuple[str, list[str]]:
        """生成执行摘要和改进建议"""
        execution = self.db.query(TestExecution).filter(TestExecution.id == execution_id).first()
        if not execution:
            return "执行记录不存在", []
        
        results = self.db.query(TestResult).filter(TestResult.execution_id == execution_id).all()
        
        if not results:
            return "无测试结果", []
        
        passed = sum(1 for r in results if r.result == "pass")
        failed = sum(1 for r in results if r.result == "fail")
        total = len(results)
        pass_rate = (passed / total * 100) if total > 0 else 0
        
        # 生成摘要
        summary_parts = []
        if pass_rate >= 95:
            summary_parts.append(f"执行情况良好，通过率 {pass_rate:.1f}%")
        elif pass_rate >= 80:
            summary_parts.append(f"执行情况一般，通过率 {pass_rate:.1f}%，建议关注失败用例")
        else:
            summary_parts.append(f"执行情况较差，通过率 {pass_rate:.1f}%，需要重点关注")
        
        if failed > 0:
            summary_parts.append(f"共 {failed} 个用例失败")
        
        # 生成改进建议
        suggestions = []
        
        # 按错误类型分组
        error_types = {}
        for result in results:
            if result.result == "fail" and result.error_message:
                error_type = self._categorize_error(result.error_message)
                error_types[error_type] = error_types.get(error_type, 0) + 1
        
        if error_types:
            sorted_errors = sorted(error_types.items(), key=lambda x: x[1], reverse=True)
            top_error = sorted_errors[0]
            suggestions.append(f"主要错误类型: {top_error[0]} ({top_error[1]} 次)")
            
            if top_error[1] > total * 0.3:
                suggestions.append("建议优先排查高频错误")
        
        # 检查是否有超时问题
        timeout_count = sum(1 for r in results if "timeout" in (r.error_message or "").lower())
        if timeout_count > 0:
            suggestions.append(f"检测到 {timeout_count} 个超时问题，建议检查服务端性能")
        
        return "；".join(summary_parts), suggestions
    
    def _categorize_error(self, error_message: str) -> str:
        """分类错误类型"""
        error_lower = error_message.lower()
        
        if "timeout" in error_lower:
            return "超时"
        if "connection" in error_lower:
            return "连接失败"
        if "500" in error_message or "internal server error" in error_lower:
            return "服务端错误"
        if "401" in error_message or "403" in error_message:
            return "权限问题"
        if "404" in error_message or "not found" in error_lower:
            return "资源不存在"
        if "validation" in error_lower or "invalid" in error_lower:
            return "参数错误"
        if "syntax" in error_lower or "parse" in error_lower:
            return "解析错误"
        
        return "其他错误"
