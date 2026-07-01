"""Standalone legal pages (Terms of Service & Privacy Policy) for external linking."""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

api = APIRouter()

LEGAL_BASE_STYLE = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*,*::before,*::after{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Inter',-apple-system,BlinkMacSystemFont,sans-serif;background:#0A0A0A;color:#E5E5E5;line-height:1.7;padding:2rem 1rem;min-height:100vh}
.container{max-width:720px;margin:0 auto}
h1{font-size:1.75rem;color:#F97316;margin-bottom:0.5rem;font-weight:700}
.last-updated{color:#888;font-size:0.85rem;margin-bottom:2rem;border-bottom:1px solid #333;padding-bottom:1rem}
h2{font-size:1.05rem;color:#FDBA74;margin-top:2rem;margin-bottom:0.75rem;font-weight:600}
h3{font-size:0.95rem;color:#D97706;margin-top:1.25rem;margin-bottom:0.5rem;font-weight:600}
p,li{font-size:0.9rem;color:#CCC;margin-bottom:0.4rem}
p{margin-bottom:1rem}
ul{margin-bottom:1rem;padding-left:1.5rem}
ul ul{padding-left:1.5rem;margin-bottom:0.5rem}
strong{color:#E5E5E5}
a{color:#F97316;text-decoration:none}
a:hover{text-decoration:underline}
.back-link{display:inline-block;margin-bottom:1.5rem;color:#F97316;font-size:0.85rem;font-weight:500}
.back-link:hover{text-decoration:underline}
.header-logo{font-size:1.5rem;font-weight:700;color:#F97316;margin-bottom:0.25rem;letter-spacing:0.05em}
.notice{background:#1a1a1a;border-left:3px solid #F97316;padding:1rem;margin:1.5rem 0;border-radius:0 8px 8px 0}
.notice p{font-size:0.85rem;margin:0;color:#AAA}
</style>
"""

TERMS_HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Day Shift — Terms of Service</title>
{LEGAL_BASE_STYLE}
</head><body><div class="container">
<div class="header-logo">DAY SHIFT</div>
<a href="/" class="back-link">← Back to Day Shift</a>
<h1>Terms of Service</h1>
<p class="last-updated">Last updated: June 2026</p>

<div class="notice"><p>IMPORTANT: PLEASE READ THESE TERMS OF SERVICE CAREFULLY BEFORE USING THE DAY SHIFT PLATFORM. BY CREATING AN ACCOUNT OR USING THE SERVICE, YOU AGREE TO BE BOUND BY THESE TERMS. THESE TERMS CONTAIN A MANDATORY ARBITRATION PROVISION AND CLASS ACTION WAIVER — SEE SECTION 14.</p></div>

<h2>1. ACCEPTANCE OF TERMS</h2>
<p>BY ACCESSING OR USING THE DAY SHIFT MOBILE APPLICATION ("THE SERVICE"), YOU ("USER," "YOU," OR "YOUR") AGREE TO BE BOUND BY THESE TERMS OF SERVICE ("TERMS"), THE PRIVACY POLICY, AND ANY OTHER POLICIES INCORPORATED BY REFERENCE, WHETHER OR NOT YOU HAVE REGISTERED FOR AN ACCOUNT. IF YOU ARE ENTERING INTO THESE TERMS ON BEHALF OF A COMPANY OR OTHER LEGAL ENTITY ("ENTITY"), YOU REPRESENT THAT YOU HAVE THE AUTHORITY TO BIND SUCH ENTITY TO THESE TERMS, AND "YOU" SHALL REFER TO BOTH YOU AND SUCH ENTITY.</p>

<h2>2. ELIGIBILITY AND AGE REQUIREMENTS</h2>
<p>THE SERVICE IS INTENDED SOLELY FOR INDIVIDUALS WHO ARE EIGHTEEN (18) YEARS OF AGE OR OLDER. BY USING THE SERVICE, YOU REPRESENT AND WARRANT THAT: (A) YOU ARE AT LEAST 18 YEARS OF AGE; (B) YOU POSSESS THE LEGAL RIGHT AND CAPACITY TO ENTER INTO A BINDING AGREEMENT; (C) YOU ARE NOT PROHIBITED FROM USING THE SERVICE UNDER THE LAWS OF THE UNITED STATES OR ANY OTHER APPLICABLE JURISDICTION; AND (D) YOU ARE NOT A REGISTERED SEX OFFENDER. DAY SHIFT DOES NOT KNOWINGLY COLLECT PERSONAL INFORMATION FROM INDIVIDUALS UNDER THE AGE OF 18.</p>

<h2>3. DESCRIPTION OF SERVICE</h2>
<p>Day Shift is a technology platform that facilitates connections between culinary industry workers ("Crew") and food service establishments ("Kitchens") for the purpose of identifying shift-based employment opportunities. DAY SHIFT ACTS SOLELY AS A TECHNOLOGY INTERMEDIARY AND MATCHING PLATFORM. DAY SHIFT IS NOT AN EMPLOYMENT AGENCY, RECRUITING FIRM, STAFFING SERVICE, JOINT EMPLOYER, OR EMPLOYER OF ANY KIND. DAY SHIFT DOES NOT: (A) EMPLOY, HIRE, OR CONTRACT WITH CREW MEMBERS; (B) GUARANTEE THE AVAILABILITY, QUALITY, SAFETY, OR OUTCOME OF ANY SHIFT OR EMPLOYMENT OPPORTUNITY; (C) VERIFY THE QUALIFICATIONS, CREDENTIALS, CERTIFICATIONS, BACKGROUND, CRIMINAL HISTORY, OR IDENTITY OF ANY USER; (D) SET, COLLECT, OR GUARANTEE WAGES, COMPENSATION, OR BENEFITS; (E) SUPERVISE, MANAGE, DIRECT, OR CONTROL ANY WORK RELATIONSHIP, WORKPLACE, OR WORKING CONDITIONS; OR (F) PROVIDE WORKERS' COMPENSATION, UNEMPLOYMENT INSURANCE, OR ANY OTHER EMPLOYMENT-RELATED BENEFITS.</p>

<h2>4. USER ACCOUNTS AND REGISTRATION</h2>
<p>To access certain features, you must create an account. You agree to: (A) provide accurate, current, and complete information during registration and promptly update it; (B) maintain the security of your account credentials and not share them; (C) notify Day Shift immediately of any unauthorized use; (D) not create multiple accounts without permission; (E) not transfer or sell your account; and (F) not impersonate any person or entity. You are solely responsible for all activity under your account. Day Shift may suspend or terminate accounts at any time, for any reason, without prior notice or liability, including for inactivity exceeding twelve (12) months.</p>

<h2>5. USER CONTENT AND LICENSE GRANT</h2>
<p>You retain all ownership rights in and to any content you submit, post, or display on the Service ("User Content"), including videos, images, text, and profile information. By posting User Content, you grant to Day Shift a worldwide, non-exclusive, royalty-free, fully paid, sublicensable, and transferable license to use, reproduce, modify, publish, distribute, perform, and display such User Content in connection with operating, providing, improving, and promoting the Service. You represent that you own or have all necessary rights to submit the User Content and that it does not infringe any third party's intellectual property rights, privacy rights, or publicity rights.</p>

<h2>6. PROHIBITED CONDUCT</h2>
<p>You agree not to:</p>
<ul>
<li>Use the Service for any unlawful purpose or in violation of any applicable laws</li>
<li>Post, upload, or transmit any content that is unlawful, harmful, threatening, abusive, harassing, defamatory, obscene, sexually explicit, pornographic, hateful, or otherwise objectionable</li>
<li>Engage in hate speech, discrimination, or harassment based on race, color, religion, sex, sexual orientation, gender identity, national origin, age, disability, or any other protected characteristic</li>
<li>Stalk, threaten, or harass any other user</li>
<li>Impersonate any person or entity, or misrepresent your identity, qualifications, or affiliations</li>
<li>Distribute spam, unsolicited communications, pyramid schemes, or unauthorized advertisements</li>
<li>Collect or harvest personal information about other users without consent</li>
<li>Interfere with, disrupt, or attempt to gain unauthorized access to the Service or servers</li>
<li>Reverse engineer, decompile, or disassemble the Service</li>
<li>Use automated systems, bots, or scrapers to access the Service</li>
<li>Upload or transmit viruses, worms, or malicious code</li>
<li>Use the Service to arrange or solicit sexual encounters, escort services, or adult entertainment</li>
<li>Post false, misleading, or deceptive content about your qualifications or identity</li>
<li>Bypass any measures Day Shift uses to prevent or restrict access</li>
</ul>

<h2>7. PAYMENTS, BOOSTS, AND ADVERTISING SUBSCRIPTIONS</h2>
<h3>Boosts</h3>
<p>Day Shift offers paid post-visibility features ("Boosts"). Boost purchases are processed through PayPal. All Boost purchases are final and non-refundable, except as required by applicable law. Boosts are one-time purchases that expire after the specified duration and do not auto-renew.</p>
<h3>Advertising Subscriptions</h3>
<p>Advertisers may purchase recurring subscription plans. Subscriptions auto-renew at the end of each billing period unless canceled. You may cancel at any time through the app settings or by contacting <a href="mailto:contact@dayshiftnow.me">contact@dayshiftnow.me</a>. Upon cancellation, your subscription remains active through the end of the current billing period; no partial refunds will be issued for the unused portion. Day Shift reserves the right to change pricing with thirty (30) days' notice.</p>
<h3>Promotional Offers</h3>
<p>Promotional codes, free trials, and discounted plans are subject to specific terms stated at the time of offer, may be limited, and may be revoked or modified. Free trials convert to paid subscriptions at trial end unless canceled.</p>

<h2>8. INTELLECTUAL PROPERTY</h2>
<p>The Service and its contents (including software, text, images, video, design, and the Day Shift name and logo) are owned by Day Shift and protected by United States and international intellectual property laws. These Terms do not grant you any right to use Day Shift's trade names, trademarks, logos, or other brand features. All feedback you provide regarding the Service is the exclusive property of Day Shift.</p>

<h2>9. DMCA / COPYRIGHT INFRINGEMENT</h2>
<p>Day Shift respects intellectual property rights. In accordance with the Digital Millennium Copyright Act ("DMCA"), Day Shift will respond expeditiously to claims of copyright infringement. To report alleged infringement, send a DMCA Notice to our Designated Copyright Agent at <a href="mailto:copyright@dayshiftnow.me">copyright@dayshiftnow.me</a> (subject: "DMCA Copyright Notice") containing: (A) your physical or electronic signature; (B) identification of the copyrighted work; (C) identification and location of the infringing material; (D) your contact information; (E) a good-faith statement that the use is unauthorized; and (F) a statement under penalty of perjury that your notice is accurate and you are authorized to act. Day Shift's policy is to terminate repeat infringers' accounts in appropriate circumstances.</p>

<h2>10. USER SAFETY AND BACKGROUND CHECKS</h2>
<p>DAY SHIFT DOES NOT CONDUCT BACKGROUND CHECKS, CRIMINAL SCREENINGS, SEX OFFENDER REGISTRY CHECKS, DRUG TESTS, OR ANY FORM OF VETTING ON ANY USER. DAY SHIFT DOES NOT VERIFY THE IDENTITY, QUALIFICATIONS, CERTIFICATIONS, OR STATEMENTS OF ANY USER. DAY SHIFT DOES NOT INSPECT OR CERTIFY ANY WORKPLACE OR KITCHEN FACILITY. YOU ARE SOLELY RESPONSIBLE FOR YOUR OWN SAFETY AND FOR VERIFYING THE IDENTITY AND SUITABILITY OF ANY USER YOU INTERACT WITH. Day Shift recommends that users take all reasonable precautions, including meeting in public places and informing others of your whereabouts.</p>

<h2>11. ASSUMPTION OF RISK</h2>
<p>YOU ASSUME ALL RISKS, KNOWN AND UNKNOWN, ASSOCIATED WITH YOUR USE OF THE SERVICE AND INTERACTIONS WITH OTHER USERS, INCLUDING RISKS OF PHYSICAL HARM, DEATH, PROPERTY DAMAGE, FINANCIAL LOSS, THEFT, FRAUD, AND ANY OTHER HARM. Day Shift is not responsible for any injury, loss, or damage arising from your use of the Service or interactions with other users.</p>

<h2>12. DISCLAIMER OF WARRANTIES</h2>
<p>THE SERVICE IS PROVIDED "AS IS" AND "AS AVAILABLE" WITHOUT WARRANTIES OF ANY KIND. DAY SHIFT DISCLAIMS ALL WARRANTIES, EXPRESS OR IMPLIED, INCLUDING MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND NON-INFRINGEMENT. Day Shift does not warrant that the Service will be uninterrupted, error-free, secure, or meet your requirements.</p>

<h2>13. LIMITATION OF LIABILITY</h2>
<p>TO THE MAXIMUM EXTENT PERMITTED BY LAW, DAY SHIFT SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, PUNITIVE, OR EXEMPLARY DAMAGES, INCLUDING LOSS OF PROFITS, DATA, OR GOODWILL, ARISING FROM YOUR USE OF THE SERVICE. DAY SHIFT'S AGGREGATE LIABILITY SHALL NOT EXCEED THE GREATER OF: (A) AMOUNTS PAID BY YOU IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM; OR (B) ONE HUNDRED DOLLARS ($100.00). Some jurisdictions do not allow certain limitations, so the above may not apply to you.</p>

<h2>14. DISPUTE RESOLUTION — MANDATORY ARBITRATION AND CLASS ACTION WAIVER</h2>
<p><strong>PLEASE READ THIS SECTION CAREFULLY. IT AFFECTS YOUR LEGAL RIGHTS, INCLUDING YOUR RIGHT TO FILE A LAWSUIT IN COURT.</strong></p>
<p><strong>Informal Resolution:</strong> Before filing any claim, you agree to contact Day Shift at <a href="mailto:legal@dayshiftnow.me">legal@dayshiftnow.me</a> and attempt to resolve the dispute informally for at least sixty (60) days.</p>
<p><strong>Mandatory Arbitration:</strong> Any dispute arising out of these Terms or the Service shall be resolved exclusively by final and binding arbitration administered by the American Arbitration Association ("AAA") under its Consumer Arbitration Rules. The arbitration shall be conducted in Franklin County, Ohio, or via video conference. Day Shift will pay AAA filing and arbitrator fees for non-frivolous claims.</p>
<p><strong>CLASS ACTION AND JURY TRIAL WAIVER:</strong> YOU AND DAY SHIFT AGREE THAT EACH MAY BRING CLAIMS ONLY IN AN INDIVIDUAL CAPACITY, AND NOT AS A PLAINTIFF OR CLASS MEMBER IN ANY PURPORTED CLASS, COLLECTIVE, OR REPRESENTATIVE PROCEEDING. YOU WAIVE ANY RIGHT TO A JURY TRIAL AND ANY RIGHT TO PARTICIPATE IN A CLASS ACTION. If this class action waiver is found unenforceable, the arbitration provision shall be void, and the dispute shall proceed in court.</p>
<p><strong>Exceptions:</strong> Either party may bring an individual small claims action in Franklin County, Ohio, or seek injunctive relief in court for intellectual property infringement or misappropriation of trade secrets.</p>

<h2>15. INDEMNIFICATION</h2>
<p>You agree to indemnify and hold harmless Day Shift from any claims, damages, losses, and expenses (including attorneys' fees) arising from: (A) your use of the Service; (B) your violation of these Terms; (C) your violation of any third-party rights; (D) your User Content; or (E) any interactions between you and other users.</p>

<h2>16. FORCE MAJEURE</h2>
<p>Day Shift shall not be liable for any delay or failure to perform resulting from causes beyond its reasonable control, including acts of God, natural disasters, war, terrorism, government orders, labor disputes, internet failures, cyber attacks, or third-party service provider failures.</p>

<h2>17. THIRD-PARTY APP STORE TERMS</h2>
<p>If you download the Service through the Apple App Store or Google Play Store: (A) these Terms are between you and Day Shift only, not the App Store provider; (B) the App Store provider has no obligation to provide maintenance or support; (C) the App Store provider may refund the purchase price (if any) but has no other warranty obligation; (D) the App Store provider is not responsible for addressing claims relating to the Service; (E) you must comply with applicable third-party terms; and (F) the App Store provider is a third-party beneficiary of these Terms.</p>

<h2>18. TERMINATION</h2>
<p>Day Shift may suspend or terminate your account at any time, with or without cause or notice. Upon termination, your right to use the Service will immediately cease. You may delete your account at any time through the app settings. Surviving provisions include Disclaimer of Warranties, Limitation of Liability, Indemnification, Dispute Resolution, and Governing Law.</p>

<h2>19. GOVERNING LAW AND JURISDICTION</h2>
<p>These Terms shall be governed by and construed in accordance with the laws of the State of Ohio, without regard to conflict of law principles. To the extent any dispute is not subject to arbitration, you and Day Shift agree to submit to the exclusive personal jurisdiction of the state and federal courts located in Franklin County, Ohio.</p>

<h2>20. CHANGES TO TERMS</h2>
<p>Day Shift reserves the right to modify these Terms at any time. We will provide at least thirty (30) days' notice of material changes via posting on the Service, email, or in-app notice. Your continued use after the effective date constitutes acceptance. If you do not agree, you must stop using the Service and delete your account.</p>

<h2>21. SEVERABILITY AND WAIVER</h2>
<p>If any provision of these Terms is held invalid or unenforceable, the remaining provisions shall remain in full force and effect. The failure of Day Shift to enforce any right or provision shall not constitute a waiver. Any waiver must be in writing and signed by an authorized representative of Day Shift.</p>

<h2>22. ENTIRE AGREEMENT</h2>
<p>These Terms, together with the Privacy Policy and other incorporated policies, constitute the entire agreement between you and Day Shift regarding the Service.</p>

<h2>23. CONTACT</h2>
<p>For questions about these Terms, contact us at:</p>
<ul>
<li>Email (general): <a href="mailto:contact@dayshiftnow.me">contact@dayshiftnow.me</a></li>
<li>Email (legal): <a href="mailto:legal@dayshiftnow.me">legal@dayshiftnow.me</a></li>
<li>Email (DMCA/copyright): <a href="mailto:copyright@dayshiftnow.me">copyright@dayshiftnow.me</a></li>
</ul>
</div></body></html>"""

PRIVACY_HTML = f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0">
<title>Day Shift — Privacy Policy</title>
{LEGAL_BASE_STYLE}
</head><body><div class="container">
<div class="header-logo">DAY SHIFT</div>
<a href="/" class="back-link">← Back to Day Shift</a>
<h1>Privacy Policy</h1>
<p class="last-updated">Last updated: June 2026</p>

<p>DAY SHIFT, INC. ("DAY SHIFT," "WE," "US," OR "OUR") RESPECTS YOUR PRIVACY AND IS COMMITTED TO PROTECTING YOUR PERSONAL DATA. THIS PRIVACY POLICY DESCRIBES HOW WE COLLECT, USE, DISCLOSE, AND SAFEGUARD YOUR INFORMATION WHEN YOU USE OUR MOBILE APPLICATION AND RELATED SERVICES (THE "SERVICE"). BY USING THE SERVICE, YOU CONSENT TO THE DATA PRACTICES DESCRIBED IN THIS POLICY.</p>

<h2>1. INFORMATION WE COLLECT</h2>
<h3>Information You Provide Directly:</h3>
<ul>
<li><strong>Account Information:</strong> Name, email address, phone number, password (hashed and salted), role (Crew or Kitchen), and profile photo</li>
<li><strong>Profile Information:</strong> Bio, location, cuisine preferences, experience level, work history, certifications, availability, and hourly rate preferences</li>
<li><strong>Content:</strong> Videos, images, text posts, direct messages, and reviews you submit or transmit</li>
<li><strong>Payment Information:</strong> Payment details processed securely through PayPal. We do not receive, store, or have access to your full credit card or bank account numbers</li>
<li><strong>Communications:</strong> Messages sent to other users or our support team</li>
<li><strong>Verification Information:</strong> Any documentation you submit for optional identity or credential verification</li>
</ul>
<h3>Information Collected Automatically:</h3>
<ul>
<li><strong>Device Information:</strong> Device type, operating system, browser type, unique device identifiers</li>
<li><strong>Usage Data:</strong> Pages viewed, features used, time spent, and interactions with the Service</li>
<li><strong>Location Data:</strong> General location from IP address; precise location only with your permission</li>
<li><strong>Log Data:</strong> Access times, IP address, referring/exit URLs, crash reports</li>
<li><strong>Cookies:</strong> As described in Section 8</li>
</ul>

<h2>2. HOW WE USE YOUR INFORMATION</h2>
<p>We use your information to:</p>
<ul>
<li>Create, maintain, and authenticate your account</li>
<li>Provide, operate, improve, and personalize the Service</li>
<li>Facilitate connections and communication between Crew and Kitchens</li>
<li>Process transactions (Boosts, subscriptions) and send confirmations</li>
<li>Send administrative, technical, and security-related communications</li>
<li>Respond to your questions, comments, and support requests</li>
<li>Monitor and analyze usage trends and metrics</li>
<li>Detect, investigate, and prevent fraud, abuse, and security incidents</li>
<li>Enforce our Terms of Service</li>
<li>Comply with legal obligations</li>
<li>With your consent, send marketing communications (opt-out anytime)</li>
</ul>

<h2>3. SHARING AND DISCLOSURE OF INFORMATION</h2>
<p><strong>We do not sell your personal information for monetary consideration.</strong> We may share your information as follows:</p>
<ul>
<li><strong>With Other Users:</strong> Your profile, posts, and reviews are visible to other users. Direct messages are visible only to conversation participants.</li>
<li><strong>Service Providers and Subprocessors:</strong>
  <ul>
    <li><strong>PayPal</strong> — Payment processing. <a href="https://www.paypal.com/us/legalhub/privacy-full" target="_blank" rel="noopener">Privacy Policy</a></li>
    <li><strong>Resend</strong> — Email delivery for transactional and support communications. <a href="https://resend.com/legal/privacy-policy" target="_blank" rel="noopener">Privacy Policy</a></li>
    <li><strong>PostHog</strong> — Optional product analytics (only with your consent). <a href="https://posthog.com/privacy" target="_blank" rel="noopener">Privacy Policy</a></li>
    <li><strong>Sentry</strong> — Error monitoring and crash reporting. <a href="https://sentry.io/privacy/" target="_blank" rel="noopener">Privacy Policy</a></li>
    <li><strong>Google reCAPTCHA</strong> — Bot and abuse prevention. <a href="https://policies.google.com/privacy" target="_blank" rel="noopener">Privacy Policy</a></li>
    <li><strong>Cloud Hosting Provider</strong> — Infrastructure and database services</li>
  </ul>
</li>
<li><strong>Legal Requirements:</strong> We may disclose information to comply with law, regulation, legal process, or governmental request, or to protect our rights and the rights of others</li>
<li><strong>Business Transfers:</strong> In connection with any merger, acquisition, sale of assets, or similar transaction</li>
<li><strong>Aggregated or De-identified Data:</strong> We may share anonymized information that cannot identify you for any lawful purpose</li>
<li><strong>With Your Consent:</strong> For any other purpose with your express consent</li>
</ul>

<h2>4. DATA SECURITY</h2>
<p>We implement appropriate technical and organizational security measures, including encryption (TLS/HTTPS), password hashing, access controls, and regular security assessments. HOWEVER, NO METHOD OF TRANSMISSION OR ELECTRONIC STORAGE IS 100% SECURE. WE CANNOT GUARANTEE ABSOLUTE SECURITY. If you believe your interaction with the Service is no longer secure, notify us immediately at <a href="mailto:security@dayshiftnow.me">security@dayshiftnow.me</a>.</p>

<h2>5. DATA BREACH NOTIFICATION</h2>
<p>In the event of a data breach involving your personal information, we will notify affected users without undue delay via the email address associated with your account, and notify relevant regulatory authorities as required by applicable law. We maintain an incident response plan to mitigate the impact of any breach.</p>

<h2>6. DATA RETENTION</h2>
<p>We retain your personal information for as long as your account is active or as necessary to provide the Service, including to comply with legal obligations, resolve disputes, and enforce our agreements. Financial records are retained for seven (7) years per tax law. Account information is retained for the life of your account plus thirty (30) days. Messages and content are retained until deleted by you or upon account deletion. Access logs are retained for up to ninety (90) days. Upon account deletion, we will delete or anonymize your personal information within thirty (30) days, except where retention is required by law.</p>

<h2>7. YOUR RIGHTS AND CHOICES</h2>
<p>Depending on your jurisdiction, you may have rights to:</p>
<ul>
<li><strong>Access and Portability:</strong> Request a copy of your data</li>
<li><strong>Correction:</strong> Request correction of inaccurate information</li>
<li><strong>Deletion:</strong> Request deletion of your data, subject to legal exceptions</li>
<li><strong>Restriction and Objection:</strong> Restrict or object to certain processing</li>
<li><strong>Opt-Out of Marketing:</strong> Unsubscribe via email instructions or app settings</li>
<li><strong>Opt-Out of Sale/Sharing:</strong> California residents may opt out as described in Section 9</li>
<li><strong>Non-Discrimination:</strong> We will not discriminate for exercising your privacy rights</li>
</ul>
<p>To exercise these rights, contact us at <a href="mailto:privacy@dayshiftnow.me">privacy@dayshiftnow.me</a>. We will respond within thirty (30) to forty-five (45) days and may need to verify your identity.</p>

<h2>8. COOKIES AND TRACKING TECHNOLOGIES</h2>
<p>We use Cookies for: (A) Essential functions (authentication, security); (B) Preferences (remembering settings); and (C) Analytics (understanding usage via PostHog, only with your consent). We do not use third-party advertising cookies. You can manage preferences through our cookie consent banner or browser settings.</p>

<h2>9. CALIFORNIA PRIVACY RIGHTS (CCPA/CPRA)</h2>
<p>California residents have the following rights under the CCPA/CPRA: (A) Know what personal information we collect, use, disclose, and sell/share; (B) Access specific pieces of personal information; (C) Delete personal information; (D) Correct inaccurate information; (E) Opt out of the sale or sharing of personal information (though we do not sell or share personal information for cross-context behavioral advertising); (F) Limit use and disclosure of sensitive personal information; and (G) Not be discriminated against for exercising these rights.</p>
<p>We have collected the following categories of personal information in the past twelve (12) months: identifiers, customer records information, protected classification characteristics, commercial information, internet activity, geolocation data, audio/visual information, professional/employment information, and inferences. We collect this information directly from you, automatically from your device, and from service providers. We disclose information to service providers for business purposes as described in Section 3. We do not sell personal information and have not done so in the past twelve (12) months.</p>
<p>To exercise your California privacy rights, email <a href="mailto:privacy@dayshiftnow.me">privacy@dayshiftnow.me</a> with the subject line "CCPA Request."</p>

<h2>10. BIOMETRIC AND VIDEO DATA</h2>
<p>The Service allows you to upload videos and images that may contain facial images and other biometric data. By uploading such content, you consent to the collection, storage, and display of this content under this Privacy Policy and the Terms of Service. We do not use facial recognition technology or extract biometric identifiers from your content. You may delete your video and image content at any time. Illinois residents and users in other jurisdictions with biometric privacy laws: your continued use of the Service constitutes informed written consent to the collection and storage of biometric data as described herein. You may withdraw consent by deleting your content and contacting us.</p>

<h2>11. CHILDREN'S PRIVACY</h2>
<p>THE SERVICE IS NOT INTENDED FOR INDIVIDUALS UNDER 18. We do not knowingly collect personal information from children under 18. If we learn we have collected such information, we will delete it promptly. Parents or guardians who believe a child has provided us information should contact us immediately at <a href="mailto:privacy@dayshiftnow.me">privacy@dayshiftnow.me</a>.</p>

<h2>12. INTERNATIONAL DATA TRANSFERS</h2>
<p>Day Shift is based in the United States and processes information on U.S. servers. If you are located outside the United States, your information will be transferred to the United States, which may have different data protection laws than your jurisdiction. By using the Service, you consent to such transfers. We implement appropriate safeguards, including standard contractual clauses where applicable.</p>

<h2>13. THIRD-PARTY LINKS AND SERVICES</h2>
<p>The Service may contain links to or integrations with third-party websites, applications, or services. This Privacy Policy does not apply to those third parties. We are not responsible for their privacy practices, content, or security. We encourage you to review their privacy policies.</p>

<h2>14. LAWFUL BASIS FOR PROCESSING (EEA/UK USERS)</h2>
<p>If you are in the EEA or UK, our legal bases for processing include: performance of a contract (providing the Service), legitimate interests (improving and securing the Service), consent (marketing, precise location), and legal obligations.</p>

<h2>15. DO NOT TRACK SIGNALS</h2>
<p>We do not currently respond to browser "Do Not Track" signals. You may manage tracking through our cookie consent preferences described in Section 8.</p>

<h2>16. CHANGES TO THIS PRIVACY POLICY</h2>
<p>We may update this Privacy Policy from time to time. We will notify you of material changes by posting the updated policy on the Service, updating the "Last updated" date, and providing at least thirty (30) days' notice where required by law. Your continued use after the effective date constitutes acceptance. We encourage you to review this Privacy Policy periodically.</p>

<h2>17. CONTACT</h2>
<p>For questions, concerns, or requests regarding this Privacy Policy:</p>
<ul>
<li>Email (privacy): <a href="mailto:privacy@dayshiftnow.me">privacy@dayshiftnow.me</a></li>
<li>Email (security): <a href="mailto:security@dayshiftnow.me">security@dayshiftnow.me</a></li>
<li>Email (general): <a href="mailto:contact@dayshiftnow.me">contact@dayshiftnow.me</a></li>
<li>Response Time: Within thirty (30) days</li>
<li>EEA/UK users: You have the right to lodge a complaint with your local data protection supervisory authority</li>
</ul>
</div></body></html>"""


@api.get("/terms", response_class=HTMLResponse)
async def terms_of_service():
    """Standalone Terms of Service page for external linking."""
    return HTMLResponse(content=TERMS_HTML)


@api.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    """Standalone Privacy Policy page for external linking."""
    return HTMLResponse(content=PRIVACY_HTML)
