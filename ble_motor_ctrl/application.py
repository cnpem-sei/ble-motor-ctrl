import dbus
from epics import caget, caput

from ble_motor_ctrl.advertisement import Advertisement
from ble_motor_ctrl.service import Application, Service, Characteristic, Descriptor

GATT_CHRC_IFACE = "org.bluez.GattCharacteristic1"
NOTIFY_TIMEOUT = 2000


class MotorAdvertisement(Advertisement):
    def __init__(self, index, name="Generic Bluetooth Controller"):
        Advertisement.__init__(self, index, "peripheral")
        self.add_local_name(name)
        self.add_manufacturer_data(0x000D, [0, 0])  # Texas Instruments
        self.include_tx_power = True


class MotorService(Service):
    MOTOR_SVC_UUID = "84e7f883-7c80-4b64-88a5-6077ce2e8925"

    def __init__(self, index, pvs):
        Service.__init__(self, index, self.MOTOR_SVC_UUID, True)
        for id, pv in enumerate(pvs, 2):
            self.add_characteristic(PosCharacteristic(self, pv_name=pv, id=id))
            self.add_characteristic(MovnCharacteristic(self, pv_name=pv, id=id))
        self.add_characteristic(RBPVCharacteristic(self))


class PosCharacteristic(Characteristic):
    def __init__(self, service, pv_name="IOC:m1", id=2):
        self.notifying = False
        self.POS_CHARACTERISTIC_UUID = f"0000000{id}-710e-4a5b-8d75-3e5b444bc3cf"

        Characteristic.__init__(self, self.POS_CHARACTERISTIC_UUID, ["write", "read", "notify"], service)
        self.pv_name = pv_name
        self.value = 0
        self.add_descriptor(DescDescriptor(self))
        self.add_descriptor(TargetPosDescriptor(self))
        self.add_descriptor(PVDescriptor(self))
        self.add_descriptor(RlvPosDescriptor(self))
        self.add_descriptor(LvioDescriptor(self))
        self.add_descriptor(StopDescriptor(self))

    def get_position(self):
        strtemp = str(round(caget(f"{self.pv_name}.RBV", timeout=1), 5))
        return [dbus.Byte(c.encode()) for c in strtemp]

    def set_pos_callback(self):
        if self.notifying:
            value = self.get_position()
            if value != self.value:
                self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])
                self.value = value

        return self.notifying

    def StartNotify(self):
        if self.notifying:
            return

        self.notifying = True

        value = self.get_position()
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])
        self.add_timeout(NOTIFY_TIMEOUT, self.set_pos_callback)

    def StopNotify(self):
        self.notifying = False

    def ReadValue(self, options):
        # Real pos
        return self.get_position()

    def WriteValue(self, value, options):
        # Target pos
        caput(self.pv_name, "".join([str(v) for v in value]))
        return value


class DescDescriptor(Descriptor):
    POS_DESCRIPTOR_UUID = "2910"

    def __init__(self, characteristic):
        self.characteristic = characteristic
        Descriptor.__init__(self, self.POS_DESCRIPTOR_UUID, ["read"], characteristic)

    def ReadValue(self, options):
        value = []
        desc = caget(f"{self.characteristic.pv_name}.DESC", timeout=1)

        for c in desc:
            value.append(dbus.Byte(c.encode()))

        return value


class TargetPosDescriptor(Descriptor):
    POS_DESCRIPTOR_UUID = "2911"

    def __init__(self, characteristic):
        self.characteristic = characteristic
        Descriptor.__init__(self, self.POS_DESCRIPTOR_UUID, ["read"], characteristic)

    def ReadValue(self, options):
        strtemp = str(round(caget(f"{self.characteristic.pv_name}.VAL", timeout=1), 5))
        return [dbus.Byte(c.encode()) for c in strtemp]


class PVDescriptor(Descriptor):
    POS_DESCRIPTOR_UUID = "2912"

    def __init__(self, characteristic):
        self.characteristic = characteristic
        Descriptor.__init__(self, self.POS_DESCRIPTOR_UUID, ["read"], characteristic)

    def ReadValue(self, options):
        return [dbus.Byte(c.encode()) for c in self.characteristic.pv_name]


