"""Pre-recorded results for the three built-in samples. Used when no
GEMINI_API_KEY is set (or FORCE_DEMO=1), so the demo never depends on wifi."""
import json
from pathlib import Path

_BOXES = json.loads((Path(__file__).parent / "demo_boxes.json").read_text(encoding="utf-8"))

FTC_TOLL = "https://www.consumer.ftc.gov/consumer-alerts/2025/01/got-text-about-unpaid-tolls-its-probably-scam"
EZPASS = "https://www.e-zpassny.com/"
REPORTFRAUD = "https://reportfraud.ftc.gov/"
CMS_NSA = "https://www.cms.gov/nosurprises"
CONED = "https://www.coned.com/"
FTC_PHISH = "https://consumer.ftc.gov/articles/how-recognize-and-avoid-phishing-scams"

DEMO = {
    "toll": {
        "extract": {
            "doc_type": "text_message", "category": "toll",
            "claimed_sender": "E-ZPass New York", "sender_details": "+1 (639) 412-0587",
            "organization": "E-ZPass New York",
            "summary": "A text claiming you owe $6.99 in unpaid tolls, with a payment link.",
            "asks": "Pay $6.99 through a link before 10/13.",
            "urls": ["https://ezpassny-tolls.top/pay"], "phones": ["+1 (639) 412-0587"],
            "amounts": [{"label": "Unpaid toll", "value": "$6.99"}, {"label": "Threatened late fee", "value": "$50.00"}],
            "dates": [{"label": "Pay by", "date": "2026-10-13", "raw": "10/13"}],
            "location_hint": "New York", "regions": _BOXES["toll"],
            "verify_queries": [
                {"purpose": "official", "query": "E-ZPass New York official website pay toll"},
                {"purpose": "scam_check", "query": "ezpassny-tolls.top unpaid toll text scam"},
                {"purpose": "rules", "query": "FTC unpaid toll text scam warning"},
            ],
        },
        "sources": [
            {"title": "Got a text about unpaid tolls? It's probably a scam", "url": FTC_TOLL, "snippet": "FTC consumer alert on texts demanding payment for unpaid tolls.", "purpose": "scam_check"},
            {"title": "E-ZPass New York — official site", "url": EZPASS, "snippet": "The official E-ZPass New York customer service center.", "purpose": "official"},
            {"title": "ReportFraud.ftc.gov", "url": REPORTFRAUD, "snippet": "Report scams and fraud to the Federal Trade Commission.", "purpose": "rules"},
        ],
        "result": {
            "verdict": "scam", "confidence": 96,
            "headline": "This toll text is a scam.",
            "plain_english": "This text pretends to be from E-ZPass New York, but its link goes to ezpassny-tolls.top, not the real E-ZPass site. Real toll agencies don't text from personal phone numbers or threaten your license over $6.99. The FTC has warned about this exact scheme.",
            "what_they_want": "They want you to open a fake payment page and type in your card details.",
            "amount_due": "", "deadline": "", "deadline_label": "",
            "red_flags": [
                {"region_id": "r4", "title": "Look-alike link", "why": "The real site is e-zpassny.com. This one just borrows the name."},
                {"region_id": "r1", "title": "Random personal number", "why": "Toll agencies don't text from ordinary 10-digit numbers."},
                {"region_id": "r3", "title": "Threats over a tiny amount", "why": "A $50 fee and license suspension over $6.99 is meant to rush you."},
                {"region_id": "r5", "title": "The 'reply Y' trick", "why": "Replying turns the blocked link back on and tells them your number works."},
            ],
            "good_signs": [],
            "steps": [
                {"title": "Don't tap the link or reply", "detail": "Not even STOP. Any reply confirms your number is active."},
                {"title": "Check your real balance yourself", "detail": "Open the E-ZPass app or type e-zpassny.com into your browser. If you owe nothing there, you owe nothing."},
                {"title": "Report it, then delete it", "detail": "Forward the text to 7726 (SPAM), report it at ReportFraud.ftc.gov, then tap Report Junk."},
                {"title": "Already paid? Call your bank now", "detail": "Ask them to block the card and dispute the charge."},
            ],
            "rights": [
                {"title": "The FTC has flagged this scheme", "detail": "Its alert describes unpaid-toll texts with payment links as a common scam.", "source_url": FTC_TOLL},
            ],
            "message": {
                "kind": "report", "to": "ReportFraud.ftc.gov",
                "subject": "Toll text scam impersonating E-ZPass New York",
                "body": "On October 11, 2026 I received a text from +1 (639) 412-0587 claiming to be E-ZPass New York. It said I owed $6.99 in unpaid tolls and threatened a $50.00 late fee and suspension of my driving privileges unless I paid at https://ezpassny-tolls.top/pay. I did not click the link or pay. I'm reporting it as a phishing scam.\n\n[Your name]",
            },
            "sources_used": [FTC_TOLL, EZPASS, REPORTFRAUD],
            "calendar_title": "",
            "call_script": {
                "who": "E-ZPass New York, using the number on e-zpassny.com (never the one in the text)", "number": "", "when": "",
                "have_ready": ["Your license plate", "Your E-ZPass account number, if you have one"],
                "lines": [
                    "Hi, I got a text saying I owe $6.99 in unpaid tolls with a link to ezpassny-tolls.top.",
                    "Can you check whether my account has any unpaid tolls?",
                    "I didn't click the link. Is there anything else I should do?",
                ],
                "if_they_say_no": "If they confirm you owe nothing, delete the text and report it to 7726.",
            },
        },
    },
    "bill": {
        "extract": {
            "doc_type": "bill", "category": "medical_bill",
            "claimed_sender": "Riverside Mercy Medical Center", "sender_details": "450 Riverside Blvd, Brooklyn, NY 11201",
            "organization": "Riverside Mercy Medical Center",
            "summary": "A hospital statement for an August 14 emergency visit with a $3,097.50 balance.",
            "asks": "Pay $3,097.50 by October 30, 2026.",
            "urls": ["riversidemercy.org/pay"], "phones": ["(718) 555-0142"],
            "amounts": [{"label": "Amount due", "value": "$3,097.50"}, {"label": "Out-of-network ER doctor", "value": "$2,847.50"}, {"label": "ER visit cost-sharing", "value": "$250.00"}],
            "dates": [{"label": "Due by", "date": "2026-10-30", "raw": "October 30, 2026"}, {"label": "Date of service", "date": "2026-08-14", "raw": "08/14/26"}],
            "location_hint": "Brooklyn, NY", "regions": _BOXES["bill"],
            "verify_queries": [
                {"purpose": "rules", "query": "No Surprises Act out-of-network emergency physician bill"},
                {"purpose": "official", "query": "Riverside Mercy Medical Center billing"},
                {"purpose": "rules", "query": "New York surprise medical bill dispute"},
            ],
        },
        "sources": [
            {"title": "No Surprises Act — CMS", "url": CMS_NSA, "snippet": "Your rights and protections against surprise medical bills.", "purpose": "rules"},
        ],
        "result": {
            "verdict": "legit", "confidence": 84,
            "headline": "Real bill, but you likely don't owe all of it.",
            "plain_english": "This looks like a genuine statement for your August 14 ER visit. The $250.00 for the visit itself is normal cost-sharing. The $2,847.50 is from an out-of-network ER doctor your insurance didn't pay, and the No Surprises Act says emergency care can only cost you what you'd pay in-network.",
            "what_they_want": "Pay $3,097.50 by October 30, 2026.",
            "amount_due": "$3,097.50", "deadline": "2026-10-30", "deadline_label": "Payment due",
            "red_flags": [
                {"region_id": "r3", "title": "Out-of-network ER doctor billed in full", "why": "Emergency care is protected from surprise out-of-network bills."},
                {"region_id": "r4", "title": "Collections warning", "why": "Ask them to pause collections while the bill is reviewed."},
            ],
            "good_signs": [
                {"title": "Matches a real visit", "why": "Dates, account number and insurer details are consistent."},
                {"title": "Official payment options", "why": "It points to the hospital's own site and phone line, not a random link."},
            ],
            "steps": [
                {"title": "Hold off on the $2,847.50", "detail": "Paying it first can make it harder to get money back. The $250.00 ER charge looks normal."},
                {"title": "Call Bluebridge Health", "detail": "Ask them to reprocess the Coastline ER Physicians claim as emergency care under the No Surprises Act, at in-network rates."},
                {"title": "Send the hospital the letter below", "detail": "It asks for an itemized bill and a hold on collections while the bill is reviewed."},
                {"title": "Escalate if they won't fix it", "detail": "Call the No Surprises Help Desk at 1-800-985-3059 or file a complaint at cms.gov/nosurprises."},
            ],
            "rights": [
                {"title": "Emergency care is protected", "detail": "Out-of-network providers at an emergency visit can only bill your in-network cost-sharing.", "source_url": CMS_NSA},
            ],
            "message": {
                "kind": "reply", "to": "Riverside Mercy Patient Financial Services",
                "subject": "Dispute of balance on account RM-2048-7731",
                "body": "Hello,\n\nI'm writing about account RM-2048-7731 for emergency care on August 14, 2026. The statement dated October 1, 2026 bills me $2,847.50 for emergency physician services from Coastline ER Physicians as out-of-network.\n\nUnder the federal No Surprises Act, out-of-network providers for emergency services may only bill me my in-network cost-sharing amount. Please:\n\n1. Send me an itemized bill for this visit.\n2. Correct the physician charge to my in-network cost-sharing after Bluebridge Health reprocesses the claim.\n3. Place my account on hold and do not refer it to collections while this is reviewed.\n\nI will pay the $250.00 balance for the emergency department visit separately.\n\nThank you,\n[Your name]\n[Phone number]",
            },
            "sources_used": [CMS_NSA],
            "calendar_title": "Riverside Mercy bill due ($3,097.50)",
            "call_script": {
                "who": "Riverside Mercy Patient Financial Services", "number": "(718) 555-0142", "when": "Monday to Friday, 8am to 6pm",
                "have_ready": ["Account RM-2048-7731", "Date of visit: August 14, 2026", "Your Bluebridge Health member ID"],
                "lines": [
                    "Hi, I'm calling about account RM-2048-7731 for an emergency room visit on August 14.",
                    "My statement shows $2,847.50 from Coastline ER Physicians billed as out-of-network.",
                    "This was emergency care, so under the No Surprises Act I should only owe my in-network cost-sharing.",
                    "Can you send me an itemized bill and resubmit that charge to Bluebridge Health as emergency care?",
                    "Please put my account on hold so it doesn't go to collections while this is reviewed.",
                    "Can I get your name and a reference number for this call?",
                ],
                "if_they_say_no": "Ask for a supervisor, then call the No Surprises Help Desk at 1-800-985-3059.",
            },
        },
    },
    "coned": {
        "extract": {
            "doc_type": "text_message", "category": "utility",
            "claimed_sender": "Con Edison", "sender_details": "26633 (short code)",
            "organization": "Con Edison",
            "summary": "A billing reminder: $84.21 due November 2.",
            "asks": "Pay $84.21 by 11/02 in the app or at coned.com.",
            "urls": ["coned.com"], "phones": [],
            "amounts": [{"label": "Bill amount", "value": "$84.21"}],
            "dates": [{"label": "Due", "date": "2026-11-02", "raw": "11/02"}],
            "location_hint": "New York", "regions": _BOXES["coned"],
            "verify_queries": [
                {"purpose": "official", "query": "Con Edison official website pay bill"},
                {"purpose": "scam_check", "query": "Con Edison text message scam"},
            ],
        },
        "sources": [
            {"title": "Con Edison — official site", "url": CONED, "snippet": "Pay your bill, manage your account.", "purpose": "official"},
            {"title": "How to recognize and avoid phishing scams — FTC", "url": FTC_PHISH, "snippet": "Signs of phishing texts and emails.", "purpose": "scam_check"},
        ],
        "result": {
            "verdict": "legit", "confidence": 78,
            "headline": "This looks like a real Con Edison bill alert.",
            "plain_english": "It reads like a normal billing reminder: an amount, a due date, and no link to tap. It sends you to the Con Edison app or coned.com instead, and it doesn't ask for personal information or threaten you.",
            "what_they_want": "Pay $84.21 by November 2.",
            "amount_due": "$84.21", "deadline": "2026-11-02", "deadline_label": "Bill due",
            "red_flags": [],
            "good_signs": [
                {"title": "No link to tap", "why": "Scam texts almost always include a payment link."},
                {"title": "Points to the official site", "why": "coned.com is Con Edison's real website."},
                {"title": "No pressure", "why": "No threats, shutoff warnings or requests for personal details."},
            ],
            "steps": [
                {"title": "Confirm it in the app", "detail": "Open the Con Edison app or type coned.com yourself and check the $84.21 matches."},
                {"title": "Pay through the official app or site", "detail": "Never through a link someone texts you, even when the text looks real."},
                {"title": "Set a reminder", "detail": "Add the November 2 due date to your calendar."},
            ],
            "rights": [],
            "message": {"kind": "none", "to": "", "subject": "", "body": ""},
            "sources_used": [CONED, FTC_PHISH],
            "calendar_title": "Con Edison bill due ($84.21)",
            "call_script": None,
        },
    },
}
