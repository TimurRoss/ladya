import pigpio
import time
import sys

# Функция convert_throttle_to_dshot остается без изменений
def convert_throttle_to_dshot(throttle: float, telemetry: bool = False) -> int:
    throttle = max(0.0, min(1.0, throttle))
    dshot_throttle = round(throttle * 1999) + 48 if throttle > 0.0 else 0
    packet = (dshot_throttle << 1) | int(telemetry)
    crc = (packet ^ (packet >> 4) ^ (packet >> 8)) & 0x0F
    return (packet << 4) | crc

class DShotMotor_pigpio:
    TIMINGS = {
        300: {'T0H': 1, 'T1H': 2, 'T_PERIOD': 3},
        150: {'T0H': 2, 'T1H': 4, 'T_PERIOD': 6},
    }

    def __init__(self, pi_connection, gpio_pin: int, speed: int = 300):
        if speed not in self.TIMINGS:
            raise ValueError(f"Speed {speed} not supported.")
        
        self.pi = pi_connection
        self.pin = gpio_pin
        self.timings = self.TIMINGS[speed]
        
        # Устанавливаем пин как выход
        self.pi.set_mode(self.pin, pigpio.OUTPUT)
        print(f"Motor on GPIO {self.pin} initialized for DShot{speed}.")

    def _create_waveform(self, dshot_frame: int) -> list:
        pulses = []
        for i in range(16):
            is_one_bit = (dshot_frame >> (15 - i)) & 1
            
            if is_one_bit:
                high_time = self.timings['T1H']
                low_time = self.timings['T_PERIOD'] - high_time
            else:
                high_time = self.timings['T0H']
                low_time = self.timings['T_PERIOD'] - high_time
            
            pulses.append(pigpio.pulse(1 << self.pin, 0, high_time))
            pulses.append(pigpio.pulse(0, 1 << self.pin, low_time))
        
        pulses.append(pigpio.pulse(0, 0, 50)) # Пауза
        return pulses

    def send_throttle(self, throttle: float):
        dshot_frame = convert_throttle_to_dshot(throttle)
        waveform = self._create_waveform(dshot_frame)
        
        self.pi.wave_add_generic(waveform)
        wave_id = self.pi.wave_create()
        
        if wave_id >= 0:
            self.pi.wave_send_once(wave_id)
            while self.pi.wave_tx_busy():
                time.sleep(0.001)
            self.pi.wave_delete(wave_id)
        else:
            print(f"Error creating wave: {wave_id}")

    def close(self):
        print("\nStopping motor and cleaning up...")
        for _ in range(10):
            self.send_throttle(0.0)
            time.sleep(0.01)
        self.pi.set_mode(self.pin, pigpio.INPUT) # Безопасное состояние
        # Соединение с демоном не закрываем, его останавливают отдельно

if __name__ == "__main__":
    MOTOR_GPIO = 18
    DSHOT_SPEED = 300
    
    pi = None
    motor = None

    try:
        # Подключаемся к демону pigpio
        pi = pigpio.pi()
        if not pi.connected:
            print("Could not connect to pigpio daemon. Is it running? (sudo pigpiod)")
            sys.exit()

        if input("!!! ВНИМАНИЕ !!! Пропеллеры СНЯТЫ? (да/нет): ").lower() != 'да':
            sys.exit()
            
        motor = DShotMotor_pigpio(pi, MOTOR_GPIO, speed=DSHOT_SPEED)
        # Арминг... (логика та же)
        print("Arming motor... Press Enter to start.")
        input()
        start_time = time.time()
        while time.time() - start_time < 2.0:
            motor.send_throttle(0.0)
            time.sleep(0.01)
        print("Arming complete.")

        print("\nEnter throttle value (0.0 to 1.0) or 'exit'.")
        while True:
            user_input = input("Throttle > ").strip().lower()
            if user_input in ['exit', 'quit', 'q']:
                break
            throttle_value = float(user_input)
            motor.send_throttle(throttle_value)
            print(f"  Sent throttle: {throttle_value:.2f}")

    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        if motor:
            motor.close()
        if pi:
            pi.stop() # Отключаемся от демона
        print("Program safely terminated.")