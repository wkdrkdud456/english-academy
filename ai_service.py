"""
AI 서비스 모듈 - Google Gemini API 기반 (google-genai SDK 사용)
대치앨리영어 학원 관리 시스템
"""
import json
import re
import io
import os
import base64
import traceback
from PIL import Image

try:
    from google import genai
    from google.genai import types
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("[AI] google-genai 패키지가 설치되어 있지 않습니다.")

import time

# 사용 가능한 모델 우선순위 (최신 모델 우선)
AVAILABLE_MODELS = [
    "gemini-3-flash-preview",
    "gemini-3-pro-preview",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-flash-latest",
    "gemini-pro-latest",
]

# 모델 캐시
_model_cache = {}

# 503 에러 시 재시도 대기 시간 (초)
RETRY_DELAY = 3
MAX_RETRIES = 2

def log_error(context, error):
    """에러 로깅"""
    print(f"[AI ERROR] {context}: {error}")
    traceback.print_exc()

def get_client(api_key):
    """Google GenAI 클라이언트를 생성합니다."""
    print(f"[AI] get_client 호출 - API 키: {'있음' if api_key and api_key.strip() else '없음'}")
    if not api_key or api_key.strip() == "":
        print("[AI] API 키가 비어있습니다.")
        return None
    if not GENAI_AVAILABLE:
        print("[AI] google-genai 패키지가 없습니다.")
        return None
    try:
        client = genai.Client(api_key=api_key)
        print("[AI] 클라이언트 생성 성공")
        return client
    except Exception as e:
        log_error("클라이언트 생성 실패", e)
        return None

def _is_retryable_error(error):
    """503 등 일시적 에러인지 확인"""
    error_str = str(error)
    return "503" in error_str or "UNAVAILABLE" in error_str or "overloaded" in error_str.lower() or "high demand" in error_str.lower()

