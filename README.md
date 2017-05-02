# WiFi Connect

This tool enables sensors to connect to a WiFi network.

When dealing with WiFi sensors, the sensor must know the SSID and password to connect to the network. One option is to program the sensor with this information before it is deployed. Another option is to have the sensor temporarily act as an access point. The user connects to the AP and enters the WiFi SSID and password. The sensor then switches out of AP mode and connects to the network.

WiFi connect takes a different approach. Using the existing home network and an Ethernet connected device, the SSID and password is securely broadcasted out to all **unassociated** sensors using the home WiFi.

There are two parts to this project: sensor and gateway.

## Sensor
### Requirements

Python 3.5 must be installed.

Install all dependencies:

```
pip install -r requirements.txt
```

There is a hard dependency on the [unassociated transfer repo](https://github.com/philipbl/unassociated_transfer.git). Clone it into your home folder.

To run,

```
python wifi_connect sensor interface_name
```

This starts a process that checks to see if the device is connected to the network. If it is not connected to a network, it puts itself in monitor mode and scans all channels looking for data from the gateway. It repeats this process until if connects to a network.


## Gateway
### Requirements

Python 3.5 must be installed. If you do not have Python 3.5 installed, follow these [instructions](http://raspberrypi.stackexchange.com/questions/54365/how-to-download-and-install-python-3-5-in-raspbian).

Next, you must install all dependencies:

```
pip install -r requirements.txt
```

Last, there is a hard dependency on the [unassociated transfer repo](https://github.com/philipbl/unassociated_transfer.git). Clone it into your home folder.

To run,

```
python wifi_connect gateway
```

This starts a web server that provides an interface to configure the network name and password for a WiFi enabled device. To access this web app, the device must be connected to Ethernet. You can then go to `http://[device-ip]:3210/`.
