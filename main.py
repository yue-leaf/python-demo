import sqlite3
from flask import session, jsonify
from flask import Flask, render_template, request, redirect, url_for, make_response
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError

from config import Config
from k8s_tool import KubernetesClient
from proxy import http_client
from tools import init_k3s, apply_kubernetes_yaml, get_cluster_info, get_k8s_token, get_k8s_svc, create_configmap_tz, \
    install_helm, install_prometheus, install_telegraf, get_resource_path
from utils import get_os_info, get_hostname, get_network_interfaces_details, get_cpu_info, get_memory_info, \
    get_disk_info, get_cpu_mem_disk, get_machine_id
from threading import local

thread_local = local()
app = Flask(__name__)
app.config['SECRET_KEY'] = "iECgbYWReMNxkRprrzMo5KAQYnb2UeZ3bwvReTSt+VSESW0OB8zbglT+6rEcDW9X"

CSRFProtect(app)
app.config['WTF_CSRF_HEADERS'] = ['X-CSRFToken']

k8s_client = KubernetesClient(Config.k8s_host, Config.k8s_token)


def get_db_connection():
    if not hasattr(thread_local, 'connection'):
        thread_local.connection = sqlite3.connect('example.db')
        # 创建表
        cursor = thread_local.connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS device (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_name TEXT NOT NULL,
                device_no TEXT,
                registered_status INTEGER,
                initialized_status INTEGER,
                registered_time TEXT,
                device_desc TEXT,
                auth TEXT
            )
        ''')
        thread_local.connection.commit()
    return thread_local.connection


def get_cache_device():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM device")
    row = cursor.fetchone()
    if row:
        return {
            'device_name': row[1],
            'device_no': row[2],
            'registered_status': row[3],
            'initialized_status': row[4],
            'registered_time': row[5],
            'device_desc': row[6],
            'auth': row[7]
        }
    return None


def insert_device(device_name, device_no, registered_time, device_desc, auth):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO device (device_name, device_no, registered_status,initialized_status,registered_time, "
        "device_desc, auth) "
        " VALUES (?, ?, ?,?, ?,?,?)",
        (device_name, device_no, 1, 0, registered_time, device_desc, auth))
    conn.commit()


def update_device(device_no):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE device SET initialized_status = 1 WHERE device_no = ?", (device_no,))
    conn.commit()


def del_device(device_no):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM device WHERE device_no =?", (device_no,))
    conn.commit()


def close_db_connection():
    if hasattr(thread_local, 'connection'):
        thread_local.connection.close()
        del thread_local.connection


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
    try:
        device = get_cache_device()
    except Exception as e:
        return jsonify({'code': Config.fail_code, 'msg': str(e)})
    finally:
        close_db_connection()
    if device:
        return render_template('home.html', username=session.get('username'))
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
    device_no = get_machine_id()
    if request.method == 'GET':
        return render_template('register.html', device_no=device_no)
    ak = request.form.get('ak')
    sk = request.form.get('sk')
    device_name = request.form.get('device_name')
    device_desc = request.form.get('device_desc')
    cpu, mem, disk = get_cpu_mem_disk()
    network_interfaces = get_network_interfaces_details()
    data = {
        'ak': ak,
        'sk': sk,
        'device_no': device_no,
        'device_name': device_name,
        'device_desc': device_desc,
        'cpu': cpu,
        'memory': mem,
        'disk': disk,
        'network_interfaces': network_interfaces
    }
    resp_data, ok = http_client.post('/genbu/edge/device/register', data=data)
    if not ok:
        return render_template('register.html', errmsg=resp_data, **data)
    try:
        insert_device(device_name, device_no, resp_data['register_time'], device_desc, resp_data['auth'])
    except Exception as e:
        return render_template('register.html', errmsg=str(e), **data)
    finally:
        close_db_connection()
    return redirect(url_for('index'))


@app.route('/device_info', methods=['GET'])
def device_info():
    hostname = get_hostname()
    os_info = get_os_info()
    network_interfaces = get_network_interfaces_details()
    cpu_info = get_cpu_info()
    mem_info = get_memory_info()
    disk_info = get_disk_info()

    return render_template('device_info.html', hostname=hostname, os_info=os_info,
                           network_interfaces=network_interfaces, cpu_info=cpu_info,
                           mem_info=mem_info, disk_info=disk_info)


@app.route('/device_manage', methods=['GET'])
def device_manage():
    device = get_cache_device()
    if not device:
        return redirect(url_for('register'))
    devices = [
        {
            'device_no': device['device_no'],
            'device_name': device['device_name'],
            'device_desc': device['device_desc'],
            'registered_status': device['registered_status'],
            'initialized_status': device['initialized_status'],
            'registered_time': device['registered_time'],
        }
    ]
    return render_template('device_manage.html', devices=devices)


@app.route('/init_device', methods=['GET'])
def init_device():
    try:
        msg, ok = init_k3s()
        if not ok:
            return jsonify({'code': Config.fail_code, 'msg': msg})
        device = get_cache_device()
        if not device:
            return jsonify({'code': Config.fail_code, 'msg': 'Device not registered'})
        cluster_info = get_cluster_info()
        if not cluster_info:
            return jsonify({'code': Config.fail_code, 'msg': 'Failed to get cluster info'})

        data = {
            'auth': device['auth'],
            'device_no': device['device_no'],
            'name': cluster_info['cluster_name'],
            'age': cluster_info['age'],
            'num': cluster_info['node_count'],
            'version': cluster_info['version'],
        }
        response, ok = http_client.post('/genbu/edge/device/init_script', data=data)
        if not ok:
            return jsonify({'code': Config.fail_code, 'msg': "Failed to get init script"})
        init_script = response['init_script']
        ok = apply_kubernetes_yaml(init_script)
        if not ok:
            return jsonify({'code': Config.fail_code, 'msg': 'Failed to apply Kubernetes YAML'})
        fluent_bit_script = response.get('fluent_bit_script', None)
        if fluent_bit_script:
            ok = create_configmap_tz()
            if not ok:
                return jsonify({'code': Config.fail_code, 'msg': 'Failed to create configmap tz'})
            ok = apply_kubernetes_yaml(fluent_bit_script)
            if not ok:
                return jsonify({'code': Config.fail_code, 'msg': 'Failed to apply fluent-bit YAML'})
        telegraf_script = response.get('telegraf_script', None)
        if telegraf_script:
            ok = install_helm()
            if not ok:
                return jsonify({'code': Config.fail_code, 'msg': 'Failed to install helm'})
            ok = install_prometheus()
            if not ok:
                return jsonify({'code': Config.fail_code, 'msg': 'Failed to install prometheus'})
            ok = install_telegraf(telegraf_script)
            if not ok:
                return jsonify({'code': Config.fail_code, 'msg': 'Failed to install telegraf'})
        k8s_token, ok = get_k8s_token()
        if not ok:
            return jsonify({'code': Config.fail_code, 'msg': 'Failed to get k8s token'})
        k8s_host, ok = get_k8s_svc()
        if not ok:
            return jsonify({'code': Config.fail_code, 'msg': 'Failed to get k8s host'})
        data['k8s_url'] = k8s_host
        data['k8s_token'] = k8s_token
        response, ok = http_client.post('/genbu/edge/device/init_success', data=data)
        if not ok:
            return jsonify({'code': Config.fail_code, 'msg': response})
        try:
            update_device(device['device_no'])
        except Exception as e:
            return jsonify({'code': Config.fail_code, 'msg': str(e)})
        finally:
            close_db_connection()
        return jsonify({'code': Config.success_code, 'msg': 'Device initialized successfully'})
    except Exception as e:
        return jsonify({'code': Config.fail_code, 'msg': str(e)})


@app.route('/delete_device', methods=['POST'])
def delete_device():
    data = request.get_json()
    device_no = data.get('device_no')
    try:
        http_client.delete('/genbu/edge/device/delete', data={'device_no': device_no})
        del_device(device_no)
    except Exception as e:
        return jsonify({'code': Config.fail_code, 'msg': str(e)})
    return jsonify({'code': Config.success_code, 'msg': 'Device deleted successfully'})


@app.route('/get_pkg', methods=['GET'])
def get_pkg():
    path = get_resource_path('pkg')
    return jsonify({'code': 200, 'msg': path})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
