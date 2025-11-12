import obd
import time
import threading

test = True

def detect_dtcs(data):
    dtcs = []

    # Helper for safe numeric conversion
    def val(key):
        try:
            return float(str(data.get(key, 0)).split(' ')[0])
        except Exception:
            return 0.0

    rpm = val("RPM")
    speed = val("SPEED")
    coolant = val("COOLANT_TEMP")
    intake = val("INTAKE_TEMP")
    maf = val("MAF")
    throttle = val("THROTTLE_POS")
    stft = val("SHORT_FUEL_TRIM_1")
    ltft = val("LONG_FUEL_TRIM_1")
    o2s1 = val("O2_B1S1")
    o2s2 = val("O2_B1S2")
    timing = val("TIMING_ADVANCE")
    fuel_pressure = val("FUEL_PRESSURE")

    # -------------------------------
    # Fuel Mixture and Airflow Faults
    # -------------------------------

    # System Too Lean (Bank 1)
    if maf < 0.6 and ltft > 10 and stft > 8:
        dtcs.append(("P0171", "System Too Lean Bank 1"))

    # System Too Rich (Bank 1)
    if maf > 3.5 and ltft < -10 and stft < -8:
        dtcs.append(("P0172", "System Too Rich (Bank 1)"))

    # Mass Air Flow Circuit Range/Performance Problem
    if maf < 0.3 or maf > 10.0:
        dtcs.append(("P0101", "MAF Circuit Range/Performance"))

    # -------------------------------
    # Misfire / Ignition Issues
    # -------------------------------

    # Random Misfire
    if rpm < 600 and throttle < 5 and timing < 10:
        dtcs.append(("P0300", "Random Misfire Detected Code"))

    # Cylinder Misfire Detected (idle roughness simulation)
    if abs(stft) > 15 and rpm < 650:
        dtcs.append(("P0301", "Cylinder #1 Misfire"))

    # -------------------------------
    # Catalyst and O2 Sensor Monitoring
    # -------------------------------

    # Catalyst Efficiency Below Threshold
    if abs(o2s1 - o2s2) < 0.1 and o2s2 > 0.6:
        dtcs.append(("P0420", "Catalyst System Efficiency Below Threshold"))

    # O2 Sensor Slow Response (Bank 1, Sensor 1)
    if abs(stft) > 12 and (o2s1 < 0.2 or o2s1 > 0.9):
        dtcs.append(("P0133", "Oxygen Sensor Circuit Slow Response"))

    # -------------------------------
    # Cooling System
    # -------------------------------

    # Coolant Thermostat Below Regulating Temperature
    if coolant < 70 and speed > 20:
        dtcs.append(("P0128", "Thermostat OBD-II Trouble Code"))

    # Engine Overheating
    if coolant > 105:
        dtcs.append(("P0217", "Engine Over Temperature"))

    # -------------------------------
    # Fuel System Pressure
    # -------------------------------

    # Fuel Pressure too low
    if fuel_pressure < 35 and (maf < 1.5 or ltft > 12):
        dtcs.append(("P0087", "Fuel Rail/System Pressure - Too Low"))  # Fuel Rail/System Pressure Too Low

    # -------------------------------
    # Throttle / Air Intake
    # -------------------------------

    # Throttle position mismatch (e.g. limp mode)
    if throttle < 5 and rpm > 2500:
        dtcs.append(("P2119", "Throttle Actuator Control Throttle Body Range"))  # Throttle actuator control throttle body range

    # -------------------------------
    # Idle Control and Stability
    # -------------------------------

    # Idle RPM not stable — possible vacuum leak
    if 600 < rpm < 900 and abs(stft) > 10 and maf < 0.5:
        dtcs.append(("P0507", "Idle Air Control System RPM Higher Than Expected"))  # Idle control system RPM higher than expected

    # -------------------------------
    # Intake Air Temperature Sensor
    # -------------------------------

    if intake < -10 or intake > 60:
        dtcs.append(("P0113", "IAT Sensor 1 Circuit High Input"))  # IAT sensor circuit high input

    # -------------------------------
    # Deduplicate and return
    # -------------------------------
    return list(set(dtcs))


# ===============================
# OBD Command Dictionaries
# ===============================