def _try_models_generate(client, contents, api_key=None):
    """여러 모델을 시도하면서 generate_content 실행 (503 에러 시 재시도)"""
    cache_key = api_key or "default"
    
    # 캐시된 모델이 있으면 먼저 시도 (재시도 포함)
    if cache_key in _model_cache:
        model_name = _model_cache[cache_key]
        for retry in range(MAX_RETRIES + 1):
            try:
                print(f"[AI] 캐시된 모델 {model_name}로 시도... (시도 {retry + 1}/{MAX_RETRIES + 1})")
                response = client.models.generate_content(model=model_name, contents=contents)
                print(f"[AI] 모델 {model_name} 응답 성공")
                return response, model_name
            except Exception as e:
                if _is_retryable_error(e) and retry < MAX_RETRIES:
                    print(f"[AI] 모델 {model_name} 일시적 에러 (503), {RETRY_DELAY}초 후 재시도... ({retry + 1}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY)
                    continue
                print(f"[AI] 캐시된 모델 {model_name} 실패: {e}")
                if cache_key in _model_cache:
                    del _model_cache[cache_key]
                break
    
    # 모든 모델 순회 (503 에러 시 재시도 포함)
    for model_name in AVAILABLE_MODELS:
        for retry in range(MAX_RETRIES + 1):
            try:
                print(f"[AI] 모델 {model_name}로 시도... (시도 {retry + 1}/{MAX_RETRIES + 1})")
                response = client.models.generate_content(model=model_name, contents=contents)
                _model_cache[cache_key] = model_name
                print(f"[AI] 모델 {model_name} 사용 가능 확인!")
                return response, model_name
            except Exception as e:
                if _is_retryable_error(e) and retry < MAX_RETRIES:
                    print(f"[AI] 모델 {model_name} 일시적 에러 (503), {RETRY_DELAY}초 후 재시도... ({retry + 1}/{MAX_RETRIES})")
                    time.sleep(RETRY_DELAY)
                    continue
                print(f"[AI] 모델 {model_name} 사용 불가: {type(e).__name__}: {e}")
                break
    
    error_msg = "사용 가능한 Gemini 모델이 없습니다."
    print(f"[AI] {error_msg}")
    raise Exception(error_msg)


def extract_text_from_image(api_key, img_bytes):
    """이미지에서 텍스트 추출"""
    print(f"[AI] extract_text_from_image 호출 (이미지 크기: {len(img_bytes)} bytes)")
    client = get_client(api_key)
    if not client: 
        return None, "API 키가 설정되지 않았거나 클라이언트를 생성할 수 없습니다."
    
    try:
        response, model_name = _try_models_generate(client, [
            "Extract all text from this image accurately.",
            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg")
        ], api_key)
        text = response.text if response.text else ""
        print(f"[AI] 텍스트 추출 완료 ({len(text)} 자)")
        return text if text else "텍스트를 추출할 수 없습니다.", True if text else False
    except Exception as e:
        log_error("extract_text_from_image", e)
        return str(e), False

def process_pdf_with_ocr(api_key, pdf_bytes):
    """PDF를 Gemini에 직접 전송하여 텍스트 추출"""
    print(f"[AI] process_pdf_with_ocr 호출 (PDF 크기: {len(pdf_bytes)} bytes)")
    client = get_client(api_key)
    if not client: 
        return None, "API 키가 설정되지 않았거나 클라이언트를 생성할 수 없습니다."
    
    try:
        response, model_name = _try_models_generate(client, [
            "Extract ALL text from this PDF document accurately. Preserve the original structure including paragraphs, headings, lists, and formatting. Extract every word completely.",
            types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
        ], api_key)
        full_text = response.text if response.text else ""
        print(f"[AI] PDF 텍스트 추출 완료 ({len(full_text)} 자)")
        return full_text if full_text else None, True if full_text else False
    except Exception as e:
        log_error("process_pdf_with_ocr", e)
        return str(e), False

def extract_vocabulary(api_key, text):
    """텍스트에서 핵심 영단어 추출"""
    print(f"[AI] extract_vocabulary 호출 (텍스트 길이: {len(text)} 자)")
    client = get_client(api_key)
    if not client: 
        return {"error": "API 키가 설정되지 않았거나 클라이언트를 생성할 수 없습니다."}
    
    prompt = f"""다음 텍스트에서 핵심 영단어 최대 100개를 추출하여 JSON 배열로만 반환해줘.
각 항목은 다음 필드를 가져야 해:
- "word": 영단어
- "meaning": 한국어 뜻 (정확하고 간결하게)
- "derivatives": 파생어 배열 (예: 복수형, 동사형, 형용사형 등 최대 5개)
- "synonyms": 유의어 배열 (같은 의미를 가진 영단어 최대 5개)

다른 설명이나 텍스트 없이 순수 JSON 배열만 출력해.
배열이 없으면 빈 배열 []을 반환해.
중복된 단어는 제외해줘.

텍스트:
{text[:15000]}"""
    try:
        response, model_name = _try_models_generate(client, prompt, api_key)
        res_text = response.text
        print(f"[AI] AI 응답 수신 ({len(res_text)} 자)")
        # JSON 블록 추출
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0]
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0]
        match = re.search(r'\[.*\]', res_text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            print(f"[AI] 단어 추출 완료: {len(result)}개")
            return result if isinstance(result, list) else []
        print(f"[AI] JSON 배열을 찾을 수 없음")
        return []
    except Exception as e:
        log_error("extract_vocabulary", e)
        return {"error": f"단어 추출 중 오류: {str(e)}"}

def analyze_exam_multi(api_key, files_info, week):
    """시험지 이미지를 분석하여 채점 결과 반환"""
    print(f"[AI] analyze_exam_multi 호출 (파일 수: {len(files_info)}, 주차: {week})")
    client = get_client(api_key)
    if not client: 
        return {"error": "API 키가 설정되지 않았거나 클라이언트를 생성할 수 없습니다."}
    
    prompt = f"""
    이 시험지({week}) 이미지를 분석해서 아래 JSON 형식으로만 답변해줘. 다른 설명은 하지마.
    전체 문항 수를 정확히 세고, 각 영역별로 몇 문항인지 정확히 구분해줘.
    각 문제에 대해 유형과 간단한 설명을 포함해줘.
    
    total_questions과 area_questions의 합이 일치하도록 해줘.
    
    {{
        "total_questions": 전체 문항 수 (숫자, 정확히 세기),
        "correct_answers": AI가 판단한 정답 문항 수 (숫자),
        "incorrect_answers": 오답 문항 수 (숫자),
        "area_questions": {{
            "어휘": 이 영역의 문항 수 (숫자),
            "문법": 이 영역의 문항 수 (숫자),
            "독해": 이 영역의 문항 수 (숫자),
            "듣기": 이 영역의 문항 수 (숫자)
        }},
        "area_accuracy_percent": {{
            "어휘": 0~100 사이 정답률,
            "문법": 0~100 사이 정답률,
            "독해": 0~100 사이 정답률,
            "듣기": 0~100 사이 정답률
        }},
        "questions": [
            {{
                "number": 문제 번호 (1부터 시작),
                "area": "영역 (어휘/문법/독해/듣기 중 하나)",
                "type": "문제 유형 (예: 어휘 선택, 문법 변환, 독해 파악, 청취 이해 등)",
                "correct": true/false (AI가 판단한 정답 여부),
                "summary": "문제에 대한 간략한 설명 (한글, 15자 이내)"
            }}
        ],
        "weakness_analysis": "취약점 분석 요약 (한글)",
        "prescription": "학습 처방 (한글)"
    }}
    """
    
    contents = [prompt]
    for f in files_info:
        ftype = f.get('type', 'image')
        fdata = f.get('bytes', b'')
        print(f"[AI] 파일 추가: 타입={ftype}, 크기={len(fdata)} bytes")
        if ftype == 'pdf': 
            print(f"[AI] PDF 파일은 건너뜀 (이미지 위주)")
            continue
        contents.append(types.Part.from_bytes(data=fdata, mime_type="image/jpeg"))
        
    print(f"[AI] 총 {len(contents)}개 contents 전송")
    try:
        response, model_name = _try_models_generate(client, contents, api_key)
        res_text = response.text
        print(f"[AI] AI 응답 수신 ({len(res_text)} 자)")
        
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0]
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0]
            
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            print(f"[AI] 분석 결과 파싱 성공")
            return result
        else:
            print(f"[AI] JSON 형식을 찾을 수 없음: {res_text[:200]}")
            return {"error": f"AI 응답에서 JSON 형식을 찾을 수 없습니다. 응답: {res_text[:200]}..."}
    except Exception as e:
        log_error("analyze_exam_multi", e)
        return {"error": f"AI 분석 중 시스템 오류 발생: {str(e)}"}

