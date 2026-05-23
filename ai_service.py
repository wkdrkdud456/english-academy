"""
AI 서비스 모듈 - Google Gemini API (gemini-2.5-flash / gemini-2.5-pro) 기반
앨리영어 학원 관리 시스템

스캔된 PDF OCR 지원: PDF 페이지를 이미지로 변환 → Gemini Vision으로 텍스트 추출
"""
import json
import re
import io
import os
import base64
from PIL import Image

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False


def get_model(api_key, model_name="gemini-2.5-flash"):
    """Gemini 모델 인스턴스 생성"""
    if not api_key or api_key == "" or api_key == "YOUR_GEMINI_API_KEY":
        return None
    if not GENAI_AVAILABLE:
        return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def extract_text_from_scanned_pdf(api_key, pdf_bytes):
    """
    스캔된 PDF에서 OCR로 텍스트 추출 (Gemini Vision)
    pypdfium2로 PDF 페이지를 이미지로 변환 → 하나의 이미지로 합쳐서 Gemini Vision 1회 호출
    """
    try:
        import pypdfium2 as pdfium
    except ImportError:
        return None, "pypdfium2 라이브러리가 필요합니다. `pip install pypdfium2`를 실행해주세요."

    model = get_model(api_key, "gemini-2.5-flash")
    if not model:
        return None, "Gemini API 키가 유효하지 않습니다."

    try:
        pdf_doc = pdfium.PdfDocument(pdf_bytes)
        page_images = []
        for page_idx in range(min(len(pdf_doc), 10)):
            page = pdf_doc[page_idx]
            bitmap = page.render(scale=150/72)
            pil_image = bitmap.to_pil()
            page_images.append(pil_image)
        pdf_doc.close()

        if not page_images:
            return None, "PDF 페이지를 읽을 수 없습니다."

        total_height = sum(im.height for im in page_images)
        max_width = max(im.width for im in page_images)
        combined = Image.new("RGB", (max_width, total_height), (255, 255, 255))
        y_offset = 0
        for im in page_images:
            combined.paste(im, (0, y_offset))
            y_offset += im.height

        img_buffer = io.BytesIO()
        combined.save(img_buffer, format="JPEG", quality=85)
        img_bytes = img_buffer.getvalue()

        response = model.generate_content([
            "이 이미지는 여러 페이지로 구성된 문서입니다. 이미지에 있는 모든 텍스트를 순서대로 그대로 추출해주세요. 영어와 한국어 모두 포함하여 최대한 정확하게 읽어주세요. 마크다운 없이 순수 텍스트만 반환하세요.",
            {"mime_type": "image/jpeg", "data": img_bytes}
        ])
        all_text = response.text.strip()
        if not all_text:
            return None, "PDF에서 텍스트를 추출할 수 없습니다."
        return all_text, None

    except Exception as e:
        error_str = str(e)
        if "429" in error_str or "quota" in error_str.lower():
            return None, "⚠️ Gemini API 일일 할당량이 초과되었습니다.\n해결: ai.google.dev에서 결제 등록 또는 내일 재시도"
        return None, f"OCR 처리 중 오류: {str(e)}"


def extract_text_from_pdf(pdf_bytes):
    """일반 PDF에서 텍스트 추출 (pdfplumber)"""
    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            text_parts = []
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
            if text_parts:
                return "\n".join(text_parts)
    except:
        pass
    return None


def extract_text_from_image(api_key, image_bytes):
    """이미지에서 텍스트 추출 (Gemini Vision OCR)"""
    model = get_model(api_key, "gemini-2.5-flash")
    if not model:
        return None, "API 키가 유효하지 않습니다."
    try:
        response = model.generate_content([
            "이 이미지에 있는 모든 텍스트를 그대로 추출해주세요. 영어와 한국어 모두 포함. 마크다운 없이 순수 텍스트만.",
            {"mime_type": "image/jpeg", "data": image_bytes}
        ])
        text = response.text.strip()
        return text if text else None, None
    except Exception as e:
        return None, str(e)


# ─── 단어장 추출 (50개) ─────────────────────────────────

