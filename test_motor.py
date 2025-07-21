import lgpio
import time
import sys

# --- Функция для расчета DShot кадра (оптимизированная) ---
def convert_throttle_to_dshot(throttle: float, telemetry: bool = False) -> int:
    """Преобразует значение газа (0.0-1.0) в 16-битный DShot кадр."""
    throttle = max(0.0, min(1.0, throttle))
    # Значения от 1 до 47 зарезервированы для команд, газ начинается с 48
    dshot_throttle = round(throttle * 1999) + 48 if throttle > 0.0 else 0
    
    # Пакет: 11 бит газа, 1 бит телеметрии
    packet = (dshot_throttle << 1) | int(telemetry)
    
    # CRC-чексумма: XOR по 4-битным частям пакета
    crc = (packet ^ (packet >> 4) ^ (packet >> 8)) & 0x0F
    
    # Финальный кадр: [12-битный пакет][4-битная CRC]
    return (packet << 4) | crc


class DShotMotor:
    """
    Класс для управления мотором по протоколу DShot на Raspberry Pi 5
    с использованием библиотеки lgpio.
    """
    # Тайминги для разных скоростей DShot в микросекундах (µs).
    # lgpio работает с целыми числами µs, поэтому DShot300 - самый надежный вариант.
    # DShot600 требует наносекундной точности, которую мы аппроксимируем.
    TIMINGS = {
        600: {'T0H': 1, 'T1H': 2, 'T_PERIOD': 3},  # Аппроксимация DShot600 (похоже на DShot300/333)
        300: {'T0H': 1, 'T1H': 2, 'T_PERIOD': 3},  # Надежные тайминги для DShot300
        150: {'T0H': 2, 'T1H': 4, 'T_PERIOD': 6},  # Надежные тайминги для DShot150
    }

    def __init__(self, chip_handle, gpio_pin: int, speed: int = 300):
        if speed not in self.TIMINGS:
            raise ValueError(f"Скорость {speed} не поддерживается. Доступные: {list(self.TIMINGS.keys())}")
        
        self.h = chip_handle
        self.pin = gpio_pin
        self.timings = self.TIMINGS[speed]
        
        # Заявляем права на эксклюзивное использование GPIO
        lgpio.gpio_claim_output(self.h, self.pin)
        print(f"Мотор на GPIO {self.pin} инициализирован для DShot{speed}.")
        
    def _create_waveform(self, dshot_frame: int) -> list:
        """Создает волновую форму lgpio для одного 16-битного DShot кадра."""
        pulses = []
        on_mask = 1 << self.pin
        off_mask = 1 << self.pin

        for i in range(16):
            # Проверяем бит от старшего к младшему
            is_one_bit = (dshot_frame >> (15 - i)) & 1
            
            if is_one_bit:
                # Бит '1': Длинный высокий импульс, короткий низкий
                pulses.append(lgpio.pulse(on_mask, 0, self.timings['T1H']))
                pulses.append(lgpio.pulse(0, off_mask, self.timings['T_PERIOD'] - self.timings['T1H']))
            else:
                # Бит '0': Короткий высокий импульс, длинный низкий
                pulses.append(lgpio.pulse(on_mask, 0, self.timings['T0H']))
                pulses.append(lgpio.pulse(0, off_mask, self.timings['T_PERIOD'] - self.timings['T0H']))
        
        # Пауза между кадрами для стабильности
        pulses.append(lgpio.pulse(0, off_mask, 50))
        return pulses

    def send_throttle(self, throttle: float, telemetry: bool = False):
        """Отправляет одну команду газа на мотор."""
        if not (0.0 <= throttle <= 1.0):
            throttle = max(0.0, min(1.0, throttle)) # Ограничиваем значение для безопасности
            
        dshot_frame = convert_throttle_to_dshot(throttle, telemetry)
        waveform = self._create_waveform(dshot_frame)
        
        lgpio.tx_wave(self.h, self.pin, waveform)
        
        # Важно дождаться окончания передачи перед отправкой следующей волны
        while lgpio.tx_busy(self.h, self.pin, lgpio.TX_WAVE):
            time.sleep(0.001)
            
        return dshot_frame

    def arm(self):
        """Активирует (арминг) ESC путем отправки нулевого газа в течение 2 секунд."""
        print("\n--- ПРОЦЕДУРА АРМИНГА ---")
        print("Убедитесь, что на мотор подано питание. Вы должны услышать стартовые сигналы ESC.")
        input("Нажмите Enter для начала арминга...")
        
        print("Арминг... Отправка нулевого газа в течение 2 секунд.")
        start_time = time.time()
        while time.time() - start_time < 2.0:
            self.send_throttle(0.0)
            time.sleep(0.01) # Отправляем команду с частотой ~100 Гц
            
        print("Арминг завершен. Мотор готов к работе. Вы должны были услышать финальный сигнал.")

    def close(self):
        """Безопасно останавливает мотор и освобождает ресурсы GPIO."""
        print("\nОстановка мотора и очистка ресурсов...")
        # Гарантированно отправляем команду остановки
        for _ in range(10):
            self.send_throttle(0.0)
            time.sleep(0.01)
        
        # Устанавливаем пин в безопасное состояние (низкий уровень) и освобождаем
        lgpio.gpio_write(self.h, self.pin, 0)
        lgpio.gpio_claim_input(self.h, self.pin)
        print(f"GPIO {self.pin} освобожден.")


