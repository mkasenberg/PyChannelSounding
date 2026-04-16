import serial
import threading
import time
from queue import Queue


class DataReader(threading.Thread):
    def __init__(self, port, baudrate=115200):
        super().__init__(daemon=True)
        self.port = port
        self.baudrate = baudrate
        self.queue = Queue()
        self.stop_flag = threading.Event()
        self.ser = None

    def open_serial(self):
        while not self.stop_flag.is_set():
            try:
                self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
                return
            except serial.SerialException:
                print(f"[WARN] Reconnect failed: {self.port}")
                time.sleep(0.5)

    def run(self):
        self.open_serial()

        while not self.stop_flag.is_set():
            try:
                line = self.ser.readline()
                if not line:
                    continue

                if isinstance(line, (bytes, bytearray)):
                    try:
                        line = line.decode("utf-8", errors="ignore")
                    except:
                        continue

                line = line.strip()
                if line:
                    self.queue.put(line)

            except serial.SerialException:
                print(f"[ERR] Serial error on {self.port}, reconnecting...")
                self.open_serial()

    def stop(self):
        self.stop_flag.set()
        if self.ser:
            try:
                self.ser.close()
            except:
                pass
