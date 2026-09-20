from flask import Flask, request, render_template, session, redirect, url_for, jsonify, flash
import os, re, secrets, string, time
import requests

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
ACCESS_CODE = os.environ.get('ACCESS_CODE', 'HH35-TIK-2026')
USERNAME_RE = re.compile(r'^[A-Za-z0-9._]{2,24}$')
last_checks = {}


def allowed():
    return bool(session.get('access'))


def valid_username(value):
    return bool(USERNAME_RE.fullmatch(value)) and value not in {'.', '..'}


def check_tiktok(username):
    username = username.lstrip('@').strip()
    if not valid_username(username):
        return {'status': 'غير صالح', 'message': 'اكتب يوزرًا من أحرف أو أرقام أو نقطة فقط.'}
    now = time.monotonic()
    previous = last_checks.get(request.remote_addr, 0)
    if now - previous < 2:
        return {'status': 'انتظر قليلًا', 'message': 'انتظر ثانيتين بين كل فحص.'}
    last_checks[request.remote_addr] = now
    url = f'https://www.tiktok.com/@{username}'
    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10, allow_redirects=True)
        if response.status_code == 404:
            return {'status': 'غير مستخدم', 'message': '', 'username': username}
        if response.status_code == 200:
            return {'status': 'مستخدم', 'message': '', 'username': username, 'url': url}
        return {'status': 'غير قابل للتأكيد', 'message': 'تعذر التأكد من TikTok الآن.'}
    except requests.RequestException:
        return {'status': 'غير قابل للتأكيد', 'message': 'تعذر الوصول إلى TikTok الآن.'}


@app.route('/', methods=['GET', 'POST'])
def home():
    if request.method == 'POST':
        code = request.form.get('code', '').strip()
        if secrets.compare_digest(code, ACCESS_CODE):
            session['access'] = True
            return redirect(url_for('checker'))
        flash('الكود غير صحيح', 'error')
    return render_template('home.html')


@app.route('/checker')
def checker():
    if not allowed():
        return redirect(url_for('home'))
    return render_template('checker.html')


@app.post('/api/check')
def api_check():
    if not allowed():
        return jsonify(status='غير مصرح'), 401
    result = check_tiktok(request.form.get('username', ''))
    return jsonify(result)


@app.post('/api/suggestions')
def api_suggestions():
    if not allowed():
        return jsonify(status='غير مصرح'), 401
    length = max(2, min(int(request.form.get('length', 5)), 12))
    alphabet = string.ascii_lowercase + string.digits
    values = set()
    while len(values) < 2:
        core = ''.join(secrets.choice(alphabet) for _ in range(length))
        if secrets.randbelow(100) < 45 and length > 2:
            point = secrets.randbelow(length - 1) + 1
            core = core[:point] + '.' + core[point:]
        values.add(core)
    return jsonify(values=sorted(values))


@app.get('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
