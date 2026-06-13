#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# <!-- Language: ko -->

import os
import sys
import re

# Vitest가 허용하는 기본 전역 객체 및 JS/TS 키워드
BUILTINS = {
    'true', 'false', 'null', 'undefined', 'return', 'const', 'let', 'var',
    'function', 'if', 'else', 'for', 'while', 'do', 'switch', 'case', 'break',
    'continue', 'throw', 'try', 'catch', 'finally', 'new', 'delete', 'typeof',
    'instanceof', 'void', 'in', 'of', 'this', 'class', 'extends', 'import',
    'export', 'default', 'as', 'from', 'yield', 'await', 'async', 'super',
    'vi', 'vitest', 'jest', 'console', 'window', 'document', 'process', 'global',
    'describe', 'it', 'test', 'expect', 'beforeEach', 'afterEach', 'beforeAll', 'afterAll',
    'Object', 'Array', 'String', 'Number', 'Boolean', 'Promise', 'Error', 'Map', 'Set',
    'JSON', 'Math', 'RegExp', 'Date', 'React', 'any', 'string', 'number', 'boolean', 'void',
    'unknown', 'never', 'Symbol', 'WeakMap', 'WeakSet', 'globalThis',
    'HTMLElement', 'HTMLDivElement', 'ComponentType', 'FC', 'ReactNode', 'HTMLAttributes',
    'Record', 'Partial', 'Pick', 'Omit', 'Required', 'Readonly', 'CSSProperties',
    'URLSearchParams', 'fetch', 'Headers', 'Request', 'Response', 'setTimeout', 'clearTimeout',
    'setInterval', 'clearInterval', 'AbortController', 'Element', 'Event', 'MouseEvent'
}

def clean_code(code: str) -> str:
    """주석, JSX 태그/속성, 타입 캐스팅, 물음표(옵셔널) 및 문자열 리터럴을 마스킹하여 순수 식별자만 남깁니다."""
    # 1. Multi-line 주석 제거
    code = re.sub(r'/\*.*?\*/', ' ', code, flags=re.DOTALL)
    # 2. Single-line 주석 제거
    code = re.sub(r'//.*', ' ', code)
    
    # 3. 옵셔널 물음표 제거 (타입 선언 내 key?: type 형태를 key: type으로 전환하여 속성 키 필터 통과 유도)
    code = code.replace('?', ' ')
    
    # 4. TS 'as Type' 캐스팅 제거
    code = re.sub(r'\bas\s+(?:readonly\s+)?[a-zA-Z_][a-zA-Z0-9_]*(?:\[\])?', ' ', code)
    
    # 5. JSX 속성명 (attr=) 제거
    code = re.sub(r'\b[a-zA-Z_][a-zA-Z0-9_-]*\s*=\s*', ' ', code)
    # 6. JSX 태그명 (</tag or <tag) 제거
    code = re.sub(r'</?[a-zA-Z_][a-zA-Z0-9_-]*', ' ', code)
    
    # 7. 템플릿 리터럴 내 식별자 구출 (${var} -> + var +)
    code = re.sub(r'\$\{([^}]+)\}', r' + \1 + ', code)
    
    # 8. 문자열 리터럴 제거
    code = re.sub(r'\'[^\']*\'', '""', code)
    code = re.sub(r'"[^"]*"', '""', code)
    code = re.sub(r'`[^`]*`', '""', code, flags=re.DOTALL)
    
    return code

def extract_params(params_text: str) -> set:
    """타입 어노테이션이 제거된 순수 함수 매개변수를 추출합니다."""
    params_set = set()
    
    # 줄바꿈을 제거하여 멀티라인 타입 선언 정화 용이화
    params_text = params_text.replace('\n', ' ').replace('\r', ' ')
    
    # 옵셔널 물음표 제거 (param?: type -> param: type)
    params_text = params_text.replace('?', '')
    
    # 1. 인라인 중괄호 타입 ': { ... }' 제거
    while True:
        match = re.search(r':\s*\{', params_text)
        if not match:
            break
        open_braces = 1
        i = match.end()
        while i < len(params_text) and open_braces > 0:
            char = params_text[i]
            if char == '{':
                open_braces += 1
            elif char == '}':
                open_braces -= 1
            i += 1
        params_text = params_text[:match.start()] + params_text[i:]
        
    # 2. 일반 콜론 타입 ': TypeName' 제거
    params_text = re.sub(r':\s*[^,=)]+', '', params_text)
    
    # 3. 스프레드 연산자 제거
    params_text = params_text.replace('...', '')
    
    # 4. 식별자 추출
    for word in re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', params_text):
        params_set.add(word)
        
    return params_set

