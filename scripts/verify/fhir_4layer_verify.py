#!/usr/bin/env python3
import importlib
import json
import os
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import requests

from scripts.observability.api_errors import api_error_timer

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.shared.fhir_compatibility import sanitize_to_r4
from src.shared.fhir_validator import FHIRValidator


def get_fhir_model(resource_type: str):
    """FHIR 리소스 타입에 해당하는 Pydantic 모델을 동적으로 로드합니다."""
    try:
        # fhir.resources.R4B 패키지에서 동적 로드 시도
        module_name = f"fhir.resources.R4B.{resource_type.lower()}"
        module = importlib.import_module(module_name)
        return getattr(module, resource_type)
    except (ImportError, AttributeError):
        # 일부 리소스는 파일명과 클래스명이 다를 수 있으므로 예외 처리 (예: MedicationRequest -> medicationrequest)
        try:
            module_name = f"fhir.resources.R4B.{resource_type.lower().replace('_', '')}"
            module = importlib.import_module(module_name)
            return getattr(module, resource_type)
        except:
            return None

@dataclass
class ValidationReport:
    layer1_pydantic: bool = False
    layer1_error: str | None = None
    layer2_sanitize: bool = False
    layer2_error: str | None = None  # Corrected field name
    layer3_java_validator: bool = False
    layer3_errors: list[Any] = field(default_factory=list)
    layer4_hapi_upload: bool = False
    layer4_error: str | None = None
    is_success: bool = False

def validate_fhir_4layer(resource_dict: dict[str, Any], snowstorm_url: str | None = None) -> ValidationReport:
    if snowstorm_url is None:
        snowstorm_url = os.getenv("SNOWSTORM_URL", "http://localhost:8080/fhir")

    report = ValidationReport()
    resource_type = resource_dict.get("resourceType")

    if not resource_type:
        report.layer1_error = "Missing resourceType"
        return report

    # Layer 1: Pydantic Structural Validation
    try:
        model_cls = get_fhir_model(resource_type)
        if model_cls:
            model_cls(**resource_dict)
            report.layer1_pydantic = True
        else:
            report.layer1_error = f"Resource type {resource_type} not found in fhir.resources.R4B"
            return report
    except Exception as e:
        report.layer1_error = str(e)
        return report

    # Layer 2: Sanitize (R4B -> R4)
    try:
        sanitized = sanitize_to_r4(resource_dict)
        report.layer2_sanitize = True
    except Exception as e:
        report.layer2_error = f"Sanitize failed: {e}"
        return report

    # Layer 3: HL7 Java Validator
    try:
        validator = FHIRValidator()
        with tempfile.NamedTemporaryFile(suffix=".json", mode="w", delete=False) as tmp:
            json.dump(sanitized, tmp)
            tmp_path = tmp.name

        try:
            # Use snowstorm_url as terminology server (-tx)
            res = validator.validate(tmp_path, tx_url=snowstorm_url)
            report.layer3_java_validator = res.is_valid
            report.layer3_errors = [vars(e) for e in res.errors]
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

        if not report.layer3_java_validator:
            return report
    except Exception as e:
        report.layer3_errors.append({"severity": "error", "message": f"Validator crash: {e}"})
        return report

    # Layer 4: HAPI/Snowstorm Upload
    try:
        # For Snowstorm, we use POST [base]/[resourceType]
        with api_error_timer("snowstorm", "POST", f"{snowstorm_url}/{resource_type}"):
            resp = requests.post(f"{snowstorm_url}/{resource_type}", json=sanitized, timeout=10)
        if resp.status_code in (200, 201):
            report.layer4_hapi_upload = True
            report.is_success = True
        else:
            report.layer4_error = f"HAPI Upload failed with status {resp.status_code}: {resp.text}"
    except Exception as e:
        report.layer4_error = f"HAPI Connection failed: {e}"

    return report

def main():
    if len(sys.argv) < 2:
        print("Usage: fhir_4layer_verify.py <resource_json_path>")
        sys.exit(1)

    file_path = sys.argv[1]
    with open(file_path) as f:
        resource_dict = json.load(f)

    report = validate_fhir_4layer(resource_dict)
    print(json.dumps(report.__dict__, indent=2, default=lambda x: str(x)))

    if not report.is_success:
        sys.exit(1)

if __name__ == "__main__":
    main()
