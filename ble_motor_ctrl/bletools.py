"""Copyright (c) 2019, Douglas Otwell

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

import dbus

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject  # noqa: F401

BLUEZ_SERVICE_NAME = "org.bluez"
LE_ADVERTISING_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"
DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"


class BleTools(object):
    @classmethod
    def get_bus(self):
        return dbus.SystemBus()

    @classmethod
    def find_adapter(self, bus):
        remote_om = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, "/"), DBUS_OM_IFACE)
        objects = remote_om.GetManagedObjects()

        for o, props in objects.items():
            if LE_ADVERTISING_MANAGER_IFACE in props:
                return o

        return None

    @classmethod
    def power_adapter(self):
        bus = self.get_bus()

        adapter = self.get_adapter()

        adapter_props = dbus.Interface(
            bus.get_object(BLUEZ_SERVICE_NAME, adapter),
            "org.freedesktop.DBus.Properties",
        )
        adapter_props.Set("org.bluez.Adapter1", "Powered", dbus.Boolean(1))

    @classmethod
    def get_connected_devices(self):
        bus = self.get_bus()

        adapter_props = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, "/"), DBUS_OM_IFACE)
        objects = adapter_props.GetManagedObjects()
        return objects

    @classmethod
    def disconnect_all_devices(self):
        bus = self.get_bus()
        devices = self.get_connected_devices()

        for mac in devices:
            if "dev" in mac and "service" not in mac:
                device = dbus.Interface(bus.get_object(BLUEZ_SERVICE_NAME, mac), "org.bluez.Device1")
                device.Disconnect()
