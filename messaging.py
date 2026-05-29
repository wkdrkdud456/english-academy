"""
문자/카카오 알림톡 발송 모듈 - 솔라피(Solapi) v4 API
앨리영어 학원 관리 시스템
"""
import requests
import json
import datetime
import hashlib
import hmac

# 솔라피 API 엔드포인트 (일부 통신사에서 DNS 차단 문제 해결을 위한 대체 도메인)
SOLAPI_ENDPOINTS = [
    "https://api.solapi.kr",
    "https://api.solapi.com",      # 대체 도메인 1
    "https://solapi.apigw.ntruss.com",  # 대체 도메인 2 (네이버 클라우드)
]

# DNS 확인을 위한 테스트 도메인
import socket

def _resolve_domain(domain):
    """도메인 resolv 가능한지 확인"""
    try:
        socket.gethostbyname(domain)
        return True
    except:
        return False

def _get_available_endpoint():
    """사용 가능한 솔라피 엔드포인트 찾기"""
    for ep in SOLAPI_ENDPOINTS:
        domain = ep.replace("https://", "").split("/")[0]
        if _resolve_domain(domain):
            return ep
    return SOLAPI_ENDPOINTS[0]  # 모두 실패시 기본값


def _make_signature(api_secret, date, salt):
    """솔라피 HMAC 서명 생성"""
    sig_input = date + salt
    return hmac.new(
        api_secret.encode(),
        sig_input.encode(),
        hashlib.sha256
    ).hexdigest()


def _build_headers(api_key, api_secret):
    """솔라피 API 인증 헤더 생성"""
    date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    salt = hashlib.sha256(date.encode()).hexdigest()[:8]
    signature = _make_signature(api_secret, date, salt)
    return {
        "Content-Type": "application/json",
        "Authorization": f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}"
    }


def check_solapi_balance(api_key, api_secret):
    """솔라피 잔액 조회"""
    if not api_key or api_key in ("", "YOUR_SOLAPI_KEY"):
        return None
    base = _get_available_endpoint()
    try:
        headers = _build_headers(api_key, api_secret)
        resp = requests.get(f"{base}/v1/balance", headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            return data
        return None
    except:
        return None


def send_message(api_key, api_secret, to_number, from_number, text, kakao_options=None):
    """
    솔라피 메시지 발송 (SMS/LMS/카카오알림톡 자동)
    
    - 90자 이하: SMS
    - 90자 초과: LMS
    - kakao_options 제공 시: 카카오 알림톡 (템플릿 필요)
    """
    if not api_key or api_key in ("", "YOUR_SOLAPI_KEY"):
        return {
            "success": False,
            "is_test": True,
            "message": (
                "⚠️ 솔라피 API 키가 설정되지 않았습니다.\n\n"
                "⚙️ 사이드바 → ⚙️ 설정 에서 API 키를 입력하거나\n"
                "아래 가이드를 참고해주세요.\n\n"
                "━━━━ 테스트 모드 ━━━━\n"
                f"📱 수신: {to_number}\n"
                f"📝 내용:\n{text}\n"
                "━━━━━━━━━━━━━━━━"
            )
        }
    
    try:
        headers = _build_headers(api_key, api_secret)
        
        # 메시지 타입 결정
        if kakao_options:
            msg_type = "ATA"  # 알림톡
        elif len(text) <= 90:
            msg_type = "SMS"
        else:
            msg_type = "LMS"
        
        payload = {
            "message": {
                "to": to_number,
                "from": from_number,
                "text": text,
                "type": msg_type
            }
        }
        
        # 카카오 알림톡 옵션 추가
        if kakao_options:
            payload["message"]["kakaoOptions"] = kakao_options
        
        base = _get_available_endpoint()
        resp = requests.post(
            f"{base}/messages/v4/send",
            headers=headers,
            json=payload,
            timeout=10
        )
        result = resp.json()
        
        if resp.status_code == 200:
            msg = "✅ 카카오 알림톡 발송 성공!" if kakao_options else "✅ 문자 발송 성공!"
            return {
                "success": True,
                "message": f"{msg} (메시지ID: {result.get('messageId', 'N/A')})",
                "data": result
            }
        else:
            err = result.get('message', '알 수 없는 오류')
            # 알림톡 실패 시 일반 문자로 폴백
            if kakao_options:
                return {
                    "success": False,
                    "message": f"❌ 알림톡 발송 실패: {err}\n→ 일반 문자로 대체 발송합니다.",
                    "fallback": send_message(api_key, api_secret, to_number, from_number, text)
                }
            return {
                "success": False,
                "message": f"❌ 발송 실패: {err}",
                "data": result
            }
    
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ 발송 중 오류: {str(e)}"
        }


