import pigpio
import time

PI_GPIO = 18

pi = pigpio.pi()
if not pi.connected:
    print("Не удалось подключиться к демону pigpio. Запустите 'sudo pigpiod'")
    exit()

print(f"Мигаем GPIO {PI_GPIO}. Нажмите Ctrl+C для выхода.")
try:
    while True:
        pi.write(PI_GPIO, 1) # Включить (3.3V)
        time.sleep(0.01)
        pi.write(PI_GPIO, 0) # Выключить (0V)
        time.sleep(0.01)
except KeyboardInterrupt:
    print("\nЗавершение.")
    pi.write(PI_GPIO, 0) # Выключаем пин перед выходом
    pi.stop()