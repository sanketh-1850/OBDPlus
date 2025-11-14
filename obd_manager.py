import obd

class OBDManager:
    def __init__(self):
        self.conn = None

    def connect(self, port=None, test=False):
        if test:
            self.conn = obd.OBD("COM9")
        else:
            self.conn = obd.OBD(port) if port else obd.OBD(fast=False, timeout=5)
        return self.conn.is_connected()

    def get_conn(self):
        return self.conn

    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None
