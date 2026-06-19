"""Standalone legal pages (Terms of Service & Privacy Policy) for Stripe/external linking."""
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
p{margin-bottom:1rem;font-size:0.9rem;color:#CCC}
ul{margin-bottom:1rem;padding-left:1.5rem}
li{font-size:0.9rem;color:#CCC;margin-bottom:0.4rem}
a{color:#F97316;text-decoration:none}
a:hover{text-decoration:underline}
.back-link{display:inline-block;margin-bottom:1.5rem;color:#F97316;font-size:0.85rem;font-weight:500}
.back-link:hover{text-decoration:underline}
.header-logo{font-size:1.5rem;font-weight:700;color:#F97316;margin-bottom:0.25rem;letter-spacing:0.05em}
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

<h2>1. ACCEPTANCE OF TERMS</h2>
<p>By accessing or using the Day Shift mobile application ("the Service"), you ("User," "you," or "your") acknowledge that you have read, understood, and agree to be bound by these Terms of Service ("Terms"). If you do not agree to these Terms, do not use the Service.</p>

<h2>2. ELIGIBILITY AND AGE REQUIREMENTS</h2>
<p>The Service is intended solely for individuals who are eighteen (18) years of age or older. By using the Service, you represent and warrant that you are at least 18 years of age and possess the legal right and capacity to enter into a binding agreement.</p>

<h2>3. DESCRIPTION OF SERVICE</h2>
<p>Day Shift is a technology platform that facilitates connections between culinary industry workers ("Crew") and food service establishments ("Kitchens") for the purpose of identifying shift-based employment opportunities. Day Shift acts solely as a technology intermediary and matching platform. Day Shift is not an employment agency, recruiting firm, staffing service, or employer of any kind. Day Shift does not employ, hire, or contract with crew members; guarantee the availability, quality, or outcome of any shift; verify the qualifications or background of any user; set or collect wages; or supervise any work relationship.</p>

<h2>4. USER ACCOUNTS AND REGISTRATION</h2>
<p>To access certain features, you must create an account. You agree to provide accurate, current, and complete information during registration and to update such information to keep it accurate. You are responsible for maintaining the security of your account credentials and for all activities that occur under your account.</p>

<h2>5. USER CONTENT</h2>
<p>You retain all ownership rights in and to any content you submit, post, or display on the Service ("User Content"), including videos, images, text, and profile information. By posting User Content, you grant to Day Shift a worldwide, non-exclusive, royalty-free, sublicensable, and transferable license to use, reproduce, modify, publish, distribute, and display such User Content in connection with operating the Service. You represent that you own or have the necessary rights to submit the User Content and that it does not infringe any third party's intellectual property rights.</p>

<h2>6. PROHIBITED CONDUCT</h2>
<p>You agree not to:</p>
<ul>
<li>Post content that is illegal, harassing, discriminatory, or sexually explicit</li>
<li>Impersonate another person or misrepresent your identity or qualifications</li>
<li>Use the Service for any unlawful purpose or in violation of any law</li>
<li>Attempt to disrupt, damage, or gain unauthorized access to the Service</li>
<li>Post content longer than 60 seconds in video format</li>
<li>Spam, solicit, or send unsolicited commercial messages</li>
</ul>

<h2>7. BOOST AND ADVERTISING</h2>
<p>Day Shift offers paid visibility features ("Boosts") that increase the visibility of user posts. Boost purchases are processed through third-party payment processors (Stripe). All boost purchases are final and non-refundable unless required by law. Promotional codes may provide free or discounted boosts and are subject to the terms specified at the time of the offer.</p>

<h2>8. INTELLECTUAL PROPERTY</h2>
<p>The Service, including its design, features, and branding, is owned by Day Shift and protected by intellectual property laws. You may not copy, modify, distribute, or create derivative works from the Service without prior written consent.</p>

<h2>9. DISCLAIMER OF WARRANTIES</h2>
<p>The Service is provided "as is" and "as available" without warranties of any kind, whether express or implied. Day Shift does not warrant that the Service will be uninterrupted, error-free, or secure, or that any match or employment opportunity will result from using the Service.</p>

<h2>10. LIMITATION OF LIABILITY</h2>
<p>To the maximum extent permitted by law, Day Shift shall not be liable for any indirect, incidental, special, consequential, or punitive damages, or any loss of profits or revenues, arising from your use of the Service.</p>

<h2>11. TERMINATION</h2>
<p>Day Shift may suspend or terminate your account at any time, with or without cause or notice. Upon termination, your right to use the Service will immediately cease.</p>

<h2>12. GOVERNING LAW</h2>
<p>These Terms shall be governed by and construed in accordance with the laws of the United States, without regard to conflict of law principles.</p>

<h2>13. CHANGES TO TERMS</h2>
<p>We may update these Terms from time to time. We will notify users of material changes by posting the updated Terms on the Service. Your continued use of the Service following any changes constitutes acceptance of the revised Terms.</p>

<h2>14. CONTACT</h2>
<p>For questions about these Terms, contact us at <a href="mailto:support@dayshift.app">support@dayshift.app</a>.</p>
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

<h2>1. INFORMATION WE COLLECT</h2>
<p>We collect information you provide directly, including your name, email, password, role (crew or kitchen), profile photo, bio, location, cuisine type, and video content. We also automatically collect device information, usage data, and cookies.</p>

<h2>2. HOW WE USE YOUR INFORMATION</h2>
<p>We use your information to:</p>
<ul>
<li>Create and manage your account</li>
<li>Facilitate matching between crew and kitchens</li>
<li>Enable in-app messaging and notifications</li>
<li>Process boost payments and tips via Stripe</li>
<li>Display user profiles and video content</li>
<li>Maintain safety and enforce community guidelines</li>
<li>Send service-related communications</li>
</ul>

<h2>3. INFORMATION SHARING</h2>
<p>We do not sell your personal information. We share information with third-party vendors who perform services on our behalf, including hosting, analytics, payment processing (Stripe), and email delivery. We may disclose information when required by law or to protect our rights.</p>

<h2>4. VIDEO CONTENT</h2>
<p>Videos you post are visible to other users on the platform. Videos are limited to 60 seconds in duration. You control your video content and may delete it at any time. Once deleted, videos are removed from public view.</p>

<h2>5. PAYMENT INFORMATION</h2>
<p>For advertisers and boost purchases, payment details are processed securely via Stripe. We do not store full card numbers. Stripe's privacy policy applies to payment information.</p>

<h2>6. DATA SECURITY</h2>
<p>We implement appropriate technical and organizational measures to protect your information, including encrypted password hashing, secure connections (HTTPS), and access controls. However, no method of transmission over the internet is 100% secure.</p>

<h2>7. YOUR RIGHTS</h2>
<p>You have the right to access, correct, or delete your personal information. You can delete your account through the app, which removes your profile and content. To exercise these rights, contact us at <a href="mailto:privacy@dayshift.app">privacy@dayshift.app</a>.</p>

<h2>8. CHILDREN'S PRIVACY</h2>
<p>The Service is not directed to individuals under 18. We do not knowingly collect personal information from children under 18. If you believe a child has provided us information, contact us and we will delete it.</p>

<h2>9. INTERNATIONAL DATA TRANSFERS</h2>
<p>Your information may be transferred to and processed in the United States or other countries where we or our service providers operate. By using the Service, you consent to such transfers.</p>

<h2>10. COOKIES AND TRACKING</h2>
<p>We use cookies and similar technologies to operate the Service, analyze usage, and improve functionality. You can control cookies through your browser settings.</p>

<h2>11. CHANGES TO THIS PRIVACY POLICY</h2>
<p>We may update this Privacy Policy from time to time. We will notify you of material changes by posting the updated policy on the Service. Your continued use of the Service following any changes constitutes acceptance.</p>

<h2>12. CONTACT</h2>
<p>For questions or requests regarding this Privacy Policy, contact us at:</p>
<ul>
<li>Email: <a href="mailto:privacy@dayshift.app">privacy@dayshift.app</a></li>
<li>Response Time: We will respond within thirty (30) days</li>
</ul>
</div></body></html>"""


@api.get("/terms", response_class=HTMLResponse)
async def terms_of_service():
    """Standalone Terms of Service page for Stripe/external linking."""
    return HTMLResponse(content=TERMS_HTML)


@api.get("/privacy", response_class=HTMLResponse)
async def privacy_policy():
    """Standalone Privacy Policy page for Stripe/external linking."""
    return HTMLResponse(content=PRIVACY_HTML)
