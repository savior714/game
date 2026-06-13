#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Language: ko

import ast
import argparse
import subprocess
import sys
import os
from typing import List, Dict, Tuple

import yaml
import re

def check_fastapi_decorators(directory: str) -> Tuple[bool, List[str], List[str]]:
    """FastAPI 라우트 데코레이터(@router.<method>)가 있는 모든 함수에 @compliance_target 데코레이터가 누락되었는지 검사합니다.
    
    신규/수정된 파일의 함수 누락 시 에러(errors)로 빌드를 차단하고, 
    기존 파일의 누락은 경고(warnings)로만 출력합니다.
    """
    warnings = []
    errors = []
    
    modified_lines_map = {} # file_path -> set of modified line numbers
    try:
        # git diff 를 통해 이번에 변경되거나 새로 추가된 라인 추출
        # HEAD 대비 변경된 라인 (수정된 파일)
        diff_output = subprocess.check_output(
            ["git", "diff", "HEAD", "--", directory], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore")
        
        # 스테이지된 새로운 파일도 포함 (새로 추가된 파일)
        staged_diff_output = subprocess.check_output(
            ["git", "diff", "--cached", "--", directory], 
            stderr=subprocess.DEVNULL
        ).decode("utf-8", errors="ignore")
        
        # 두 diff 를 합침
        diff_output = diff_output + "\n" + staged_diff_output
        
        current_file = None
        current_line = 0
        for line in diff_output.splitlines():
            if line.startswith("+++ b/"):
                current_file = line[6:].strip()
                modified_lines_map[current_file] = set()
            elif line.startswith("@@"):
                match = re.search(r"\+(\d+)", line)
                if match:
                    current_line = int(match.group(1))
            elif line.startswith("+") and not line.startswith("+++"):
                if current_file:
                    modified_lines_map[current_file].add(current_line)
                current_line += 1
            elif not line.startswith("-"):
                current_line += 1
    except Exception:
        pass

    for root, _, files in os.walk(directory):
        for file in files:
            if not file.endswith(".py"):
                continue
            file_path = os.path.join(root, file)
            repo_relative_path = os.path.relpath(file_path, os.getcwd())
            
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                
                # 라우터 관련 키워드가 없는 경우 최적화 스킵
                if "APIRouter" not in content and "@router" not in content:
                    continue
                
                tree = ast.parse(content, filename=file_path)
                
                # 라우터 객체 이름 자동 추출
                router_names = {"router"}
                for node in ast.walk(tree):
                    if isinstance(node, ast.Assign):
                        if isinstance(node.value, ast.Call):
                            func = node.value.func
                            if isinstance(func, ast.Name) and func.id == "APIRouter":
                                for target in node.targets:
                                    if isinstance(target, ast.Name):
                                        router_names.add(target.id)
                
                # 함수 정의 순회 검사
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        is_route = False
                        route_decorator_name = ""
                        has_compliance = False
                        
                        for dec in node.decorator_list:
                            # 1. @router.get(...) 등 라우터 호출 확인
                            if isinstance(dec, ast.Call):
                                func = dec.func
                                if isinstance(func, ast.Attribute):
                                    if isinstance(func.value, ast.Name) and func.value.id in router_names:
                                        if func.attr in ["get", "post", "put", "delete", "patch", "options", "head", "trace", "api_route"]:
                                            is_route = True
                                            route_decorator_name = f"{func.value.id}.{func.attr}"
                            
                            # 2. @compliance_target 데코레이터 확인
                            dec_name = ""
                            if isinstance(dec, ast.Call):
                                if isinstance(dec.func, ast.Name):
                                    dec_name = dec.func.id
                                elif isinstance(dec.func, ast.Attribute):
                                    dec_name = dec.func.attr
                            elif isinstance(dec, ast.Name):
                                dec_name = dec.id
                            elif isinstance(dec, ast.Attribute):
                                dec_name = dec.attr
                                
                            if dec_name == "compliance_target":
                                has_compliance = True
                                
                        if is_route and not has_compliance:
                            line_no = node.lineno
                            msg = f"  - {repo_relative_path}:{line_no} (def {node.name}): @{route_decorator_name} 에 @compliance_target 이 누락되었습니다."
                            
                            is_new_route = False
                            if repo_relative_path in modified_lines_map:
                                dec_lines = [d.lineno for d in node.decorator_list]
                                func_lines = set(dec_lines + list(range(node.lineno, getattr(node, "end_lineno", node.lineno) + 1)))
                                if func_lines.intersection(modified_lines_map[repo_relative_path]):
                                    is_new_route = True
                                    
                            if is_new_route:
                                errors.append(msg)
                            else:
                                warnings.append(msg)
                                
            except Exception as e:
                warnings.append(f"  - {repo_relative_path}: 파싱 중 에러 발생: {e}")
                
    success = (len(errors) == 0)
    return success, warnings, errors

# Domain to Command Mapping (Seed Data / Fallback)
SEED_DOMAIN_MAPPING: Dict[str, List[str]] = {
    # This will be merged with dynamic data from .agents/
}

def load_dynamic_mapping() -> Dict[str, List[str]]:
    """Scan .agents/ directory and extract domain/verify_with from frontmatter."""
    mapping = SEED_DOMAIN_MAPPING.copy()
    agents_dir = ".agents"
    
    if not os.path.exists(agents_dir):
        return mapping

    for root, _, files in os.walk(agents_dir):
        for file in files:
            if file.endswith(".md"):
                path = os.path.join(root, file)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                        # Simple extraction of frontmatter (between ---)
                        match = re.search(r"^---\s*\n(.*?)\n---\s*\n", content, re.DOTALL)
                        if match:
                            fm_text = match.group(1)
                            metadata = yaml.safe_load(fm_text)
                            if not metadata:
                                continue
                                
                            domain = metadata.get("domain")
                            verify_with = metadata.get("verify_with")
                            
                            if domain and verify_with:
                                if isinstance(verify_with, str):
                                    verify_with = [verify_with]
                                
                                if domain not in mapping:
                                    mapping[domain] = []
                                
                                for cmd in verify_with:
                                    if cmd not in mapping[domain]:
                                        mapping[domain].append(cmd)
                except Exception:
                    # Silently skip if not a valid frontmatter or other errors
                    pass
    mapping["fastapi_router"] = []
    return mapping

DOMAIN_MAPPING = load_dynamic_mapping()

def run_command(command: str) -> bool:
    print(f"🚀 Running: {command}")
    try:
        # Use shell=True because some commands are just aliases or have pipes
        result = subprocess.run(command, shell=True, check=False)
        if result.returncode == 0:
            print(f"✅ Success: {command}")
            return True
        else:
            print(f"❌ Failed (exit code {result.returncode}): {command}")
            return False
    except Exception as e:
        print(f"💥 Exception while running {command}: {e}")
        return False

from datetime import datetime

def generate_report(results: Dict[str, Dict], overall_success: bool):
    """Generate a markdown report of the compliance check results."""
    report_dir = "docs/reports"
    os.makedirs(report_dir, exist_ok=True)
    report_path = os.path.join(report_dir, "REPORT_compliance_summary.md")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status_icon = "✅" if overall_success else "❌"
    status_text = "PASS" if overall_success else "FAIL"
    
    lines = [
        "---",
        "id: REPORT-compliance-summary",
        "type: REPORT",
        "status: active",
        f"last_verified: {datetime.now().strftime('%Y-%m-%d')}",
        "---",
        "<!-- Language: ko -->",
        "# 📋 Compliance Summary Report",
        "",
        f"- **Timestamp**: {timestamp}",
        f"- **Overall Status**: {status_icon} **{status_text}**",
        "",
        "## 📂 Domain Results",
        "",
        "| Domain | Status | Commands |",
        "| :--- | :--- | :--- |"
    ]
    
    # Sort domains for consistent report
    for domain in sorted(results.keys()):
        data = results[domain]
        domain_status = "✅ PASS" if data["success"] else "❌ FAIL"
        cmd_details = []
        for cmd, cmd_success in data["commands"].items():
            cmd_icon = "✅" if cmd_success else "❌"
            cmd_details.append(f"`{cmd}` ({cmd_icon})")
        
        lines.append(f"| {domain} | {domain_status} | {', '.join(cmd_details)} |")
    
    lines.append("\n---")
    lines.append("*Generated by compliance_guard.py*")
    
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    
    print(f"\n📝 Report generated at: {report_path}")

def main():
    parser = argparse.ArgumentParser(description="EMR 도메인 규칙 준수 검증기 (Compliance Guard)")
    parser.add_argument("domain", nargs="?", default="all", help="검증할 도메인 (예: fhir, react, ddd) 또는 'all'")
    parser.add_argument("--list", action="store_true", help="지원하는 도메인 목록 출력")
    
    args = parser.parse_args()

    if args.list:
        print("Available domains:")
        for domain in sorted(DOMAIN_MAPPING.keys()):
            print(f"  - {domain}")
        return

    targets = []
    if args.domain == "all":
        targets = sorted(list(DOMAIN_MAPPING.keys()))
    elif args.domain in DOMAIN_MAPPING:
        targets = [args.domain]
    else:
        print(f"❌ Unknown domain: {args.domain}")
        print("Use --list to see available domains.")
        sys.exit(1)

    print(f"🔍 Starting Compliance Check for: {', '.join(targets)}")
    print("=" * 50)

    overall_success = True
    results = {}

    # FastAPI 라우터 데코레이터 규격 정적 검사 수행 (all 이거나 api 또는 fastapi_router 도메인 검증 시)
    if args.domain in ["all", "api", "fastapi_router"]:
        print("\n🔍 Starting FastAPI Router @compliance_target decorator scan...")
        router_success, router_warnings, router_errors = check_fastapi_decorators("src/api")
        
        if router_warnings:
            print("\n⚠️  [WARNING] FastAPI @compliance_target 데코레이터 누락 목록 (기존 라우트):")
            for w in router_warnings:
                print(w)
                
        if router_errors:
            print("\n❌ [ERROR] FastAPI @compliance_target 데코레이터 누락 목록 (신규/수정된 라우트 - 차단됨):")
            for e in router_errors:
                print(e)
            overall_success = False
            
        results["fastapi_router_decorator"] = {
            "success": router_success,
            "commands": {
                "check_fastapi_decorators": router_success
            }
        }
        if not router_success:
            overall_success = False

    for domain in targets:
        print(f"\n📂 Domain: {domain}")
        domain_results = {"success": True, "commands": {}}
        for cmd in DOMAIN_MAPPING[domain]:
            success = run_command(cmd)
            domain_results["commands"][cmd] = success
            if not success:
                domain_results["success"] = False
                overall_success = False
        results[domain] = domain_results

    print("\n" + "=" * 50)
    print("📋 Compliance Summary Report")
    for domain in targets:
        status = "PASS" if results[domain]["success"] else "FAIL"
        icon = "✅" if status == "PASS" else "❌"
        print(f"{icon} {domain:15}: {status}")
    print("=" * 50)

    # Generate Report File
    generate_report(results, overall_success)

    if not overall_success:
        print("❌ Some compliance checks failed.")
        sys.exit(1)
    else:
        print("🎉 All compliance checks passed!")
        sys.exit(0)

if __name__ == "__main__":
    main()
