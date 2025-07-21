# Установка программного обеспечения

Для Raspberry Pi 5 мы будем использовать библиотеку lgpio. Она обычно предустановлена в последних версиях Raspberry Pi OS, но на всякий случай установите её явно.

``` Bash
# Убедимся, что списки пакетов свежие (вы это уже делали)
sudo apt update

# Устанавливаем pigpio и ее Python-модуль
sudo apt install pigpio python3-pigpio
```

# Как запустить:
```
    sudo pigpiod
    python3 rpi_dshot_pigpio.py (sudo здесь не нужно, т.к. демон уже запущен с правами root).
```