def extract_vocabulary(api_key, pdf_text):
    """PDF 텍스트에서 핵심 중요 단어 50개 추출 (JSON)"""
    model = get_model(api_key, "gemini-2.5-flash")
    if not model:
        return None

    prompt = f"""당신은 영어 어휘 전문가입니다. 다음 영어 지문에서 핵심 중요 단어 50개를 엄선해주세요.

중요도 순으로 정렬해서 50개를 뽑아주세요.
각 단어마다 [단어, 뜻, 유의어, 반의어, 파생어와 품사] 정보를 포함한 JSON 배열로 반환해주세요.
반드시 아래 JSON 형식만 반환하고 다른 텍스트(마크다운 코드블록 포함)는 절대 포함하지 마세요.

[
  {{
    "word": "example",
    "meaning": "예시",
    "synonyms": "instance, sample",
    "antonyms": "none",
    "derivatives": "exemplify(v), exemplary(adj)"
  }},
  ...
]

지문:
{pdf_text[:12000]}
"""
    try:
        response = model.generate_content(prompt)
        result = response.text.strip()
        result = re.sub(r'```json\s*|\s*```', '', result)
        result = result.strip()
        if result.startswith('[') and result.endswith(']'):
            return json.loads(result)
        else:
            match = re.search(r'\[.*?\]', result, re.DOTALL)
            if match:
                return json.loads(match.group())
            return {"error": "JSON 파싱 실패", "raw_result": result}
    except Exception as e:
        return {"error": str(e), "raw_result": result if 'result' in locals() else ""}


# ─── 시험지 이미지/PDF 분석 (멀티파일 + 주차별) ─────────

def analyze_exam_multi(api_key, files_info, week_label=""):
    """
    여러 이미지/PDF 시험지 분석 (Gemini Vision)
    
    files_info: [{"type": "image"/"pdf", "bytes": ...}, ...]
    week_label: "1주차" 같은 문자열
    """
    model = get_model(api_key, "gemini-2.5-flash")
    if not model:
        return None

    # 모든 파일에서 텍스트/이미지 추출
    all_images = []
    all_texts = []
    
    for finfo in files_info:
        if finfo["type"] == "image":
            all_images.append(finfo["bytes"])
        elif finfo["type"] == "pdf":
            # PDF → 이미지 변환 시도
            try:
                import pypdfium2 as pdfium
                pdf_doc = pdfium.PdfDocument(finfo["bytes"])
                for page_idx in range(min(len(pdf_doc), 5)):
                    page = pdf_doc[page_idx]
                    bitmap = page.render(scale=150/72)
                    pil_image = bitmap.to_pil()
                    buf = io.BytesIO()
                    pil_image.save(buf, format="JPEG", quality=85)
                    all_images.append(buf.getvalue())
                pdf_doc.close()
            except:
                all_texts.append("[PDF 변환 실패]")

    # 내용이 너무 많으면 텍스트 우선 추출 후 분석
    if len(all_images) > 3:
        # 여러 이미지 → 하나로 합치기
        pil_images = []
        for img_bytes in all_images:
            try:
                pil_images.append(Image.open(io.BytesIO(img_bytes)).convert("RGB"))
            except:
                pass
        
        if pil_images:
            total_h = sum(im.height for im in pil_images)
            max_w = max(im.width for im in pil_images)
            combined = Image.new("RGB", (max_w, total_h), (255, 255, 255))
            y_off = 0
            for im in pil_images:
                combined.paste(im, (0, y_off))
                y_off += im.height
            buf = io.BytesIO()
            combined.save(buf, format="JPEG", quality=80)
            all_images = [buf.getvalue()]
    
    week_context = f" (주차: {week_label})" if week_label else ""
    
    prompt = f"""이 영어 시험지 이미지{week_context}를 분석해주세요.

다음 JSON 형식으로만 응답해주세요 (마크다운 코드블록 없이 순수 JSON만):
{{
  "week": "{week_label}",
  "total_questions": 전체 문항 수,
  "correct_count": 정답 문항 수,
  "incorrect_count": 오답 문항 수,
  "accuracy_by_area": {{
    "어휘": {{"total": 총문항, "correct": 정답문항}},
    "문법": {{"total": 총문항, "correct": 정답문항}},
    "독해": {{"total": 총문항, "correct": 정답문항}},
    "듣기": {{"total": 총문항, "correct": 정답문항}}
  }},
  "area_accuracy_percent": {{
    "어휘": 정답률(숫자),
    "문법": 정답률(숫자),
    "독해": 정답률(숫자),
    "듣기": 정답률(숫자)
  }},
  "weakness_analysis": "이 학생의 취약점 분석 상세 코멘트 (한국어)",
  "prescription": "취약점 보완을 위한 학습 처방전 (한국어)"
}}"""

    try:
        contents = [prompt]
        for img_bytes in all_images[:3]:  # 최대 3장
            contents.append({"mime_type": "image/jpeg", "data": img_bytes})
        for t in all_texts:
            contents.append(t)

        response = model.generate_content(contents)
        result = response.text.strip()
        result = re.sub(r'```json\s*|\s*```', '', result)
        return json.loads(result)
    except Exception as e:
        return {"error": str(e), "raw_result": result if 'result' in locals() else ""}


