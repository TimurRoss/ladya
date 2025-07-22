import pigpio
import time

# Настройка пина для PWM
ESC_PIN = 18  # GPIO18 (физический пин 12)

# Параметры PWM для ESC
PWM_FREQ = 50  # 50 Гц стандартная частота для ESC
MIN_PULSE_WIDTH = 1040  # Минимальная ширина импульса в микросекундах (обычно 1000)
MAX_PULSE_WIDTH = 1960  # Максимальная ширина импульса (обычно 2000)
STOP_PULSE_WIDTH = 0    # Нулевой сигнал (не все ESC поддерживают)

# Инициализация pigpio
pi = pigpio.pi()
if not pi.connected:
    print("Не удалось подключиться к pigpio демону!")
    exit()

def set_esc_speed(pulse_width):
    """Установка скорости ESC (ширина импульса в микросекундах)"""
    pi.set_servo_pulsewidth(ESC_PIN, pulse_width)

def initialize_esc():
    """Инициализация ESC"""
    print("Инициализация ESC...")
    set_esc_speed(0)  # Сначала убедимся, что ESC выключен
    time.sleep(1)
    
    set_esc_speed(MIN_PULSE_WIDTH)  # Минимальный сигнал
    time.sleep(1)
    print("ESC готов к работе")

def gradual_speed_increase(current_pulse,target_pulse, step=10, delay=0.1):
    """Постепенное увеличение скорости"""
    while current_pulse <= target_pulse:
        set_esc_speed(current_pulse)
        print(f"Текущая ширина импульса: {current_pulse} мкс")
        current_pulse += step
        time.sleep(delay)

try:
    initialize_esc()
    
    # # Плавное увеличение скорости до 1500 мкс (середина диапазона)
    # print("Постепенное увеличение скорости...")
    # gradual_speed_increase(MIN_PULSE_WIDTH,1500)
    
    # # Держим скорость 5 секунд
    # time.sleep(5)
    
    # # Плавное уменьшение скорости
    # print("Постепенное уменьшение скорости...")
    # gradual_speed_increase(1500,MIN_PULSE_WIDTH, step=-10)

    set_esc_speed(1500)
    time.sleep(10000)
    # Полная остановка
    set_esc_speed(0)
    print("Мотор остановлен")

except KeyboardInterrupt:
    print("Прервано пользователем")
finally:
    set_esc_speed(0)  # Убедимся, что мотор остановлен
    pi.stop()  # Закрытие соединения с pigpio
    print("Программа завершена, ресурсы освобождены")
