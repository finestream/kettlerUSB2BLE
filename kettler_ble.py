"""
KettlerBLE - Bluetooth Low Energy GATT Server
Uses bluezero library for proper D-Bus GATT registration with PUSH notifications
Implements FTMS (Fitness Machine Service) and Cycling Power Service
"""

import logging
import struct
from typing import Optional, Callable
from bluezero import peripheral, adapter

logger = logging.getLogger(__name__)


class KettlerBLE:
    """
    BLE GATT Server for Kettler bike trainer
    Exposes FTMS and Cycling Power services with push notifications
    """
    
    # Service UUIDs (short form)
    FTMS_SERVICE_UUID = '1826'
    CYCLING_POWER_SERVICE_UUID = '1818'
    
    # FTMS Characteristic UUIDs (short form)
    INDOOR_BIKE_DATA_UUID = '2AD2'
    FITNESS_MACHINE_STATUS_UUID = '2ADA'
    FITNESS_CONTROL_POINT_UUID = '2AD9'
    FITNESS_MACHINE_FEATURE_UUID = '2ACC'
    SUPPORTED_POWER_RANGE_UUID = '2AD8'
    
    # Cycling Power Characteristic UUIDs (short form)
    CYCLING_POWER_MEASUREMENT_UUID = '2A63'
    CYCLING_POWER_FEATURE_UUID = '2A65'
    SENSOR_LOCATION_UUID = '2A5D'
    
    def __init__(self, control_callback: Optional[Callable] = None):
        """
        Initialize BLE GATT server
        
        Args:
            control_callback: Callback function for control point commands
        """
        self.name = "KettlerBLE"
        self.control_callback = control_callback
        self.under_control = False
        
        # Current data values
        self.indoor_bike_data = bytearray(10)
        self.cycling_power_data = bytearray(8)
        self.machine_status = bytearray([0x04])
        self.crank_revolutions = 0
        
        # Get adapter address
        self.adapter_address = adapter.Adapter().address
        
        # Peripheral
        self.peripheral = None
        
        # Characteristic references for pushing notifications
        self.indoor_bike_char = None
        self.cycling_power_char = None
        self.machine_status_char = None
        self.control_point_char = None
        
        logger.info(f'[{self.name}] Initializing on adapter {self.adapter_address}')
        
    def start(self, status_callback=None):
        """Start the BLE GATT server"""
        try:
            logger.info(f'[{self.name}] Starting BLE peripheral...')
            
            # Create peripheral
            self.peripheral = peripheral.Peripheral(
                self.adapter_address,
                local_name=self.name
            )
            
            # Add FTMS Service
            self._add_ftms_service()
            
            # Add Cycling Power Service
            self._add_cycling_power_service()
            
            logger.info(f'[{self.name}] ✓ BLE server started and advertising as "{self.name}"')
            logger.info(f'[{self.name}] Services exposed:')
            logger.info(f'[{self.name}]   • Fitness Machine (FTMS) - 1826')
            logger.info(f'[{self.name}]   • Cycling Power - 1818')
            
            # Notify callback that we're ready before blocking
            if status_callback:
                status_callback(True, None)
            
            # Start advertising (this blocks!)
            self.peripheral.publish()
            
        except Exception as e:
            logger.error(f'[{self.name}] ✗ Failed to start: {e}')
            if status_callback:
                status_callback(False, str(e))
            raise
            
    def _add_ftms_service(self):
        """Add Fitness Machine Service (FTMS) to peripheral"""
        self.peripheral.add_service(srv_id=1, uuid=self.FTMS_SERVICE_UUID, primary=True)
        
        # Indoor Bike Data (Notify)
        self.peripheral.add_characteristic(
            srv_id=1,
            chr_id=1,
            uuid=self.INDOOR_BIKE_DATA_UUID,
            value=list(self.indoor_bike_data),
            notifying=False,
            flags=['notify', 'read'],
            read_callback=lambda: list(self.indoor_bike_data),
            notify_callback=self._indoor_bike_notify_callback
        )
        
        # Fitness Machine Status (Notify)
        self.peripheral.add_characteristic(
            srv_id=1,
            chr_id=2,
            uuid=self.FITNESS_MACHINE_STATUS_UUID,
            value=list(self.machine_status),
            notifying=False,
            flags=['notify', 'read'],
            read_callback=lambda: list(self.machine_status),
            notify_callback=self._machine_status_notify_callback
        )
        
        # Fitness Control Point (Write, Indicate)
        self.peripheral.add_characteristic(
            srv_id=1,
            chr_id=3,
            uuid=self.FITNESS_CONTROL_POINT_UUID,
            value=[],
            notifying=False,
            flags=['write', 'indicate'],
            write_callback=self._handle_control_point_write,
            indicate_callback=self._control_point_indicate_callback
        )
        
        # Fitness Machine Feature (Read)
        self.peripheral.add_characteristic(
            srv_id=1,
            chr_id=4,
            uuid=self.FITNESS_MACHINE_FEATURE_UUID,
            value=[0x02, 0x44, 0x00, 0x00, 0x08, 0x20, 0x00, 0x00],
            notifying=False,
            flags=['read']
        )
        
        # Supported Power Range (Read)
        self.peripheral.add_characteristic(
            srv_id=1,
            chr_id=5,
            uuid=self.SUPPORTED_POWER_RANGE_UUID,
            value=[0x32, 0x00, 0x58, 0x02, 0x05, 0x00],
            notifying=False,
            flags=['read']
        )
        
        logger.info(f'[{self.name}] Added FTMS service with 5 characteristics')
        
    def _add_cycling_power_service(self):
        """Add Cycling Power Service to peripheral"""
        self.peripheral.add_service(srv_id=2, uuid=self.CYCLING_POWER_SERVICE_UUID, primary=True)
        
        # Cycling Power Measurement (Notify)
        self.peripheral.add_characteristic(
            srv_id=2,
            chr_id=1,
            uuid=self.CYCLING_POWER_MEASUREMENT_UUID,
            value=list(self.cycling_power_data),
            notifying=False,
            flags=['notify', 'read'],
            read_callback=lambda: list(self.cycling_power_data),
            notify_callback=self._cycling_power_notify_callback
        )
        
        # Cycling Power Feature (Read)
        self.peripheral.add_characteristic(
            srv_id=2,
            chr_id=2,
            uuid=self.CYCLING_POWER_FEATURE_UUID,
            value=[0x08, 0x00, 0x00, 0x00],
            notifying=False,
            flags=['read']
        )
        
        # Sensor Location (Read)
        self.peripheral.add_characteristic(
            srv_id=2,
            chr_id=3,
            uuid=self.SENSOR_LOCATION_UUID,
            value=[13],
            notifying=False,
            flags=['read']
        )
        
        logger.info(f'[{self.name}] Added Cycling Power service with 3 characteristics')
    
    def _indoor_bike_notify_callback(self, notifying, characteristic):
        """Called when client subscribes/unsubscribes to Indoor Bike Data"""
        if notifying:
            logger.info(f'[{self.name}] Indoor Bike Data notifications ENABLED')
            self.indoor_bike_char = characteristic
        else:
            logger.info(f'[{self.name}] Indoor Bike Data notifications DISABLED')
            self.indoor_bike_char = None
    
    def _cycling_power_notify_callback(self, notifying, characteristic):
        """Called when client subscribes/unsubscribes to Cycling Power"""
        if notifying:
            logger.info(f'[{self.name}] Cycling Power notifications ENABLED')
            self.cycling_power_char = characteristic
        else:
            logger.info(f'[{self.name}] Cycling Power notifications DISABLED')
            self.cycling_power_char = None
    
    def _machine_status_notify_callback(self, notifying, characteristic):
        """Called when client subscribes/unsubscribes to Machine Status"""
        if notifying:
            logger.info(f'[{self.name}] Machine Status notifications ENABLED')
            self.machine_status_char = characteristic
        else:
            logger.info(f'[{self.name}] Machine Status notifications DISABLED')
            self.machine_status_char = None
    
    def _control_point_indicate_callback(self, indicating, characteristic):
        """Called when client subscribes/unsubscribes to Control Point indications"""
        if indicating:
            logger.info(f'[{self.name}] Control Point indications ENABLED')
            self.control_point_char = characteristic
        else:
            logger.info(f'[{self.name}] Control Point indications DISABLED')
            self.control_point_char = None
    
    def _send_control_point_response(self, opcode: int, result_code: int):
        """Send response indication to control point (0x80 response)"""
        if self.control_point_char and self.control_point_char.is_notifying:
            response = [0x80, opcode, result_code]
            self.control_point_char.set_value(response)
            logger.debug(f'[{self.name}] → Sent control response: opcode=0x{opcode:02X}, result=0x{result_code:02X}')
        else:
            logger.warning(f'[{self.name}] Cannot send control response - no indication subscription')
        
    def _handle_control_point_write(self, value: bytes):
        """Handle writes to Fitness Control Point characteristic"""
        if not value or len(value) == 0:
            return
            
        opcode = value[0]
        logger.info(f'[{self.name}] Control Point opcode: 0x{opcode:02X}')
        
        # Result codes (FTMS spec)
        RESULT_SUCCESS = 0x01
        RESULT_OP_CODE_NOT_SUPPORTED = 0x02
        RESULT_INVALID_PARAMETER = 0x03
        RESULT_OPERATION_FAILED = 0x04
        RESULT_CONTROL_NOT_PERMITTED = 0x05
        
        try:
            if opcode == 0x00:  # Request Control
                logger.info(f'[{self.name}] → Request Control')
                if not self.under_control:
                    if self.control_callback and self.control_callback('control'):
                        self.under_control = True
                        logger.info(f'[{self.name}] ✓ Control granted')
                        self._send_control_point_response(opcode, RESULT_SUCCESS)
                    else:
                        logger.warning(f'[{self.name}] ✗ Control request failed')
                        self._send_control_point_response(opcode, RESULT_OPERATION_FAILED)
                else:
                    logger.info(f'[{self.name}] Already under control')
                    self._send_control_point_response(opcode, RESULT_SUCCESS)
                    
            elif opcode == 0x01:  # Reset
                logger.info(f'[{self.name}] → Reset')
                if self.under_control:
                    if self.control_callback:
                        self.control_callback('reset')
                    self.under_control = False
                    self._send_control_point_response(opcode, RESULT_SUCCESS)
                else:
                    logger.warning(f'[{self.name}] Reset without control')
                    self._send_control_point_response(opcode, RESULT_CONTROL_NOT_PERMITTED)
                
            elif opcode == 0x05:  # Set Target Power (ERG mode)
                logger.info(f'[{self.name}] → Set Target Power')
                if self.under_control:
                    if len(value) >= 3:
                        power = struct.unpack('<H', value[1:3])[0]
                        logger.info(f'[{self.name}]   Power: {power}W')
                        if self.control_callback and self.control_callback('power', power):
                            self._send_control_point_response(opcode, RESULT_SUCCESS)
                        else:
                            self._send_control_point_response(opcode, RESULT_OPERATION_FAILED)
                    else:
                        logger.warning(f'[{self.name}] Invalid power command length')
                        self._send_control_point_response(opcode, RESULT_INVALID_PARAMETER)
                else:
                    logger.warning(f'[{self.name}] Set power without control')
                    self._send_control_point_response(opcode, RESULT_CONTROL_NOT_PERMITTED)
                    
            elif opcode == 0x07:  # Start/Resume
                logger.info(f'[{self.name}] → Start/Resume')
                if self.control_callback:
                    self.control_callback('start')
                self._send_control_point_response(opcode, RESULT_SUCCESS)
                
            elif opcode == 0x08:  # Stop/Pause
                logger.info(f'[{self.name}] → Stop/Pause')
                if self.control_callback:
                    self.control_callback('stop')
                self._send_control_point_response(opcode, RESULT_SUCCESS)
                
            elif opcode == 0x11:  # Set Indoor Bike Simulation Parameters (SIM mode)
                logger.info(f'[{self.name}] → Simulation Parameters')
                if len(value) >= 7:
                    windspeed = struct.unpack('<h', value[1:3])[0] * 0.001
                    grade = struct.unpack('<h', value[3:5])[0] * 0.01
                    crr = value[5] * 0.0001 if len(value) > 5 else 0.005
                    cw = value[6] * 0.01 if len(value) > 6 else 0.39
                    
                    logger.info(f'[{self.name}]   Wind: {windspeed:.2f}m/s, Grade: {grade:.1f}%')
                    if self.control_callback and self.control_callback('simulation', windspeed, grade, crr, cw):
                        self._send_control_point_response(opcode, RESULT_SUCCESS)
                    else:
                        self._send_control_point_response(opcode, RESULT_OPERATION_FAILED)
                else:
                    logger.warning(f'[{self.name}] Invalid simulation command length')
                    self._send_control_point_response(opcode, RESULT_INVALID_PARAMETER)
                    
            else:
                logger.warning(f'[{self.name}] Unknown opcode: 0x{opcode:02X}')
                self._send_control_point_response(opcode, RESULT_OP_CODE_NOT_SUPPORTED)
                
        except Exception as e:
            logger.error(f'[{self.name}] Error handling control point: {e}')
            
    def notify_ftms(self, data: dict):
        """Update and notify FTMS data"""
        if not data:
            return
            
        if 'speed' in data or 'rpm' in data or 'power' in data:
            self._update_indoor_bike_data(data)
            
        if 'power' in data:
            self._update_cycling_power(data)
            
    def _update_indoor_bike_data(self, data: dict):
        """Update Indoor Bike Data characteristic and PUSH notification"""
        try:
            buffer = bytearray(10)
            index = 0
            
            # Flags (uint16) - 0x0244 = speed + cadence + power
            buffer[index] = 0x44
            index += 1
            buffer[index] = 0x02
            index += 1
            
            # Instantaneous Speed (uint16, 0.01 km/h)
            speed = data.get('speed', 0)
            speed_value = int(speed * 100)
            struct.pack_into('<H', buffer, index, speed_value)
            index += 2
            
            # Instantaneous Cadence (uint16, 0.5 rpm)
            rpm = data.get('rpm', 0)
            cadence_value = int(rpm * 2)
            struct.pack_into('<H', buffer, index, cadence_value)
            index += 2
            
            # Instantaneous Power (sint16, watts)
            power = data.get('power', 0)
            struct.pack_into('<h', buffer, index, int(power))
            index += 2
            
            # Heart Rate (uint8, bpm)
            hr = data.get('hr', 0)
            if hr > 0:
                buffer[index] = int(hr)
            
            self.indoor_bike_data = buffer
            
            # PUSH notification if client is subscribed
            if self.indoor_bike_char and self.indoor_bike_char.is_notifying:
                self.indoor_bike_char.set_value(list(buffer))
                logger.debug(f'[{self.name}] ✓ Pushed Indoor Bike Data notification')
                
        except Exception as e:
            logger.error(f'[{self.name}] Error updating indoor bike data: {e}')
            
    def _update_cycling_power(self, data: dict):
        """Update Cycling Power Measurement characteristic and PUSH notification"""
        try:
            buffer = bytearray(8)
            index = 0
            
            # Flags (uint16) - 0x0020 = Crank Revolution Data Present
            buffer[index] = 0x20
            index += 1
            buffer[index] = 0x00
            index += 1
            
            # Instantaneous Power (sint16, watts)
            power = data.get('power', 0)
            struct.pack_into('<h', buffer, index, int(power))
            index += 2
            
            # Cumulative Crank Revolutions (uint16)
            rpm = data.get('rpm', 0)
            struct.pack_into('<H', buffer, index, int(rpm))
            index += 2
            
            # Last Crank Event Time (uint16, 1/1024 second)
            struct.pack_into('<H', buffer, index, 0)
            
            self.cycling_power_data = buffer
            
            # PUSH notification if client is subscribed
            if self.cycling_power_char and self.cycling_power_char.is_notifying:
                self.cycling_power_char.set_value(list(buffer))
                logger.debug(f'[{self.name}] ✓ Pushed Cycling Power notification')
                
        except Exception as e:
            logger.error(f'[{self.name}] Error updating cycling power: {e}')
