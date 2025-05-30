import socket
from flask import session, jsonify
from flask import Flask, render_template, request, redirect, url_for, make_response
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError

from config import Config
from k8s_tool import KubernetesClient
from proxy import http_client
from tools import check_register

app = Flask(__name__)
app.config['SECRET_KEY'] = "iECgbYWReMNxkRprrzMo5KAQYnb2UeZ3bwvReTSt+VSESW0OB8zbglT+6rEcDW9X"

CSRFProtect(app)

k8s_client = KubernetesClient(Config.k8s_host, Config.k8s_token)


@app.before_request
def check_login():
    # 如果请求的是登录页，直接放行
    if request.path.startswith('/static/') or request.path == url_for('login'):
        return None

    if session.get('username') != Config.username:
        return redirect(url_for('login'))


@app.errorhandler(CSRFError)
def handle_csrf_error(e):
    return redirect(url_for('login'))


@app.route('/index', methods=['GET'])
def index():
    # deployment_name = Config.deployment_name
    # namespace = Config.k8s_namespace
    # ok, deployment = k8s_client.read_namespaced_deployment(deployment_name, namespace)
    # if not ok:
    #     return 'get deployment failed'
    # pod_num = deployment.spec.replicas
    # pod_ip = socket.gethostbyname(socket.gethostname())
    # version = 'v0.0.3'
    # return render_template('index.html', pod_num=pod_num, pod_ip=pod_ip, version=version)

    # 检查是否已经注册
    if check_register():
        return render_template('home.html')
    else:
        return redirect(url_for('register'))


@app.route('/', methods=['GET'])
def indexPage():
    if session.get('username') == Config.username:
        return redirect(url_for('index'))
    else:
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        if session.get('username') == Config.username:
            return redirect(url_for('index'))
        return render_template('login.html')
    username = request.form['username']
    password = request.form['password']
    if username == Config.username and password == Config.password:
        response = make_response(redirect(url_for('index')))
        session['username'] = username
        return response
    else:
        return render_template('login.html', errmsg='Invalid username or password')


@app.route('/logout', methods=['GET'])
def logout():
    session.pop('username', None)
    return jsonify({'code': 200, 'msg': 'Logout successfully'})


@app.route('/register', methods=['POST', 'GET'])
def register():
    if request.method == 'GET':
        return render_template('register.html')
    username = request.form.get('username')
    password = request.form.get('password')
    device_no = request.form.get('device_no')
    device_name = request.form.get('device_name')
    device_desc = request.form.get('device_desc')
    data = {
        'username': username,
        'password': password,
        'device_no': device_no,
        'device_name': device_name,
        'device_desc': device_desc
    }
    resp_data, ok = http_client.post('/api/device/register', data=data)
    # if not ok:
    #     return render_template('register.html', errmsg=resp_data, **data)
    return redirect(url_for('index'))


@app.route('/host_info', methods=['GET'])
def host_info():
    host_ip = socket.gethostbyname(socket.gethostname())
    return render_template('index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