def find_local_declarations(code: str) -> set:
    """팩토리 함수 내부에서 정의된 로컬 변수/함수/매개변수를 정밀 수집합니다."""
    locals_set = set()
    
    # 1. 단일 변수 선언 (const x =, let x =, var x =)
    for match in re.finditer(r'\b(?:const|let|var)\s+([a-zA-Z_][a-zA-Z0-9_]*)\b', code):
        locals_set.add(match.group(1))
        
    # 2. 구조분해 할당 (const { a, b: c } = ...)
    for match in re.finditer(r'\b(?:const|let|var)\s*\{\s*([^}]+)\s*\}', code):
        inner = match.group(1)
        for part in re.split(r'[, \n\t]+', inner):
            part = part.strip()
            if not part:
                continue
            # 옵셔널 변수 물음표 제거
            part = part.replace('?', '')
            if ':' in part:
                val = part.split(':')[-1].strip()
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', val):
                    locals_set.add(val)
            else:
                if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', part):
                    locals_set.add(part)
                    
    # 3. 배열 구조분해 할당 (const [ a, b ] = ...)
    for match in re.finditer(r'\b(?:const|let|var)\s*\[\s*([^\]]+)\s*\]', code):
        inner = match.group(1)
        for part in re.split(r'[, \n\t]+', inner):
            part = part.strip().replace('?', '')
            if re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', part):
                locals_set.add(part)

    # 4. 함수 선언 (function foo(...) {})
    for match in re.finditer(r'\bfunction\s+([a-zA-Z_][a-zA-Z0-9_]*)\b', code):
        locals_set.add(match.group(1))
        
    # 5. 모든 형태의 함수 매개변수 괄호 탐색 및 분석 (정교한 bracket matching)
    for match in re.finditer(r'\(', code):
        start_idx = match.start()
        open_parens = 1
        i = match.end()
        while i < len(code) and open_parens > 0:
            char = code[i]
            if char == '(':
                open_parens += 1
            elif char == ')':
                open_parens -= 1
            i += 1
        if open_parens == 0:
            parens_text = code[start_idx+1:i-1]
            tail = code[i:].strip()
            if tail.startswith('=>') or tail.startswith('{'):
                locals_set.update(extract_params(parens_text))
                
    # 6. 단일 인자 화살표 함수 (x =>)
    for match in re.finditer(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=>', code):
        locals_set.add(match.group(1))

    return locals_set

def analyze_file(filepath: str) -> list:
    """파일 내 vi.mock 선언을 스캔하여 Lexical Scope 위반을 탐지합니다."""
    violations = []
    
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
        
    # vi.mock( 선언 찾기
    for match in re.finditer(r'\bvi\.mock\s*\(', content):
        start_idx = match.start()
        line_num = content[:start_idx].count('\n') + 1
        
        # bracket matching을 통한 vi.mock(...) 전체 호출 추출
        open_parens = 1
        i = match.end()
        while i < len(content) and open_parens > 0:
            char = content[i]
            if char == '(':
                open_parens += 1
            elif char == ')':
                open_parens -= 1
            i += 1
            
        full_call = content[start_idx:i]
        
        # 팩토리 함수(두 번째 인자) 추출
        factory_match = re.search(r'\bvi\.mock\s*\(\s*(?:\'[^\']*\'|"[^"]*"|`[^`]*`)\s*,\s*', full_call)
        if not factory_match:
            continue
            
        factory_code = full_call[factory_match.end():-1].strip()
        
        # 팩토리 내 식별자 검증을 위해 마스킹 수행
        clean_factory = clean_code(factory_code)
        
        # 팩토리 내부 로컬 선언 수집
        locals_set = find_local_declarations(clean_factory)
        
        # 팩토리 내부의 모든 식별자 추출
        # (객체 키 및 점 뒤의 멤버 속성명 제외)
        all_identifiers = re.findall(r'(?<!\.)\b([a-zA-Z_][a-zA-Z0-9_]*)\b(?!\s*:)', clean_factory)
        
        file_violations = set()
        for idx in all_identifiers:
            # 1. 예약어 및 전역 내장 빌트인 제외
            if idx in BUILTINS:
                continue
            # 2. 로컬 선언 변수 제외
            if idx in locals_set:
                continue
            # 3. mock 접두사 예외 규칙 허용
            if idx.lower().startswith('mock'):
                continue
            # 4. 숫자 등의 예외 제외
            if idx.isdigit():
                continue
                
            file_violations.add(idx)
            
        if file_violations:
            violations.append({
                'line': line_num,
                'variables': sorted(list(file_violations)),
                'snippet': factory_code[:100].replace('\n', ' ') + ('...' if len(factory_code) > 100 else '')
            })
            
    return violations

def main():
    base_dir = "apps/renderer/tests"
    if not os.path.isdir(base_dir):
        print(f"오류: 대상 디렉토리 '{base_dir}'가 존재하지 않습니다.")
        sys.exit(0)
        
    print(f"🔍 Vitest/Jest 모킹 Lexical Scope 제약 조건 검사 시작: {base_dir}")
    
    total_files = 0
    total_violations = 0
    
    for root, _, files in os.walk(base_dir):
        for file in files:
            if file.endswith(('.test.ts', '.test.tsx', '.spec.ts', '.spec.tsx')):
                filepath = os.path.join(root, file)
                total_files += 1
                
                violations = analyze_file(filepath)
                if violations:
                    print(f"\n❌ 위반 감지: {filepath}")
                    for v in violations:
                        print(f"  - [Line {v['line']}] 외부 Lexical 변수 직접 참조: {', '.join(v['variables'])}")
                        print(f"    코드: {v['snippet']}")
                    total_violations += len(violations)
                    
    print("\n" + "=" * 50)
    if total_violations > 0:
        print(f"❌ 검사 실패: {total_files}개 파일 중 {total_violations}건의 Lexical Scope 위반 감지!")
        sys.exit(1)
    else:
        print(f"✅ 검사 성공: {total_files}개 파일 모두 호이스팅 제약 조건 준수 완료.")
        sys.exit(0)

if __name__ == '__main__':
    main()