# (하위 호환성)
def analyze_exam_image(api_key, image_bytes):
    """단일 이미지 분석 (레거시)"""
    return analyze_exam_multi(api_key, [{"type": "image", "bytes": image_bytes}])


# ─── 학교 기출 PDF 분석 ─────────────────────────────────

def analyze_school_exam_pdf(api_key, pdf_text):
    """학교 기출 시험지 PDF 분석"""
    model = get_model(api_key, "gemini-2.5-flash")
    if not model:
        return None

    prompt = f"""다음 학교 기출 시험지 텍스트를 분석하여 문항 유형별 비율을 JSON으로 반환해주세요.

다음 형식으로만 응답 (마크다운 코드블록 없이 순수 JSON만):
{{
  "analysis": {{
    "어휘": 비율_숫자,
    "문법": 비율_숫자,
    "독해": 비율_숫자,
    "듣기": 비율_숫자
  }},
  "total_questions": 전체_문항_수,
  "key_features": "이 시험지의 주요 특징 요약 (한국어)",
  "difficulty": "상/중/하",
  "notable_topics": ["두드러지는 주제1", "주제2"]
}}

시험지 텍스트:
{pdf_text[:10000]}
"""
    try:
        response = model.generate_content(prompt)
        result = response.text.strip()
        result = re.sub(r'```json\s*|\s*```', '', result)
        return json.loads(result)
    except Exception as e:
        return {"error": str(e), "raw_result": result if 'result' in locals() else ""}


# ─── 학교별 트렌드 리포트 ──────────────────────────────

def generate_trend_report(api_key, school_name, exam_data_list):
    """학교별 누적 데이터 기반 트렌드 리포트 생성"""
    model = get_model(api_key, "gemini-2.5-flash")
    if not model:
        return None, None

    exam_summary = json.dumps(exam_data_list, ensure_ascii=False, indent=2)
    prompt = f"""다음은 {school_name}의 역대 시험 데이터입니다.

{exam_summary}

위 데이터를 기반으로 다음 두 가지를 JSON으로 반환해주세요:

1. trend_data: 연도/학기별 유형별 비율 변화를 보여주는 데이터
2. report: "다음 시험 대비 전략 보고서" 형식의 상세 분석문 (한국어, 500자 이상)

JSON 형식 (마크다운 코드블록 없이 순수 JSON만):
{{
  "trend_data": [
    {{"year": "2025", "semester": "1학기", "어휘": 25, "문법": 30, "독해": 35, "듣기": 10}},
    ...
  ],
  "report": "전략 보고서 내용..."
}}
"""
    try:
        response = model.generate_content(prompt)
        result = response.text.strip()
        result = re.sub(r'```json\s*|\s*```', '', result)
        data = json.loads(result)
        return data.get("trend_data", []), data.get("report", "")
    except Exception as e:
        return None, f"리포트 생성 중 오류: {str(e)}"


# ─── 주간 리포트 생성 ──────────────────────────────────

def generate_weekly_report(api_key, student_info, attendance_records, history_records, exam_results):
    """주간 리포트 생성"""
    model = get_model(api_key, "gemini-2.5-flash")
    if not model:
        return None

    context = f"""
학생 정보: {json.dumps(student_info, ensure_ascii=False)}
최근 출석 기록: {json.dumps(attendance_records, ensure_ascii=False)}
금주 특이사항: {json.dumps(history_records, ensure_ascii=False)}
시험 진단 결과: {json.dumps(exam_results, ensure_ascii=False)}
"""
    prompt = f"""다음은 한 주간의 학원 데이터입니다. 학부모님께 보낼 주간 알림장을 정중하고 체계적으로 작성해주세요.

{context}

포함할 내용:
- 이번 주 출석 현황 요약
- 학습 태도 및 과제 수행 평가
- 시험 결과가 있다면 분석 피드백
- 칭찬할 점과 격려 메시지
- 다음 주 학습 계획 안내

따뜻하고 전문적인 톤으로 작성해주세요. (한국어, 300~500자)
"""
    try:
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"리포트 생성 중 오류: {str(e)}"


# ─── PDF OCR 통합 처리 ─────────────────────────────────

def process_pdf_with_ocr(api_key, pdf_bytes):
    """
    PDF 지능 처리: pdfplumber 먼저, 실패시 Gemini OCR
    """
    text = extract_text_from_pdf(pdf_bytes)
    if text and len(text.strip()) > 50:
        return text, False
    ocr_text, error = extract_text_from_scanned_pdf(api_key, pdf_bytes)
    if ocr_text:
        return ocr_text, True
    return None, error