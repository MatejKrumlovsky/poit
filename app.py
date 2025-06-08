from flask import Flask, render_template, jsonify
import serial
import threading
import time
import os
import signal


app = Flask(__name__)

SERIAL_PORT = '/dev/ttyACM0'  # uprav podla svojho zariadenia
BAUD_RATE = 9600
ser = None

# Uchovavame data (timestamp, hodnota)
data_points = []
read_serial_active = False
system_initialized = False  # kontrola, ci bolo stlacene OPEN

# Funkcia na citanie dat zo serioveho portu
def read_serial():
    global data_points, read_serial_active, ser
    while True:
        if ser and ser.in_waiting > 0 and read_serial_active:
            line = ser.readline().decode(errors='ignore').strip()
            if line.isdigit():
                timestamp = time.time()
                value = int(line)
                data_points.append({"x": timestamp, "y": value})
        time.sleep(0.01)  # rýchlejšie čítanie

@app.route('/')
def index():
    return render_template('graph.html')

@app.route('/graf')
def graf():
    return render_template('casovy_graf.html')

@app.route('/cifernik')
def cif():
    return render_template('cifernik.html')

@app.route('/data')
def get_data():
    return jsonify(data_points if read_serial_active else [])

@app.route('/status')
def get_status():
    return jsonify({"initialized": system_initialized})

@app.route('/command/<cmd>')
def send_command(cmd):
    global read_serial_active, system_initialized, ser
    print(f"Prijatý príkaz: {cmd}")

    cmd = cmd.upper()

    if cmd == "OPEN":
        if system_initialized:
            return "Systém už je inicializovaný", 400
        try:
            ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
            time.sleep(2)  # Čakaj na inicializáciu Arduina
            ser.write(b'OPEN\n')
            system_initialized = True
            return "Systém inicializovaný", 200
        except Exception as e:
            print(f"Chyba pri inicializácii systému: {e}")
            return "Zlyhala inicializácia systému", 500

    if not system_initialized:
        return "Systém ešte nebol inicializovaný (OPEN)", 400

    if cmd == "START":
        ser.write(b'START\n')
        read_serial_active = True
        return "Monitorovanie spustené", 200
    elif cmd == "STOP":
        ser.write(b'STOP\n')
        read_serial_active = False
        return "Monitorovanie zastavené", 200
    elif cmd == "CLOSE":
        ser.write(b'CLOSE\n')
        read_serial_active = False
        system_initialized = False
        if ser:
            ser.close()
            ser = None
        os.kill(os.getpid(), signal.SIGINT)
        return "Spojenie ukončené", 200

    else:
        return "Neplatný príkaz", 400

# Spustenie vlakna na citanie az po OPEN
if __name__ == '__main__':
    threading.Thread(target=read_serial, daemon=True).start()
    app.run(debug=True, host='0.0.0.0')
