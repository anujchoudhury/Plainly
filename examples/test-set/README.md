# Plainly test set

Thirteen illustrative inputs for trying Plainly live: phone screenshots, letters as PDFs and as phone photos, and text to paste. They cover clear scams, real documents with something worth fighting, and the in-between cases where a good answer is "Careful" or "Not sure".

Every person, company, account number, phone number and link here is made up. The only real brands are ones scammers commonly impersonate (USPS, Microsoft), used the way real scam messages use them. Phone numbers use the 555-01xx range reserved for fiction, and `.example` addresses can't resolve.

## How to use them

- **Images** (`.png`, `.jpg`): tap **Upload a screenshot or PDF**. On a phone, AirDrop or save them to Photos first. The `-photo.jpg` letters look like a camera shot of paper, so they're the most realistic thing to show.
- **PDFs**: upload them directly. Plainly reads PDFs fine but only draws the red-flag boxes and the stamp on images, so for a demo use the photo version, or screenshot the PDF.
- **Text** (`.txt`): tap **Paste the text instead** and paste the whole file.

## What Plainly should say

| # | File | What it is | Expected verdict | What a good answer catches |
|---|---|---|---|---|
| 01 | `01-usps-redelivery-text.png` | USPS "package on hold" text from a +63 number | **Scam** | Foreign number, look-alike link (not usps.com), a tiny fee to get card details, the "reply Y" trick |
| 02 | `02-bank-fraud-alert-text.png` | Bank fraud alert from a short code: "Did you attempt $842.19?" | **Looks real** or **Careful** | No link, a short code, YES/NO reply only, and it says the bank never asks for a PIN. Should still say to call the number on the back of the card if unsure |
| 03 | `03-job-offer-whatsapp.png` | WhatsApp "remote job" paying $300–$900/day for rating products | **Scam** | Unsolicited, unrealistic pay, moves you to Telegram, asks for a "refundable deposit": the task scam pattern |
| 04 | `04-techguard-renewal-email.png` | "Your antivirus renewed for $399.99, call within 24 hours" | **Scam** | Gmail sender for a "billing dept", urgency, a phone number to call for a "refund": the refund scam |
| 05 | `05-lease-renewal-letter.pdf` / `-photo.jpg` | NYC landlord renewal with a 9.5% increase, sent Oct 5 for a Nov 30 lease end | **Looks real**, with a problem | NY Real Property Law § 226-c requires 90 days' notice for an increase of 5% or more when the lease ran two years. This letter gives 56, so the old rent continues until 90 days after the notice. The Oct 31 "sign or we'll show the apartment" deadline is pressure, not law |
| 06 | `06-anesthesia-bill.pdf` | $1,860 from an out-of-network anesthesiologist at an in-network surgery center | **Looks real**, likely not owed | The No Surprises Act protects you from balance bills by out-of-network anesthesiologists at in-network facilities. Should draft a dispute and suggest calling the insurer |
| 07 | `07-debt-collection-notice.pdf` | Debt collector's validation notice for a $612.40 medical bill | **Looks real** | Your right to dispute by Nov 10 and have collection paused. Should draft a dispute or validation request and suggest checking the original bill |
| 08 | `08-tax-levy-scam-letter.pdf` / `-photo.jpg` | "National Tax Resolution Bureau" final notice: pay $4,870 in 48 hours | **Scam** | Not a real agency, gift cards and Bitcoin ATM, arrest threats, "don't tell your bank". Should say to check irs.gov directly |
| 09 | `09-insurance-denial-eob.pdf` | Insurer denies a $1,950 MRI as "not medically necessary" | **Looks real** | "This is not a bill", the 180-day appeal window, prior authorization, and asking the doctor for a peer-to-peer review. Should draft the appeal |
| 10 | `10-grandparent-scam.txt` | "Grandma it's me, I'm in jail, need bail, don't tell Mom" | **Scam** | The grandparent scam: secrecy, urgency, cash courier or gift cards. Should say to call the grandchild or a parent on a known number |
| 11 | `11-wrong-number-text.txt` | "Hi Linda, still on for golf?" then "I do crypto investing, can we be friends?" | **Suspicious** | The wrong-number opener that leads to an investment scam. Nothing to click yet, so "Careful" is the right answer |
| 12 | `12-password-expiry-email.txt` | "Microsoft 365: your password expires today, keep it here" | **Scam** | The link domain isn't Microsoft's, there's a threat to delete mail, and "keep my password" is a credential grab |
| 13 | `13-pharmacy-ready-text.txt` | "Your prescription is ready for pickup" from a short code | **Looks real** | No link, no request, no money. Good for showing Plainly doesn't call everything a scam |

## A strong 3-minute demo order

1. **08 photo**: the tax letter. Big, scary and obviously fake once Plainly circles the gift-card line.
2. **06**: the anesthesia bill. Real, but you don't owe it. Show the dispute letter and the phone script.
3. **11**: the wrong-number text. "Careful", not "Scam", which shows the judgment.
4. **13**: the pharmacy text. "Looks real". It doesn't cry wolf.