def send_solapi_message(api_key, api_secret, to_number, from_number, text):
    """문자 발송 (하위 호환용)"""
    return send_message(api_key, api_secret, to_number, from_number, text)


def send_kakao_alimtalk(api_key, api_secret, to_number, from_number, text, template_code=None, pf_id=None):
    """
    카카오 알림톡 발송
    
    알림톡 발송 조건:
    1. 솔라피에서 카카오 비즈니스 채널 등록 (pfId 발급)
    2. 알림톡 템플릿 등록 (templateId 발급)
    
    템플릿 없으면 일반 LMS로 대체 발송됨
    """
    kakao_options = {}
    if pf_id:
        kakao_options["pfId"] = pf_id
    if template_code:
        kakao_options["templateId"] = template_code
    
    if not kakao_options:
        # 템플릿 정보 없으면 일반 문자 발송
        return send_message(api_key, api_secret, to_number, from_number, text)
    
    return send_message(api_key, api_secret, to_number, from_number, text, kakao_options)


# ============================================================
# 🆕 종합 알림톡 발송 함수 (템플릿 변수 지원)
# ============================================================
def send_comprehensive_alimtalk(api_key, api_secret, from_number, to_number, pf_id, template_id, variables):
    """
    솔라피 카카오 알림톡 발송 (템플릿 변수 포함)
    
    Parameters:
        api_key (str): 솔라피 API Key
        api_secret (str): 솔라피 API Secret
        from_number (str): 발신번호
        to_number (str): 수신번호 (학부모)
        pf_id (str): 카카오 채널 ID (예: "@앨리영어")
        template_id (str): 승인된 알림톡 템플릿 ID
        variables (dict): 템플릿 변수 (예: {"#{학생이름}": "김앨리", ...})
    
    Returns:
        dict: 발송 결과
    """
    kakao_options = {
        "pfId": pf_id,
        "templateId": template_id,
        "variables": variables
    }
    
    # 폴백 문자 메시지 (알림톡 실패 시)
    fallback_text = f"[앨리영어] {variables.get('#{학생이름}', '학생')}님의 알림이 있습니다. 자세한 내용은 앱을 확인해주세요."
    
    return send_message(api_key, api_secret, to_number, from_number, fallback_text, kakao_options)


# ============================================================
# 🆕 사용 예시 (app.py 등에서 호출)
# ============================================================
"""
# app.py에서 이렇게 사용:

from messaging import send_comprehensive_alimtalk

# 알림톡 발송
result = send_comprehensive_alimtalk(
    api_key=st.session_state.solapi_key_input,
    api_secret=st.session_state.solapi_secret_input,
    from_number=st.session_state.solapi_from_input,
    to_number=student_info['parent_phone'],
    pf_id="@앨리영어",
    template_id="YOUR_APPROVED_TEMPLATE_ID",
    variables={
        "#{학생이름}": "김앨리",
        "#{출석날짜}": "5월 29일",
        "#{출석상태}": "✅ 출석",
        "#{잔여횟수}": "7",
        "#{시험주차}": "3주차 테스트",
        "#{정답률}": "18/25 (72%)",
        "#{취약영역}": "⚠️ 문법 영역",
        "#{리포트월}": "5월",
        "#{듣기점수}": "85",
        "#{어휘점수}": "78",
        "#{문법점수}": "65",
        "#{독해점수}": "80",
        "#{AI총평}": "이번 달 듣기 영역에서...",
    }
)
"""