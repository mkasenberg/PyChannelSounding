import os
import threading
import datetime
import tkinter as tk
import queue
import numpy as np
import re
from os.path import realpath
from tkinter import font
from openpyxl import Workbook
from openpyxl.chart import LineChart, Reference

from data_reader import DataReader

C = 299_792_458.0  # m/s
root = tk.Tk()
label: tk.Label | None = None
data_queue = queue.Queue()


IQ_LINE_RE = re.compile(r'^-?\d+( -?\d+)*$')


def parse_report(line):
    print(line)
    if not IQ_LINE_RE.match(line):
        return None

    values = list(map(int, line.split()))
    samples_count = values[0]
    values_count = len(values)

    values_per_sample = 5
    expected_count = 1 + samples_count * values_per_sample
    if values_count < expected_count:
        print(f"Report truncated: received {values_count} numbers, expected {expected_count}")
        return None

    fs = []
    Iis = []
    Qis = []
    Irs = []
    Qrs = []

    for i in range(1, values_count, values_per_sample):
        fs.append(values[i])
        Iis.append(values[i + 1])
        Qis.append(values[i + 2])
        Irs.append(values[i + 3])
        Qrs.append(values[i + 4])

    return fs, Iis, Qis, Irs, Qrs


def process_samples(samples, make_excel, filename="report.xlsx"):
    fs, Iis, Qis, Irs, Qrs = samples

    fs = np.array(fs[1:])
    Iis = np.array(Iis[1:], dtype=np.int16)
    Qis = np.array(Qis[1:], dtype=np.int16)
    Irs = np.array(Irs[1:], dtype=np.int16)
    Qrs = np.array(Qrs[1:], dtype=np.int16)

    fs_idx = np.argsort(fs)
    fs = fs[fs_idx]
    Iis = Iis[fs_idx]
    Qis = Qis[fs_idx]
    Irs = Irs[fs_idx]
    Qrs = Qrs[fs_idx]

    f_hz = 2402e6 + 1e6 * np.array(fs)

    PCT_i = np.array(Iis) + 1j * np.array(Qis)
    PCT_r = np.array(Irs) + 1j * np.array(Qrs)
    H2 = PCT_r * PCT_i
    phi_H2 = np.angle(H2)
    theta_CH = np.unwrap(phi_H2)

    f0 = np.mean(f_hz)
    slope, intercept = np.polyfit(f_hz - f0, theta_CH, 1)
    print(f'slope={slope}, intercept={intercept}')
    tof = -slope / (2 * np.pi)
    d = tof * C
    data_queue.put(d)
    print(f"DISTANCE: {d}")

    if not make_excel:
        return

    wb = Workbook()
    ws = wb.active
    ws.title = "Samples"

    # Headers
    ws.append(
        ["Index", "Ii", "Qi", "Ir", "Qr", "Ph_I", "Ph_R", "Ph_H2", "Ph_H2_Unwrapped"])

    N = len(fs)
    for idx, (
        f, Ii, Qi, Ir, Qr, phase_i, phase_r, phase_h2, phase_h2_unwrapped) in enumerate(
            zip(fs, Iis, Qis, Irs, Qrs,
                np.arctan2(Qis, Iis),
                np.arctan2(Qrs, Irs),
                phi_H2, theta_CH)):
        ws.append([idx,  # A
                   Ii,  # B
                   Qi,  # C
                   Ir,  # D
                   Qr,  # E
                   phase_i,  # F
                   phase_r,  # G
                   phase_h2,  # H
                   phase_h2_unwrapped,  # I
                   ])

    # IQ Samples I chart
    chart = LineChart()
    chart.title = "IQ Samples I"
    chart.x_axis.title = "Sample index"
    chart.y_axis.title = "Value"
    chart.smooth = False

    data = Reference(ws, min_col=2, max_col=3, min_row=1, max_row=N + 1)
    chart.add_data(data, titles_from_data=True)

    xvalues = Reference(ws, min_col=1, min_row=2, max_row=N + 1)
    chart.set_categories(xvalues)

    # Add markers
    for serie in chart.series:
        serie.smooth = False
        serie.marker.symbol = "circle"
        serie.marker.size = 4

    ws.add_chart(chart, "S1")

    # IQ Samples R chart
    chart2 = LineChart()
    chart2.title = "IQ Samples R"
    chart2.x_axis.title = "Sample index"
    chart2.y_axis.title = "Value"
    chart2.smooth = False

    data2 = Reference(ws, min_col=4, max_col=5, min_row=1, max_row=N + 1)
    chart2.add_data(data2, titles_from_data=True)

    xvalues2 = Reference(ws, min_col=1, min_row=2, max_row=N + 1)
    chart2.set_categories(xvalues2)

    # Add markers
    for serie in chart2.series:
        serie.smooth = False
        serie.marker.symbol = "circle"
        serie.marker.size = 4

    ws.add_chart(chart2, f"S{1 * 15}")

    # Ph_I chart
    chart3 = LineChart()
    chart3.title = "Ph_I"
    chart3.x_axis.title = "Sample index"
    chart3.y_axis.title = "Value"
    chart3.smooth = False

    data3 = Reference(ws, min_col=6, max_col=6, min_row=1, max_row=N + 1)
    chart3.add_data(data3, titles_from_data=True)

    xvalues3 = Reference(ws, min_col=1, min_row=2, max_row=N + 1)
    chart3.set_categories(xvalues3)

    # Add markers
    for serie in chart3.series:
        serie.smooth = False
        serie.marker.symbol = "circle"
        serie.marker.size = 4

    ws.add_chart(chart3, f"S{2 * 15}")

    # Ph_R chart
    chart4 = LineChart()
    chart4.title = "Ph_R"
    chart4.x_axis.title = "Sample index"
    chart4.y_axis.title = "Value"
    chart4.smooth = False

    data4 = Reference(ws, min_col=7, max_col=7, min_row=1, max_row=N + 1)
    chart4.add_data(data4, titles_from_data=True)

    xvalues4 = Reference(ws, min_col=1, min_row=2, max_row=N + 1)
    chart4.set_categories(xvalues4)

    # Add markers
    for serie in chart4.series:
        serie.smooth = False
        serie.marker.symbol = "circle"
        serie.marker.size = 4

    ws.add_chart(chart4, f"S{3 * 15}")

    # Ph_R chart
    chart5 = LineChart()
    chart5.title = "Ph_H2"
    chart5.x_axis.title = "Sample index"
    chart5.y_axis.title = "Value"
    chart5.smooth = False

    data5 = Reference(ws, min_col=8, max_col=8, min_row=1, max_row=N + 1)
    chart5.add_data(data5, titles_from_data=True)

    xvalues5 = Reference(ws, min_col=1, min_row=2, max_row=N + 1)
    chart5.set_categories(xvalues5)

    # Add markers
    for serie in chart5.series:
        serie.smooth = False
        serie.marker.symbol = "circle"
        serie.marker.size = 4

    ws.add_chart(chart5, f"S{4 * 15}")

    # Ph_R Unwrapped chart
    chart6 = LineChart()
    chart6.title = "Ph_H2_Unwrapped"
    chart6.x_axis.title = "Sample index"
    chart6.y_axis.title = "Value"
    chart6.smooth = False

    data6 = Reference(ws, min_col=9, max_col=9, min_row=1, max_row=N + 1)
    chart6.add_data(data6, titles_from_data=True)

    xvalues6 = Reference(ws, min_col=1, min_row=2, max_row=N + 1)
    chart6.set_categories(xvalues6)

    # Add markers
    for serie in chart6.series:
        serie.smooth = False
        serie.marker.symbol = "circle"
        serie.marker.size = 4

    ws.add_chart(chart6, f"S{5 * 15}")

    wb.save(filename)
    print(f"Excel saved to {filename}")


