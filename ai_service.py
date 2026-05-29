"""
AI 서비스 모듈 - Google Gemini API 기반
대치앨리영어 학원 관리 시스템
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

def get_model(api_key, model_name="gemini-1.5-flash"):
    if not api_key or api_key == "": return None
    if not GENAI_AVAILABLE: return None
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def extract_text_from_image(api_key, img_bytes):
    """이미지에서 텍스트 추출"""
    model = get_model(api_key)
    if not model: return None, "API 키가 없습니다."
    try:
        response = model.generate_content([
            "Extract all text from this image accurately.",
            {"mime_type": "image/jpeg", "data": img_bytes}
        ])
        return response.text, True
    except Exception as e:
        return str(e), False

def process_pdf_with_ocr(api_key, pdf_bytes):
    """PDF를 이미지로 변환하여 Gemini로 텍스트 추출"""
    model = get_model(api_key)
    if not model: return None, "API 키가 없습니다."
    
    try:
        import pypdfium2 as pdfium
        pdf = pdfium.PdfDocument(pdf_bytes)
        full_text = ""
        for page in pdf:
            bitmap = page.render(scale=2)
            pil_image = bitmap.to_pil()
            img_byte_arr = io.BytesIO()
            pil_image.save(img_byte_arr, format='PNG')
            response = model.generate_content([
                "Extract all text from this image accurately.",
                {"mime_type": "image/png", "data": img_byte_arr.getvalue()}
            ])
            full_text += response.text + "\n"
        return full_text, True
    except Exception as e:
        return str(e), False

def extract_vocabulary(api_key, text):
    model = get_model(api_key)
    if not model: return {"error": "API 키가 설정되지 않았습니다."}
    
    prompt = f"""다음 텍스트에서 핵심 영단어 30개를 추출하여 JSON 배열로만 반환해줘.
각 항목은 "word"(영단어), "meaning"(뜻), "derivatives"(파생어) 필드를 가져.
다른 설명이나 텍스트 없이 순수 JSON 배열만 출력해.
배열이 없으면 빈 배열 []을 반환해.

텍스트:
{text[:10000]}"""
    try:
        response = model.generate_content(prompt)
        res_text = response.text
        # JSON 블록 추출
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0]
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0]
        match = re.search(r'\[.*\]', res_text, re.DOTALL)
        if match:
            result = json.loads(match.group())
            return result if isinstance(result, list) else []
        return []
    except Exception as e:
        return {"error": f"단어 추출 중 오류: {str(e)}"}

def analyze_exam_multi(api_key, files_info, week):
    model = get_model(api_key)
    if not model: return {"error": "API 키가 설정되지 않았거나 모델을 불러올 수 없습니다."}
    
    prompt = f"""
    이 시험지({week}) 이미지를 분석해서 아래 JSON 형식으로만 답변해줘. 다른 설명은 하지마.
    {{
        "total_questions": 전체 문항 수 (숫자),
        "correct_answers": AI가 판단한 정답 문항 수 (숫자),
        "incorrect_answers": 오답 문항 수 (숫자),
        "area_accuracy_percent": {{
            "어휘": 0~100 사이 숫자,
            "문법": 0~100 사이 숫자,
            "독해": 0~100 사이 숫자,
            "듣기": 0~100 사이 숫자
        }},
        "weakness_analysis": "취약점 분석 요약 (한글)",
        "prescription": "학습 처방 (한글)"
    }}
    """
    
    contents = [prompt]
    for f in files_info:
        # mime_type을 파일 확장자에 따라 유연하게 설정
        mime = "image/jpeg"
        if f.get('type') == 'pdf': continue # PDF는 별도 처리 필요하지만 여기선 이미지 위주
        contents.append({"mime_type": mime, "data": f['bytes']})
        
    try:
        response = model.generate_content(contents)
        res_text = response.text
        
        # JSON 블록 추출 로직 강화
        if "```json" in res_text:
            res_text = res_text.split("```json")[1].split("```")[0]
        elif "```" in res_text:
            res_text = res_text.split("```")[1].split("```")[0]
            
        match = re.search(r'\{.*\}', res_text, re.DOTALL)
        if match:
            return json.loads(match.group())
        else:
            return {"error": f"AI 응답에서 JSON 형식을 찾을 수 없습니다. 응답 내용: {res_text[:100]}..."}
    except Exception as e:
        return {"error": f"AI 분석 중 시스템 오류 발생: {str(e)}"}

def generate_weekly_report(api_key, student_info, attendance, history, scores):
    model = get_model(api_key)
    if not model: return "리포트 생성 실패"
    
    prompt = f"학생 {student_info['name']}의 이번주 기록(출석:{attendance}, 활동:{history}, 성적:{scores})을 바탕으로 학부모님께 보낼 정중한 주간 리포트를 작성해줘. 따뜻하고 전문적인 톤으로 3~5줄 정도로 써줘."
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "리포트 생성 중 오류 발생"

def generate_monthly_summary(api_key, student_info, avg_scores):
    model = get_model(api_key)
    if not model: return "총평 생성 실패"
    
    prompt = f"학생 {student_info['name']}의 한달 평균 성적({avg_scores})을 분석해서 4대영역별 성과와 앞으로의 학습 방향에 대해 3줄 정도의 총평을 써줘. 매번 다른 문구를 사용해서 정성스럽게 작성해줘."
    try:
        response = model.generate_content(prompt)
        return response.text
    except: return "성적이 향상되고 있으며 꾸준한 학습이 필요합니다."