# --- Основной блок исполнения ---
if __name__ == "__main__":
    # --- НАСТРОЙКИ ---
    MOTOR_GPIO = 18    # GPIO пин, к которому подключен сигнал ESC
    GPIO_CHIP = 0      # Для Raspberry Pi 5 используем чип 0
    DSHOT_SPEED = 300  # Рекомендуется 300 или 150 для максимальной надежности
    
    h = None
    motor = None

    try:
        print("*"*50)
        print("      DShot Motor Control for Raspberry Pi 5")
        print("*"*50)
        print(f"Используется библиотека lgpio, GPIO={MOTOR_GPIO}, DShot{DSHOT_SPEED}")
        
        # --- ВНИМАНИЕ: СНИМИТЕ ПРОПЕЛЛЕРЫ! ---
        if input("!!! ВНИМАНИЕ !!! Пропеллеры СНЯТЫ? (да/нет): ").lower() != 'да':
            print("Безопасность прежде всего! Завершение программы.")
            sys.exit()

        # Инициализация lgpio
        h = lgpio.gpiochip_open(GPIO_CHIP)
        motor = DShotMotor(h, MOTOR_GPIO, speed=DSHOT_SPEED)

        # Процедура арминга
        motor.arm()

        # Интерактивный режим управления
        print("\n--- РЕЖИМ РУЧНОГО УПРАВЛЕНИЯ ---")
        print("Введите значение газа от 0.0 до 1.0 (например, 0.1 для 10%).")
        print("Введите 'выход' или 'exit' для завершения.")
        
        while True:
            try:
                user_input = input("Газ > ").strip().lower()
                if user_input in ['выход', 'exit', 'quit', 'q']:
                    break
                
                throttle_value = float(user_input)
                if not (0.0 <= throttle_value <= 1.0):
                    print("Ошибка: значение должно быть между 0.0 и 1.0.")
                    continue
                
                dshot_val = motor.send_throttle(throttle_value)
                print(f"  Установлен газ: {throttle_value:.2f} -> DShot кадр: {dshot_val} (0b{dshot_val:016b})")

            except ValueError:
                print("Ошибка: введите корректное число (например, 0.05).")
            except lgpio.error as e:
                print(f"Ошибка lgpio: {e}")
                break

    except KeyboardInterrupt:
        print("\nОбнаружено прерывание (Ctrl+C).")
    except Exception as e:
        print(f"\nПроизошла критическая ошибка: {e}")
    finally:
        if motor:
            motor.close()
        if h:
            lgpio.gpiochip_close(h)
        print("Программа безопасно завершена.")