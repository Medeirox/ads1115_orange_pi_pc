from typing import Optional
import smbus2 as smbus
import time

# Defining ADS1115 configurations
ADS1115_CONFIG_OS_SINGLE = 0x8000  # Single conversion mode
ADS1115_CONFIG_MUX_SINGLE_0 = 0x4000  # Channel 0
ADS1115_CONFIG_MUX_SINGLE_1 = 0x5000  # Channel 1
ADS1115_CONFIG_MUX_SINGLE_2 = 0x6000  # Channel 2
ADS1115_CONFIG_MUX_SINGLE_3 = 0x7000  # Channel 3
ADS1115_CONFIG_PGA_4_096V = 0x0200  # Gain of 4.096V
# ADS1115_CONFIG_PGA_2_048V = 0x0100  # Gain of 2.048V
ADS1115_CONFIG_MODE_SINGLE = 0x0100  # Single-shot mode
ADS1115_CONFIG_DR_128SPS = 0x0080  # Data rate of 128 samples per second
ADS1115_CONFIG_CMODE_TRAD = 0x0000  # Traditional comparator mode
ADS1115_CONFIG_CPOL_ACTVLOW = 0x0000  # Active low polarity
ADS1115_CONFIG_CLATCH_NONLAT = 0x0000  # Comparator non-latching
ADS1115_CONFIG_CQUE_NONE = 0x0003  # Disables comparator

ADS1115_POINTER_CONVERT = 0x00  # Points to the conversion register
ADS1115_POINTER_CONFIG = 0x01  # Points to the configuration register


class AdsReadException(Exception):
    pass

class AdsNotFound(Exception):
    pass


class Device:
    def __init__(self, address, resolution, i2c_channel):
        self.address = address
        self.resolution = resolution
        self.i2c_channel = i2c_channel

    def _read_logical_port(self, address: int, resolution: float, i2c_channel: int = 0) -> list:
        """
        Reads the four analog channels of the ADS1115 and returns the voltage values (in volts) in a list.

        Parameters:
        - address: I2C address of the ADS1115.
        - resolution: Resolution used to calculate the measured voltage on the channels.
        Example: if the ADS1115 is configured with a gain of 4.096V, the resolution is (4.096 / 32767).
        - i2c_channel: The number of the I2C bus to be used (default is 0).

        Returns:
        - A list of the measured voltages on each channel, formatted in volts.
        """
        try:
            # Initialize the I2C bus
            bus = smbus.SMBus(i2c_channel)  # Ensure you are using the correct bus

            # Helper function to configure and read a channel
            def read_channel(mux_config):
                config = (
                    ADS1115_CONFIG_OS_SINGLE |
                    mux_config |
                    ADS1115_CONFIG_PGA_4_096V |  # Use ADS1115_CONFIG_PGA_2_048V for 2.048V gain
                    ADS1115_CONFIG_MODE_SINGLE |
                    ADS1115_CONFIG_DR_128SPS |
                    ADS1115_CONFIG_CMODE_TRAD |
                    ADS1115_CONFIG_CPOL_ACTVLOW |
                    ADS1115_CONFIG_CLATCH_NONLAT |
                    ADS1115_CONFIG_CQUE_NONE
                )

                # Send the configuration to the configuration register
                bus.write_i2c_block_data(address, ADS1115_POINTER_CONFIG, [(config >> 8) & 0xFF, config & 0xFF])

                # Wait for conversion (~100ms to ensure completion)
                time.sleep(0.1)

                # Read data from the conversion register (2 bytes)
                result = bus.read_i2c_block_data(address, ADS1115_POINTER_CONVERT, 2)

                # Convert the read value to a 16-bit number
                value = (result[0] << 8) | result[1]

                # Adjust the value to signed format (positive or negative)
                if value > 32767:
                    value -= 65536

                # Convert the value to voltage by multiplying by the resolution
                voltage = value * resolution

                # Round the voltage reading to 4 decimal places
                return voltage

            # List to store the channel voltages
            voltages = []

            # Read the four channels and store the voltages
            voltages.append(read_channel(ADS1115_CONFIG_MUX_SINGLE_0))  # Channel 0
            voltages.append(read_channel(ADS1115_CONFIG_MUX_SINGLE_1))  # Channel 1
            voltages.append(read_channel(ADS1115_CONFIG_MUX_SINGLE_2))  # Channel 2
            voltages.append(read_channel(ADS1115_CONFIG_MUX_SINGLE_3))  # Channel 3

            return voltages
        except Exception as error:
            print(f'Error reading voltage: {error}')
            return []

    def _check_if_device_exists(self, i2c_channel: int = 0, address: int = 0x48) -> bool:
        """
        Checks if the I2C device with the provided address is present on the specified I2C channel.

        Parameters:
        - i2c_channel: The number of the I2C bus to be used (default is 0).
        - address: The I2C device address (default is 0x48).

        Returns:
        - `True` if the device is found.
        - `False` if the device is not found or there is a communication error.
        """
        try:
            bus = smbus.SMBus(i2c_channel)

            bus.write_quick(address)
            # print(f"I2C device found at address 0x{address:X}.")
            return True

        except OSError:
            # print(f"I2C device not found at address 0x{address:X}.")
            return False
    
    def read(self) -> list:
        try:
            if self._check_if_device_exists(self.i2c_channel, self.address):
                return self._read_logical_port(address, resolution, i2c_channel)
            raise AdsNotFound(f"Could not find i2c device on channel 0x{i2c_channel:X} and address 0x{address:X}")
        except Exception as e:
            raise AdsReadException(e)


def search_i2c_memory(i2c_channel: int = 0) -> Optional[list]:
    try:
        bus = smbus.SMBus(i2c_channel)
        available_devices = []
        print("Searching for I2C devices...")

        for address in range(0x03, 0x78):
            try:
                bus.write_quick(address)
                available_devices.append(address)
            except OSError:
                pass

        if available_devices:
            # print(f"Devices found at addresses: {available_devices}")
            return available_devices
        else:
            # print("No I2C devices found.")
            return None
    except Exception as error:
        # print(f'Error searching for I2C devices: {error}')
        raise AdsReadException(f'Error searching for I2C devices: {error}')


if __name__ == "__main__":
    try:
        # Example usage:
        i2c_channel = 0
        devices = search_i2c_memory(i2c_channel)  # Assuming the Orange Pi uses I2C bus 0
        address = 0x48  # Default address of ADS1115
        resolution = 4.096 / 32767  # Resolution in volts per bit
        # resolution = 2.048 / 32767  # Resolution in volts per bit

        ads_sensor = Device(address, resolution, i2c_channel)
        try:
            voltages = ads_sensor.read()
        except AdsReadException as e:
            print(f"Error reading i2c device: {e}")
        except AdsNotFound as e:
            print(f"Device not found: {e}")
        print(f"Channel readings: {voltages}")

    except Exception as e:
        print(f'General error: {e}')