# --- Mode 1: Live Data Commands ---
live_commands = {
    'RPM': obd.commands.RPM,
    'SPEED': obd.commands.SPEED,
    'COOLANT_TEMP': obd.commands.COOLANT_TEMP,
    'INTAKE_TEMP': obd.commands.INTAKE_TEMP,
    'MAF': obd.commands.MAF,
    'THROTTLE_POS': obd.commands.THROTTLE_POS,
    'SHORT_FUEL_TRIM_1': obd.commands.SHORT_FUEL_TRIM_1,
    'LONG_FUEL_TRIM_1': obd.commands.LONG_FUEL_TRIM_1,
    'O2_B1S1': obd.commands.O2_B1S1,
    'O2_B1S2': obd.commands.O2_B1S2,
    'TIMING_ADVANCE': obd.commands.TIMING_ADVANCE,
    'FUEL_PRESSURE': obd.commands.FUEL_PRESSURE,
}

# --- Mode 2: Freeze Frame Commands ---
freeze_commands = {
    'RPM': obd.commands.DTC_RPM,
    'SPEED': obd.commands.DTC_SPEED,
    'COOLANT_TEMP': obd.commands.DTC_COOLANT_TEMP,
    'INTAKE_TEMP': obd.commands.DTC_INTAKE_TEMP,
    'MAF': obd.commands.DTC_MAF,
    'THROTTLE_POS': obd.commands.DTC_THROTTLE_POS,
    'SHORT_FUEL_TRIM_1': obd.commands.DTC_SHORT_FUEL_TRIM_1,
    'LONG_FUEL_TRIM_1': obd.commands.DTC_LONG_FUEL_TRIM_1,
    'O2_B1S1': obd.commands.DTC_O2_B1S1,
    'O2_B1S2': obd.commands.DTC_O2_B1S2,
    'TIMING_ADVANCE': obd.commands.DTC_TIMING_ADVANCE,
    'FUEL_PRESSURE': obd.commands.DTC_FUEL_PRESSURE,
}


# ===============================
# Core OBD Functions
# ===============================

def get_dtc_codes(conn):
    """
    Read all active Diagnostic Trouble Codes (DTCs) from the ECU.
    """
    try:
        if test:
            dtcs = detect_dtcs(get_freeze_frame(conn))
        else:
            response = conn.query(obd.commands.GET_DTC)
            if response.is_null():
                return []
            dtcs = [(code, desc) for code, desc in response.value]
        return dtcs
    except Exception as e:
        print(f"[get_dtc_codes] Error: {e}")
        return []


def clear_dtc(conn):
    """
    Clear all Diagnostic Trouble Codes.
    """
    try:
        conn.query(obd.commands.CLEAR_DTC)
        return "✅ DTCs cleared successfully."
    except Exception as e:
        print(f"[clear_dtc] Error: {e}")
        return f"❌ Failed to clear DTCs: {e}"


def get_freeze_frame(conn):
    """
    Retrieve freeze-frame data (snapshot when the DTC was set).
    """
    frame_data = {}
    if test:
        return get_live_data(conn)
    else:
        for name, cmd in freeze_commands.items():
            try:
                resp = conn.query(cmd)
                frame_data[name] = str(resp.value) if not resp.is_null() else "N/A"
            except Exception as e:
                frame_data[name] = f"Error: {e}"
        return frame_data


def get_live_data(conn):
    """
    Read current live sensor data once (non-continuous).
    """
    live_data = {}
    for name, cmd in live_commands.items():
        try:
            resp = conn.query(cmd)
            live_data[name] = str(resp.value) if not resp.is_null() else "N/A"
        except Exception as e:
            live_data[name] = f"Error: {e}"
    return live_data


# ===============================
# Continuous Live Data Polling
# ===============================

live_data_cache = {}
polling_active = False


def start_live_polling(conn, interval=1):
    """
    Continuously query live OBD data every `interval` seconds in a background thread.
    """
    global polling_active
    polling_active = True

    def poll():
        global live_data_cache
        print("✅ Live data polling started.")
        while polling_active:
            try:
                data = get_live_data(conn)
                live_data_cache = data
                time.sleep(interval)
            except Exception as e:
                print(f"[Polling] Error: {e}")
                break
        print("🛑 Live data polling thread ended.")

    thread = threading.Thread(target=poll, daemon=True)
    thread.start()


def stop_live_polling():
    """
    Stop the continuous live data polling thread.
    """
    global polling_active
    polling_active = False
    print("🛑 Live data polling stopped.")


def get_latest_live_data():
    """
    Return the most recent cached live data snapshot.
    """
    return live_data_cache