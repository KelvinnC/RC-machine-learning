#!/usr/bin/env python3
import time
import threading
import cv2
from queue import Queue, Empty
from pca import set_pwm_freq, set_pwm
from evdev import InputDevice, list_devices, ecodes
from loggerexperiment import DataLogger

STEER_CH, THROTTLE_CH = 1, 0
STEER_MIN, STEER_MAX = 150, 600
THROTTLE_REV, THROTTLE_STOP, THROTTLE_MAX = 205, 307, 410
def map_range(x, a, b, c, d):
    return int((x - a)/(b - a)*(d - c)+c)

latest_frame = None
frame_lock   = threading.Lock()

def capture_thread(cam_index, width, height, stop_event):
    global latest_frame
    cap = cv2.VideoCapture(cam_index)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH,  width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    while not stop_event.is_set():
        ret, frame = cap.read()
        if ret:
            with frame_lock:
                latest_frame = frame.copy()
    cap.release()

def stream_thread(stop_event):
    cv2.namedWindow('Stream', cv2.WINDOW_NORMAL)
    while not stop_event.is_set():
        with frame_lock:
            frame = None if latest_frame is None else latest_frame.copy()
        if frame is not None:
            cv2.imshow('Stream', frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            stop_event.set()
            break
    cv2.destroyAllWindows()

def logger_worker(log_queue: Queue, logger: DataLogger):
    while True:
        steer, thr = log_queue.get()
        if steer is None and thr is None:
            break
        with frame_lock:
            frame = None if latest_frame is None else latest_frame.copy()
        if frame is not None:
            logger.capture_frame(frame, steer, thr)

def main():
    set_pwm_freq(50)

    stop_cap = threading.Event()
    cap_t = threading.Thread(target=capture_thread,
                             args=("/dev/video0", 1280, 720, stop_cap),
                             daemon=True)
    cap_t.start()

    stop_stream = threading.Event()
    str_t = threading.Thread(target=stream_thread,
                             args=(stop_stream,),
                             daemon=True)
    str_t.start()

    log_q = Queue(maxsize=256)
    logger = DataLogger()
    log_t = threading.Thread(target=logger_worker,
                             args=(log_q, logger),
                             daemon=True)
    log_t.start()

    devices = [InputDevice(fn) for fn in list_devices()]
    ctrl = next((d for d in devices if d.name=='Wireless Controller'), None)
    if not ctrl:
        print("No controller found.")
        stop_cap.set(); stop_stream.set()
        return

    cur_steer = (STEER_MIN+STEER_MAX)//2
    cur_th    = THROTTLE_STOP
    recording = False
    prev_r2   = 0
    TRIM = 0
    SQUARE_BTN = ecodes.BTN_WEST
    CIRCLE_BTN = ecodes.BTN_EAST
    R2_THR = 10

    try:
        for ev in ctrl.read_loop():
            if ev.type == ecodes.EV_KEY and ev.value == 1:
                if ev.code == SQUARE_BTN:
                    TRIM = max(
                        TRIM - 10,
                        STEER_MIN - (STEER_MIN + STEER_MAX)//2
                    )
                    print(f"[TRIM] steering_trim={TRIM} (left)")
                elif ev.code == CIRCLE_BTN:
                    TRIM = min(
                        TRIM + 10,
                        STEER_MAX - (STEER_MIN + STEER_MAX)//2
                    )
                    print(f"[TRIM] steering_trim={TRIM} (right)")
                continue

            if ev.type!=ecodes.EV_ABS:
                continue

            name = ecodes.bytype[ecodes.EV_ABS][ev.code]
            val  = ev.value

            if name=='ABS_RZ':
                if val>R2_THR and prev_r2<=R2_THR:
                    recording = not recording
                    print(f"[INFO] Recording {'ON' if recording else 'OFF'}")
                    if not recording:
                        flushed=0
                        while True:
                            try: log_q.get_nowait(); flushed+=1
                            except Empty: break
                        print(f"[INFO] Flushed {flushed}")
                prev_r2 = val
                continue

            if name=='ABS_X':
                raw = map_range(val,0,255,STEER_MIN,STEER_MAX)
                cur_steer = max(STEER_MIN, min(STEER_MAX, raw+TRIM))
                set_pwm(STEER_CH,0,cur_steer)

            elif name=='ABS_RY':
                off = 128-val
                if abs(off)<10: cur_th=THROTTLE_STOP
                elif off>0:     cur_th = map_range(off,0,128,THROTTLE_STOP,THROTTLE_MAX)
                else:           cur_th = map_range(-off,0,128,THROTTLE_STOP,THROTTLE_REV)

                set_pwm(THROTTLE_CH,0,cur_th)
                print(f"[DBG] steer={cur_steer} thr={cur_th}")
                if recording:
                    try: log_q.put_nowait((cur_steer,cur_th))
                    except: pass

    except KeyboardInterrupt:
        pass
    finally:
        stop_cap.set()
        stop_stream.set()
        log_q.put((None,None))
        cap_t.join()
        str_t.join()
        log_t.join()

if __name__=="__main__":
    main()
