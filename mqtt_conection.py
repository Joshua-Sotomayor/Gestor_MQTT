import os
import subprocess
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt

app = Flask(__name__)
socketio = SocketIO(app)

# Rutas predeterminadas según la guía [cite: 393, 394, 395]
MOSQUITTO_PATH = r"C:\Program Files\mosquitto"
CONFIG_FILE = os.path.join(MOSQUITTO_PATH, "mosquitto.conf")
PASSWD_FILE = os.path.join(MOSQUITTO_PATH, "user_pass.txt")

# --- Lógica de MQTT para la "Mini CMD" ---
def on_message(client, userdata, message):
    payload = message.payload.decode()
    topic = message.topic
    # Enviamos el dato a la interfaz web en tiempo real
    socketio.emit('mqtt_data', {'topic': topic, 'message': payload})

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message

# --- Funciones de Control del Broker ---

def run_command(command):
    """Ejecuta comandos de consola y retorna el resultado [cite: 469, 534]"""
    try:
        # Nota: Se requiere ejecutar el script como Administrador para sc start/stop [cite: 534]
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout if result.returncode == 0 else result.stderr
    except Exception as e:
        return str(e)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/service/<action>')
def manage_service(action):
    """Inicia o detiene el servicio de Mosquitto """
    cmd = f"sc {action} mosquitto"
    output = run_command(cmd)
    return jsonify({"status": "success", "output": output})

@app.route('/add_user', methods=['POST'])
def add_user():
    """Crea o actualiza usuarios en el archivo de contraseñas [cite: 716, 731, 739]"""
    user = request.json.get('username')
    pw = request.json.get('password')
    
    # -b permite añadir usuario y contraseña en una sola línea 
    cmd = f'"{os.path.join(MOSQUITTO_PATH, "mosquitto_passwd.exe")}" -b "{PASSWD_FILE}" {user} {pw}'
    output = run_command(cmd)
    return jsonify({"status": "success", "output": "Usuario procesado"})

@app.route('/configure_broker', methods=['POST'])
def configure_broker():
    """Configura IP, puerto y seguridad en mosquitto.conf [cite: 398, 403, 741]"""
    port = request.json.get('port', '1883')
    secure = request.json.get('secure') # Booleano
    
    config_content = [
        "per_listener_settings true\n",
        f"listener {port}\n",
        "allow_anonymous false\n",
        f"password_file {PASSWD_FILE}\n"
    ]
    
    if secure:
        # Aquí podrías añadir rutas a certificados TLS/SSL [cite: 54, 403]
        config_content.append("protocol mqtt\n") 

    try:
        with open(CONFIG_FILE, "w") as f:
            f.writelines(config_content)
        return jsonify({"status": "success", "message": "Configuración actualizada. Reinicie el broker."})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

@app.route('/connect_mqtt', methods=['POST'])
def connect_mqtt():
    """Conecta el 'escucha' para ver el flujo de datos [cite: 37, 71]"""
    ip = request.json.get('ip', 'localhost')
    port = int(request.json.get('port', 1883))
    
    try:
        mqtt_client.connect(ip, port)
        mqtt_client.subscribe("#") # Se suscribe a todo para ver el flujo 
        mqtt_client.loop_start()
        return jsonify({"status": "connected"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    # Es vital ejecutar como admin para comandos 'sc' y acceso a Archivos de Programa [cite: 534, 775]
    socketio.run(app, debug=True)