def serial_reader():
    port = realpath('/dev/serial/by-id/usb-SEGGER_J-Link_001234567890-if02')
    reader = DataReader(port)
    reader.start()
    iq_samples = None
    make_excel = False
    excel_file = False

    if make_excel:
        results_dir = f"./results/{datetime.datetime.now().strftime('%Y_%m_%d_%H_%M_%S')}"
        os.makedirs(results_dir)

    try:
        idx = 0
        while True:
            if iq_samples is None:
                line_i = reader.queue.get()
                iq_samples = parse_report(line_i)
                if iq_samples is None:
                    continue
                print("IQ:", iq_samples)

            if make_excel:
                excel_file = os.path.join(results_dir, f"report_{idx}.xlsx")

            process_samples(iq_samples, make_excel, filename=excel_file)
            idx += 1
            iq_samples = None
    except KeyboardInterrupt:
        pass
    finally:
        reader.stop()


def update_gui():
    try:
        while True:
            distance = data_queue.get_nowait()
            label.config(text=f"{distance:.2f} m")
    except queue.Empty:
        pass

    root.after(50, update_gui)  # Triggered 20×/s


def main():
    global root, label

    root.title("Distance")
    h = root.winfo_screenheight() // 2
    w = 2 * h
    x = 50
    y = 50
    root.geometry(f"{w}x{h}+{x}+{y}")
    root.attributes("-topmost", True)
    root.after(100, lambda: root.attributes("-topmost", False))

    label_font = font.Font(family="Arial", weight="bold")
    label = tk.Label(root, text="-.-- m", font=label_font)
    label.pack(padx=50, pady=50, expand=True, fill="both")

    threading.Thread(
        target=serial_reader,
        daemon=True
    ).start()

    last_size = {"w": 0, "h": 0}

    def resize_font(event):
        if event.width == last_size["w"] and event.height == last_size["h"]:
            return

        last_size["w"] = event.width
        last_size["h"] = event.height

        size = min(event.width, event.height)
        new_size = max(10, int(size * 0.35))

        if label_font.cget("size") != new_size:
            label_font.configure(size=new_size)

    root.bind("<Configure>", resize_font)
    update_gui()
    root.mainloop()


if __name__ == "__main__":
    main()
