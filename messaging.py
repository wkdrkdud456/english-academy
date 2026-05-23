"""
문자/카카오 알림톡 발송 모듈 - 솔라피(Solapi) API 연동
앨리영어 학원 관리 시스템
"""
import requests
import json

def send_solapi_message(api_key, api_secret, to_number, from_number, text):
    """
    솔라피 API를 통해 문자 메시지 발송
    
    실제 운영 시 아래 정보 필요:
    - api_key: 솔라피 API Key
    - api_secret: 솔라피 API Secret
    - from_number: 발신 번호 (사전 등록 필요)
    
    파라미터:
        api_key (str): 솔라피 API Key
        api_secret (str): 솔라피 API Secret  
        to_number (str): 수신자 전화번호
        from_number (str): 발신자 전화번호
        text (str): 메시지 내용
    
    Returns:
        dict: 발송 결과 {"success": True/False, "message": "..."}
    """
    # API 키가 설정되지 않은 경우 테스트 모드
    if not api_key or api_key == "" or api_key == "YOUR_SOLAPI_KEY":
        return {
            "success": False,
            "message": "⚠️ 솔라피 API 키가 설정되지 않았습니다. .env 파일이나 사이드바에서 API 키를 설정해주세요.\n[테스트 모드] 발송될 메시지:\n─────────────────────\n" + text + "\n─────────────────────"
        }
    
    try:
        url = "https://api.solapi.kr/messages/v4/send"
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "message": {
                "to": to_number,
                "from": from_number,
                "text": text,
                "type": "SMS" if len(text) <= 90 else "LMS"
            }
        }
        
        # HMAC 인증 헤더 생성
        import datetime
        import hashlib
        import hmac
        
        date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        salt = str(hashlib.sha256(date.encode()).hexdigest())[:8]
        signature_data = date + salt
        signature = hmac.new(
            api_secret.encode(),
            signature_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        headers["Authorization"] = f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}"
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        result = response.json()
        
        if response.status_code == 200:
            return {
                "success": True,
                "message": f"✅ 메시지가 성공적으로 발송되었습니다! (메시지ID: {result.get('messageId', 'N/A')})"
            }
        else:
            return {
                "success": False,
                "message": f"❌ 발송 실패: {result.get('message', '알 수 없는 오류')}"
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ 발송 중 오류 발생: {str(e)}"
        }


def send_kakao_alimtalk(api_key, api_secret, to_number, from_number, text, template_code=None):
    """
    카카오 알림톡 발송 (솔라피 SDK 활용)
    
    알림톡 발송을 위해선 사전에 솔라피에서 템플릿 등록이 필요합니다.
    템플릿 미등록 시 일반 LMS로 대체 발송됩니다.
    """
    # 템플릿이 없으면 일반 문자로 대체
    if not template_code:
        return send_solapi_message(api_key, api_secret, to_number, from_number, text)
    
    try:
        url = "https://api.solapi.kr/messages/v4/send"
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "message": {
                "to": to_number,
                "from": from_number,
                "text": text,
                "type": "ATA",
                "kakaoOptions": {
                    "pfId": from_number,
                    "templateId": template_code
                }
            }
        }
        
        import datetime
        import hashlib
        import hmac
        
        date = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        salt = str(hashlib.sha256(date.encode()).hexdigest())[:8]
        signature_data = date + salt
        signature = hmac.new(
            api_secret.encode(),
            signature_data.encode(),
            hashlib.sha256
        ).hexdigest()
        
        headers["Authorization"] = f"HMAC-SHA256 apiKey={api_key}, date={date}, salt={salt}, signature={signature}"
        
        response = requests.post(url, headers=headers, json=payload, timeout=10)
        result = response.json()
        
        if response.status_code == 200:
            return {
                "success": True,
                "message": f"✅ 카카오 알림톡이 성공적으로 발송되었습니다!"
            }
        else:
            return {
                "success": False,
                "message": f"❌ 알림톡 발송 실패: {result.get('message', '알 수 없는 오류')}. 일반 문자로 대체 발송합니다.",
                "fallback": send_solapi_message(api_key, api_secret, to_number, from_number, text)
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ 알림톡 발송 중 오류: {str(e)}. 일반 문자로 대체 발송합니다.",
            "fallback": send_solapi_message(api_key, api_secret, to_number, from_number, text)
        }