class RlvPosDescriptor(Descriptor):
    POS_DESCRIPTOR_UUID = "2913"

    def __init__(self, characteristic):
        self.characteristic = characteristic
        Descriptor.__init__(self, self.POS_DESCRIPTOR_UUID, ["read", "write"], characteristic)

    def ReadValue(self, options):
        try:
            strtemp = str(round(caget(f"{self.characteristic.pv_name}.RLV", timeout=1), 5))
            return [dbus.Byte(c.encode()) for c in strtemp]
        except Exception as e:
            print(e)

    def WriteValue(self, value, options):
        caput(self.characteristic.pv_name + ".RLV", "".join([str(v) for v in value]))
        return value


class LvioDescriptor(Descriptor):
    POS_DESCRIPTOR_UUID = "2914"

    def __init__(self, characteristic):
        self.characteristic = characteristic
        Descriptor.__init__(self, self.POS_DESCRIPTOR_UUID, ["read"], characteristic)

    def ReadValue(self, options):
        try:
            strtemp = str(caget(f"{self.characteristic.pv_name}.LVIO", timeout=1))
            return [dbus.Byte(c.encode()) for c in strtemp]
        except Exception as e:
            print(e)


class StopDescriptor(Descriptor):
    POS_DESCRIPTOR_UUID = "2915"

    def __init__(self, characteristic):
        self.characteristic = characteristic
        Descriptor.__init__(self, self.POS_DESCRIPTOR_UUID, ["write"], characteristic)

    def WriteValue(self, value, options):
        caput(self.characteristic.pv_name + ".STOP", "".join([str(v) for v in value]))
        return value


class MovnCharacteristic(Characteristic):
    def __init__(self, service, pv_name="IOC:m1", id=2):
        self.notifying = False
        self.POS_CHARACTERISTIC_UUID = f"0000000{id}-710f-4a5b-8d75-3e5b444bc3cf"

        Characteristic.__init__(self, self.POS_CHARACTERISTIC_UUID, ["read", "notify"], service)
        self.pv_name = pv_name
        self.moving = 0

    def get_status(self):
        strtemp = "1" if float(caget(f"{self.pv_name}.MOVN", timeout=1)) else "0"
        return [dbus.Byte(c.encode()) for c in strtemp]

    def set_status_callback(self):
        if self.notifying:
            status = self.get_status()
            if status != self.moving:
                self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": status}, [])
                self.moving = status

        return self.notifying

    def StartNotify(self):
        if self.notifying:
            return

        self.notifying = True

        status = self.get_status()
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": status}, [])
        self.add_timeout(NOTIFY_TIMEOUT, self.set_status_callback)

    def StopNotify(self):
        self.notifying = False

    def ReadValue(self, options):
        return self.get_status()


class RBPVCharacteristic(Characteristic):
    def __init__(self, service):
        self.notifying = False
        self.RBPV_CHARACTERISTIC_UUID = "00000001-7110-4a5b-8d75-3e5b444bc3cf"

        Characteristic.__init__(self, self.RBPV_CHARACTERISTIC_UUID, ["write", "read", "notify"], service)
        self.pv_name = None
        self.pv_egu = ""
        self.pv_value = ""

    def get_value(self):
        strtemp = f"{str(caget(self.pv_name, timeout=0.3) or 'Invalid')} {self.pv_egu}"
        return [dbus.Byte(c.encode()) for c in strtemp]

    def set_value_callback(self):
        if self.notifying:
            if self.pv_name:
                value = self.get_value()
                self.pv_value = value
            else:
                value = [dbus.Byte(c.encode()) for c in "Invalid"]
            self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])

        return self.notifying

    def StartNotify(self):
        if self.notifying:
            return

        if self.pv_name:
            self.pv_egu = caget(self.pv_name + ".EGU", timeout=0.1) or " "
            value = self.get_value()
        else:
            value = [dbus.Byte(c.encode()) for c in "Invalid"]

        self.notifying = True
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])
        self.add_timeout(NOTIFY_TIMEOUT, self.set_value_callback)

    def StopNotify(self):
        self.notifying = False

    def ReadValue(self, options):
        return [dbus.Byte(c.encode()) for c in self.pv_name or "No PV"]

    def WriteValue(self, value, options):
        self.pv_name = "".join([str(v) for v in value])
        if caget(self.pv_name, timeout=0.5):
            self.pv_egu = caget(self.pv_name + ".EGU", timeout=0.1) or " "
        else:
            self.pv_name = None
        return value


def register(pvs, name):
    app = Application()
    app.add_service(MotorService(0, pvs))
    app.register()

    adv = MotorAdvertisement(0, name)
    adv.register()

    try:
        app.run()
    except KeyboardInterrupt:
        app.quit()
