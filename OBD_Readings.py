import obd
import time

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
        dtcs.append("P0171")

    # System Too Rich (Bank 1)
    if maf > 3.5 and ltft < -10 and stft < -8:
        dtcs.append("P0172")

    # Mass Air Flow Circuit Range/Performance Problem
    if maf < 0.3 or maf > 10.0:
        dtcs.append("P0101")

    # -------------------------------
    # Misfire / Ignition Issues
    # -------------------------------

    # Random Misfire
    if rpm < 600 and throttle < 5 and timing < 10:
        dtcs.append("P0300")

    # Cylinder Misfire Detected (idle roughness simulation)
    if abs(stft) > 15 and rpm < 650:
        dtcs.append("P0301")

    # -------------------------------
    # Catalyst and O2 Sensor Monitoring
    # -------------------------------

    # Catalyst Efficiency Below Threshold
    if abs(o2s1 - o2s2) < 0.1 and o2s2 > 0.6:
        dtcs.append("P0420")

    # O2 Sensor Slow Response (Bank 1, Sensor 1)
    if abs(stft) > 12 and (o2s1 < 0.2 or o2s1 > 0.9):
        dtcs.append("P0133")

    # -------------------------------
    # Cooling System
    # -------------------------------

    # Coolant Thermostat Below Regulating Temperature
    if coolant < 70 and speed > 20:
        dtcs.append("P0128")

    # Engine Overheating
    if coolant > 105:
        dtcs.append("P0217")

    # -------------------------------
    # Fuel System Pressure
    # -------------------------------

    # Fuel Pressure too low
    if fuel_pressure < 35 and (maf < 1.5 or ltft > 12):
        dtcs.append("P0087")  # Fuel Rail/System Pressure Too Low

    # -------------------------------
    # Throttle / Air Intake
    # -------------------------------

    # Throttle position mismatch (e.g. limp mode)
    if throttle < 5 and rpm > 2500:
        dtcs.append("P2119")  # Throttle actuator control throttle body range

    # -------------------------------
    # Idle Control and Stability
    # -------------------------------

    # Idle RPM not stable — possible vacuum leak
    if 600 < rpm < 900 and abs(stft) > 10 and maf < 0.5:
        dtcs.append("P0507")  # Idle control system RPM higher than expected

    # -------------------------------
    # Intake Air Temperature Sensor
    # -------------------------------

    if intake < -10 or intake > 60:
        dtcs.append("P0113")  # IAT sensor circuit high input

    # -------------------------------
    # Deduplicate and return
    # -------------------------------
    return list(set(dtcs))

def get_OBD_readings() -> dict:
    conn = obd.OBD("COM9")  # connect to the other end of the VSPE virtual cable

    commands = {
        'RPM': obd.commands.RPM,
        'SPEED': obd.commands.SPEED,
        'COOLANT_TEMP': obd.commands.COOLANT_TEMP,
        'INTAKE_TEMP': obd.commands.INTAKE_TEMP,
        'MAF': obd.commands.MAF,
        'THROTTLE_POS': obd.commands.THROTTLE_POS,
        'SHORT_FUEL_TRIM_1': obd.commands.SHORT_FUEL_TRIM_1,    # STFT_B1
        'LONG_FUEL_TRIM_1':obd.commands.LONG_FUEL_TRIM_1,     # LTFT_B1
        'O2_B1S1': obd.commands.O2_B1S1,              # O2 sensor bank 1, sensor 1
        'O2_B1S2': obd.commands.O2_B1S2,              # O2 sensor bank 1, sensor 2
        'TIMING_ADVANCE': obd.commands.TIMING_ADVANCE,       # IGNITION_TIMING
        'FUEL_PRESSURE': obd.commands.FUEL_PRESSURE
    }

    data = {}
    for cmd1, cmd2 in commands.items():
        data[cmd1] = str(conn.query(cmd2))
    data['GET_DTC'] = detect_dtcs(data)             #simulate DTC fault code based on sensor data. Comment for real OBD2 Reader.
    
    return data