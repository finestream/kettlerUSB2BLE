# Kettler Bridge
This software is a bridge between an old KettlerBike with USB Serial port to a fresh Bluetooth Low Energy peripheral implementing FTMS and some GATT services.
* the bike appears as a controlable Bike (FTMS, with SIM and ERG support)
* there is also a Cadence sensor, power meter and other services
* In SIM mode : It implements a Power Curve to fit to external feeling.

## Implemented Features
* **Gear Shift** - Full support with web UI buttons and GPIO momentary buttons
* **Momentary buttons** - GPIO pins 7 (Gear Down) and 11 (Gear Up) for hardware control
* **Power Curve** - Implemented for SIM mode with physics-based calculations

## Future Enhancements
* Power Curve fine-tuning and configuration
* OLED screen feedback (code ready, needs testing and wiring)
* Advanced sim parameters

## Tested Hardware
- **Kettler Ergorace** (https://www.bikeradar.com/reviews/training/indoor-trainers/resistance-trainer/kettler-ergorace-trainer-review/)
- **MyWhoosh Bike Trainer**
- Compatible with ZWIFT, MyWhoosh, and other FTMS-enabled cycling apps

## Minimal requirements
You need a Raspeberyy Pi zero W. The "W" version is important as you need the bluetooth version.

Kubii is a very good site, with good prices.
- the raspberry zeroW card: https://www.kubii.fr/les-cartes-raspberry-pi/1851-raspberry-pi-zero-w-kubii-3272496006997.html
- a small box to stick it under the bike : https://www.kubii.fr/accessoires-officiels-raspberry-pi/1845-boitier-officiel-pour-pi-zero-kubii-3272496006966.html
- a Micro SD card (4go is enough)
- Power Supply : USB charger 1 Ampere minimum
- micro USB cable of minimum 1.5m long (to run it along the bike)

the following kit contains a lot of stuff (Budget)
https://www.kubii.fr/home/2077-kit-pi-zero-w-kubii-3272496009509.html#/237-selectionnez_votre_kit-starter_16_go

To connect the Raspberry to the bike
- a usb cable B to micro-USB https://www.amazon.fr/Apark-USB-Connecteur-Interface-Adaptateur/dp/B0885SV415/ref=sr_1_6?__mk_fr_FR=%C3%85M%C3%85%C5%BD%C3%95%C3%91&dchild=1&keywords=cable%2BUSB%2Bb%2Bvers%2Bmicro%2Busb&qid=1606051026&quartzVehicle=694-1217&replacementKeywords=cable%2Busb%2Bvers%2Bmicro%2Busb&sr=8-6&th=1
- or an adaptor + usb Cable

## Quick Setup
An image of the full system is available.
You can directly download and write it on an sd card.

it contains:
- a Raspbian systeme
- KettlerUSB (without Oled Display)
- An autostart script

it also inclue
- a wifi hotspot to access the Pi. (password is always = Password)

Download this image
https://drive.google.com/file/d/13brFb1yyl03pNfKIfYgkOhw5_Ije4iDB/view?usp=sharing

Follow these instructions: 
https://opensource.com/article/17/3/how-write-sd-cards-raspberry-pi


## Setup

### Pi Zero 2W on Debian Bookworm 64-bit ARM (Manual Setup)

#### Step 1: Update system packages
```bash
sudo apt update && sudo apt upgrade -y
```

#### Step 2: Install dependencies
```bash
sudo apt install -y bluetooth bluez libbluetooth-dev libudev-dev \
  git python3-dev build-essential libncurses-dev libreadline-dev \
  usbutils curl wget
```

#### Step 3: Install Node.js (v20 LTS)
For Pi Zero 2W with Bookworm 64-bit ARM:
```bash
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt install -y nodejs
node --version  # Verify installation
npm --version
```

#### Step 4: Disable Bluetooth service
Bleno implements its own Bluetooth stack, so we need to disable the system service:
```bash
sudo systemctl disable bluetooth
sudo systemctl stop bluetooth
```

#### Step 5: Enable Bluetooth hardware
Prepare the Bluetooth interface (will be managed by Bleno):
```bash
sudo hciconfig hci0 up
```

#### Step 6: Clone and install KettlerUSB2BLE
```bash
cd ~
git clone https://github.com/360manu/kettlerUSB2BLE.git
cd ~/kettlerUSB2BLE
npm install
```

**Note:** This step compiles Bleno from source and may take 5-10 minutes on a Pi Zero 2W. Do NOT use sudo for npm install as it breaks the build.

#### Step 7: Copy the systemd service file
The service file is included in the repository. Copy and enable it:
```bash
sudo cp ~/kettlerUSB2BLE/kettler.service /etc/systemd/system/
sudo systemctl daemon-reload
```

#### Step 8: Enable and start the service
```bash
sudo systemctl enable kettler.service
sudo systemctl start kettler.service
```

#### Step 9: Verify the service is running
```bash
sudo systemctl status kettler.service
journalctl -u Kettler -f  # View live logs (uses SyslogIdentifier)
```

#### Step 10: USB Power Configuration (Optional but recommended)
To ensure sufficient power for the Bluetooth operations:

Edit `/boot/firmware/config.txt`:
```bash
sudo nano /boot/firmware/config.txt
```

Add this line (or modify if exists):
```
max_usb_current=1
```

Reboot for changes to take effect:
```bash
sudo reboot
```

### Connection Setup

1. **Plug in the Kettler bike:** Connect a USB cable from the Pi Zero 2W's data USB port (the center micro-USB port) to your Kettler bike's USB port.
   - Use a USB-A to micro-USB-B cable or adapter

2. **Access the web interface:** Once the service is running, open your browser and navigate to:
   ```
   http://<pi-ip-address>:3000
   ```

3. **Pair with Zwift/compatible apps:** Your Kettler bike should now appear as a Bluetooth peripheral (FTMS compatible) ready to pair with cycling apps.

### Troubleshooting

- **Service won't start:** Check logs with `journalctl -u Kettler -f` or `sudo systemctl status kettler.service`
- **Bluetooth not found:** Verify `sudo hciconfig` shows `hci0 UP RUNNING`
- **USB connection issues:** Try a different USB cable or check `dmesg` for device recognition
- **npm install fails:** Ensure you're using the `pi` user (not sudo) and have enough disk space
- **sudo: command not found in service:** The service uses `sudo` in ExecStart - ensure the `pi` user has passwordless sudo configured

### Legacy Setup Notes

For older Pi Zero W with Raspbian Jessie/Stretch, see the original instructions above. The new setup is optimized for Pi Zero 2W with modern Debian distributions.
* an old one from USB B to USB A
it's not very clean but it works

The Linux version installed on the PI already contains the CP21xx drivers.
-> Nothing special on this side

## Usage

### Start
First try (need to sudo for bleno):
```
sudo node server.js
```

You should hear a sound from the bike when the Serial connection is OK.
On the bike screen, you can now see the "USB" icons

If you scan for BLE peripheral (use Nordic RF app fro ANdroid or IPhone for example)
Your kettler bike should appear as KettlerBLE device with two services (power & FTMS)

### website
The Bridge is also a simple web server.
It help debuging and have more feedback on the current state of the bike.

I use a static IP for the PI (see the doc of your router)
* modify the index.ejs (line 47) file with the ip of your raspbery
* start your browser pi-adress:3000

you can follow the bridge activity on a simple website.
It will display the current power, HR et speed and some logs.
It's also possible to switch gears.

### Running as a service
For an automatic launch with the raspberry 
```
sudo systemctl link /home/pi/kettlerUSB2BLE/kettler.service
```
-> Created symlink /etc/systemd/system/kettler.service → /home/pi/kettlerUSB2BLE/kettler.service.

```
sudo systemctl enable kettler.service
sudo systemctl start kettler.service
```
