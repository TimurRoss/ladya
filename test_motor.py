import pigpio
import time

ESC_GPIO = 18  # Используйте GPIO, поддерживающий аппаратный ШИМ (например, 12, 13, 18, 19)

pi = pigpio.pi()
if not pi.connected:
    exit()

# Минимальный и максимальный импульс для большинства ESC (в микросекундах)
ESC_MIN = 1000  # Минимальная скорость (обычно 1 мс)
ESC_MAX = 2000  # Максимальная скорость (обычно 2 мс)

def set_speed(pulsewidth):
    # pulsewidth в микросекундах (1000-2000)
    pi.set_servo_pulsewidth(ESC_GPIO, pulsewidth)

try:
    print("Arming ESC...")
    # set_speed(ESC_MAX)
    # time.sleep(2)
    set_speed(ESC_MIN)
    time.sleep(2)
    set_speed((ESC_MIN+ESC_MAX)/2)
    time.sleep(2)
    print("ESC Armed. Increasing speed...")

    # Постепенно увеличиваем скорость
    for pw in range(ESC_MIN, ESC_MAX+1, 50):
        set_speed(pw)
        print(f"Pulsewidth: {pw}")
        time.sleep(0.5)

    print("Setting to minimum speed...")
    set_speed(ESC_MIN)
    time.sleep(2)

finally:
    print("Stopping ESC...")
    set_speed(0)
    pi.stop()