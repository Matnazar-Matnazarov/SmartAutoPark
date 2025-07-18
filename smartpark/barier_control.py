import serial
import time

def control_barrier_time(delay_seconds=10):
    """
    Shlakboumni ochadi va N soniyadan keyin avtomatik yopadi.
    """
    try:
        port = '/dev/ttyUSB0'  # Ehtiyot bo‘ling: o‘zingizga mos portni belgilang
        baudrate = 9600

        with serial.Serial(port, baudrate, timeout=1) as ser:
            time.sleep(2)  # Port ochilgandan keyin barqarorlashish

            # Ochish buyrug‘i
            ser.write(b'O')  # Bu sizning qurilmangizga bog‘liq (masalan b'\xA0\x01\x01\xA2')
            print("✅ Barrier OPEN command sent")

            # Kutish
            time.sleep(delay_seconds)

            # Yopish buyrug‘i
            ser.write(b'C')
            print("✅ Barrier CLOSE command sent")

    except serial.SerialException as e:
        print(f"❌ Serial port error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")



def control_barrier_command(action='open'):
    """
    Shlakbaumni boshqarish: 'open' yoki 'close'
    Qurilmaga serial orqali signal yuboradi.
    """
    try:
        # USB portga ulanganda chiqadigan nom (Linuxda /dev/ttyUSB0, Windowsda COM3 bo'lishi mumkin)
        port = '/dev/ttyUSB0'   # EHTIYOT BO‘LING: sizda boshqa bo‘lishi mumkin, `ls /dev/ttyUSB*` bilan tekshiring
        baudrate = 9600         # Modulga mos ravishda sozlang (odatda 9600)

        # Serial port ochiladi
        with serial.Serial(port, baudrate, timeout=1) as ser:
            time.sleep(2)  # Port ochilgandan keyin kutish

            if action == 'open':
                command = b'O'  # O = Open (sizning modulga bog‘liq, ba'zida b'\xA0\x01\x01\xA2' bo'lishi mumkin)
            elif action == 'close':
                command = b'C'  # C = Close
            else:
                raise ValueError("Action must be 'open' or 'close'")

            ser.write(command)
            print(f"✅ Barrier command sent: {action}")

    except serial.SerialException as e:
        print(f"❌ Serial port error: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
