# Real-world examples for the demo

Real scam messages and real (confusing but legitimate) documents published on the web, for showing Plainly on things it has never seen. Open a link on your phone, screenshot or save the image, and upload it in Plainly. For a PDF, upload it directly or screenshot the first page.

These are linked, not copied into the repo: most belong to the sites that published them.

## Scams

| What | Why it's a good demo | Link |
|---|---|---|
| **Fake E-ZPass "unpaid toll" text** that hit NYC drivers when congestion pricing launched (amNY, Feb 2025) | Local to NYC. Everyone in the room has had one. Plainly should call it a scam and point to the real E-ZPass site. | [Image](https://www.amny.com/wp-content/uploads/2025/02/ez-pass-fake.jpg?w=700), [article](https://www.amny.com/nyc-transit/congestion-pricing-scam-bogus-texts-unpaid-tolls) |
| **USPS "package can't be delivered" text** from a +44 number (Brown University IT phishing alert) | A classic smishing text: a foreign number, a fake delivery problem and a link. | [Image](https://it.brown.edu/sites/default/files/pbowl_USPSscam_20231031.jpg), [alert](https://it.brown.edu/phish-bowl-alerts/usps-delivery-scam-text-messages) |
| **Fake Geek Squad renewal invoice** email (Intego) | Shows Plainly on email, not just texts. Fake "you were charged" invoices push you to call a phone number. | [Image](https://www.intego.com/mac-security-blog/wp-content/uploads/2023/06/fake-Geek-Squad-invoice-20230525.jpg), [article](https://www.intego.com/mac-security-blog/fake-invoice-scams-norton-mcafee-paypal-and-more/) |
| **Fake Norton LifeLock invoice** sent through a real invoicing service (Intego) | The tricky kind: it comes through a legitimate service, so the sender looks real. | [Image](https://www.intego.com/mac-security-blog/wp-content/uploads/2023/06/fake-Norton-LifeLock-invoice-20230525.jpg) |
| **Fake PayPal invoice for $499.99 in Bitcoin** (Intego, via MakeUseOf) | It looks like real PayPal, because it is sent through PayPal itself. Plainly should catch the "call this number to dispute" trap. | [Image](https://www.intego.com/mac-security-blog/wp-content/uploads/2023/06/fake-PayPal-Bitcoin-invoice-via-MakeUseOf.jpg) |

## Real documents that are confusing

| What | Why it's a good demo | Link |
|---|---|---|
| **IRS CP14 "balance due" notice**, a real notice with personal details redacted (TaxAudit) | The IRS letter people panic about. Plainly should say it looks real, explain the amount and deadline, and suggest a payment plan or dispute. | [Page 1](https://intuit.taxaudit.com/getattachment/b95e5bd7-4ee4-458e-8c32-a43b435a03ea/CP14-1.png), [sample page](https://intuit.taxaudit.com/audit-defense/resources/sample-audit-notices/irs-notices/irs-audit-letter-cp14-sample-1) |
| **Medicare Summary Notice, Part B** (official sample from HHS/CMS) | A real government document that confuses older adults. Good for the "built for parents" story. | [PDF](https://www.hhs.gov/guidance/sites/default/files/hhs-guidance-documents/CMS/Sample-Part-B-Medicare-Summary-Notice.pdf) |
| **Explanation of Benefits** sample (Children's Healthcare of Atlanta) | "This is not a bill" documents confuse everyone. Plainly should explain what you actually owe. | [PDF](https://www.choa.org/-/media/Files/Childrens/patients/sample-eob.pdf) |

## Built-in samples

The app also ships three made-up samples (toll text, hospital bill, Con Edison text) in `static/samples/`. They replay saved answers without any API keys or Wi-Fi, so they're the safety net if the venue network fails.