def generate_weekly_report(api_key, student_info, attendance, history, scores):
    """주간 리포트 생성"""
    client = get_client(api_key)
    if not client: 
        return "리포트 생성 실패: API 키가 설정되지 않았거나 클라이언트를 생성할 수 없습니다."
    
    prompt = f"학생 {student_info['name']}의 이번주 기록(출석:{attendance}, 활동:{history}, 성적:{scores})을 바탕으로 학부모님께 보낼 정중한 주간 리포트를 작성해줘. 따뜻하고 전문적인 톤으로 3~5줄 정도로 써줘."
    try:
        response, model_name = _try_models_generate(client, prompt, api_key)
        return response.text if response.text else "리포트 생성 실패"
    except Exception as e: 
        return f"리포트 생성 중 오류 발생: {str(e)}"

def generate_monthly_summary(api_key, student_info, avg_scores):
    """월간 총평 생성"""
    client = get_client(api_key)
    if not client: 
        return "총평 생성 실패: API 키가 설정되지 않았거나 클라이언트를 생성할 수 없습니다."
    
    prompt = f"학생 {student_info['name']}의 한달 평균 성적({avg_scores})을 분석해서 4대영역별 성과와 앞으로의 학습 방향에 대해 3줄 정도의 총평을 써줘. 매번 다른 문구를 사용해서 정성스럽게 작성해줘."
    try:
        response, model_name = _try_models_generate(client, prompt, api_key)
        return response.text if response.text else "성적이 향상되고 있으며 꾸준한 학습이 필요합니다."
    except Exception as e: 
        return f"성적이 향상되고 있으며 꾸준한 학습이 필요합니다. (오류: {str(e)})"