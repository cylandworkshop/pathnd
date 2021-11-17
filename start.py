import os
import sys
import math
import signal
import dbus
import getpass
from time import sleep, time
import RPi.GPIO as GPIO

BUTTON_GPIO = 24

MAIN_POSITION = 2
OPEN_POSITION = 3
OUTRO_POSITION = 20
VIDEO_DURATION = 3

OPEN_TIME = 10

try:
    from subprocess import DEVNULL
except ImportError:
    import os
    DEVNULL = open(os.devnull, 'wb')

OMXPLAYER = 'omxplayer'
OMXPLAYER_DBUS_ADDR='/tmp/omxplayerdbus.%s' % getpass.getuser()

#
# D-Bus player interface
#
class PlayerInterface():
    def _get_dbus_interface(self):
        try:
            bus = dbus.bus.BusConnection(
                open(OMXPLAYER_DBUS_ADDR).readlines()[0].rstrip())
            proxy = bus.get_object(
                'org.mpris.MediaPlayer2.omxplayer',
                '/org/mpris/MediaPlayer2',
                introspect=False)
            self.methods = dbus.Interface(
                proxy, 'org.mpris.MediaPlayer2.Player')
            self.properties = dbus.Interface(
                proxy, 'org.freedesktop.DBus.Properties')
            return True
        except Exception as e:
            print("WARNING: dbus connection could not be established")
            print(e)
            sleep(5)
            return False

    def initialize(self):
        sleep(10) # wait for omxplayer to appear on dbus
        return self._get_dbus_interface()

    def playPause(self):
        try:
            self.methods.Action(16)
            return True
        except:
            print(e)
            return False

    def setPosition(self, seconds):
        try:
            self.methods.SetPosition(
                dbus.ObjectPath('/not/used'),
                dbus.Int64(seconds * 1000000))
        except Exception as e:
            print(e)
            return False

        return True

    def Position(self):
        try:
            return self.properties.Get(
                'org.mpris.MediaPlayer2.Player',
                'Position')
        except Exception as e:
            return False

def setInterval(interval):
    def decorator(function):
        def wrapper(*args, **kwargs):
            stopped = threading.Event()

            def loop(): # executed in another thread
                while not stopped.wait(interval): # until stopped
                    function(*args, **kwargs)

            t = threading.Thread(target=loop)
            t.daemon = True # stop if the program exits
            t.start()
            return stopped
        return wrapper
    return decorator

@setInterval(.5)
def function():
    print("time event")

led_state = True
@setInterval(.25)
def handle_led():
    global led_state
    GPIO.output(LED_GPIO, 1 if led_state else 0)
    led_state = not led_state

led_timer = None
def start_led():
    global led_timer
    if led_timer is not None:
        led_timer = handle_led()

def stop_led():
    global led_timer
    if led_timer is not None:
        led_timer.set()
        led_timer = None
    GPIO.output(LED_GPIO, 0)

@setInterval(MAIN_POSITION)
def handle_intro_loop():
    controller.setPosition(0)

intro_loop_timer = None
def start_intro_loop():
    global intro_loop_timer
    if intro_loop_timer is not None:
        controller.setPosition(0)
        intro_loop_timer = handle_intro_loop()

def stop_intro_loop_go_main():
    global intro_loop_timer
    if intro_loop_timer is not None:
        intro_loop_timer.set()
        intro_loop_timer = None
    controller.setPosition(MAIN_POSITION)


@setInterval(VIDEO_DURATION - OUTRO_POSITION)
def handle_outro_loop():
    controller.setPosition(OUTRO_POSITION)

outro_loop_timer = None
def start_outro_loop():
    global outro_loop_timer
    if outro_loop_timer is not None:
        controller.setPosition(OUTRO_POSITION)
        outro_loop_timer = handle_outro_loop()
    
def stop_outro_loop():
    global outro_loop_timer
    if outro_loop_timer is not None:
        outro_loop_timer.set()
        outro_loop_timer = None

controller = PlayerInterface()
process = Popen([OMXPLAYER, "/data/pathd.mov"], preexec_fn=os.setsid, stdout=DEVNULL, stderr=DEVNULL, stdin=DEVNULL)
self.controller.initialize()

start_event = threading.Event()
def handle_button(channel):
    print("button pressed")
    start_event.set()

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_GPIO, GPIO.IN, pull_up_down=GPIO.PUD_OFF)
GPIO.add_event_detect(BUTTON_GPIO, GPIO.RISING, callback=handle_button, bouncetime=100)

print("start PATHND")
while True:
    print("wait for events")
    start_led() # blink led
    start_intro_loop() # show intro
    start_event.wait() # wait for pressing button
    
    print("start main sequence")
    stop_led()
    stop_intro_loop_go_main()
    sleep(OPEN_POSITION - MAIN_POSITION)
    
    print("open the case")
    GPIO.output(RELAY_GPIO, 1) # open the case
    sleep(OUTRO_POSITION - OPEN_POSITION)

    print("outro")
    start_outro_loop()
    sleep(OPEN_TIME)
    
    print("close the case")
    GPIO.output(RELAY_GPIO, 0) # close the case
    sleep(CLOSING_TIME)

    print("end of cycle")
    stop_outro_loop()
    start_event.clear()

