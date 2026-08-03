# BluetoothGatt  |  API reference
> 原文链接: https://developer.android.com/reference/android/bluetooth/BluetoothGatt

---

-   [Android Developers](https://developer.android.com/)
-   [Develop](https://developer.android.com/develop)
-   [API reference](https://developer.android.com/reference)

-   On this page
-   [Summary](#summary)
    -   [Constants](#constants)
    -   [Inherited constants](#inherited-constants)
    -   [Public methods](#public-methods)
    -   [Inherited methods](#inherited-methods)
-   [Constants](#constants_1)
    -   [CONNECTION\_PRIORITY\_BALANCED](#CONNECTION_PRIORITY_BALANCED)
    -   [CONNECTION\_PRIORITY\_DCK](#CONNECTION_PRIORITY_DCK)
    -   [CONNECTION\_PRIORITY\_HIGH](#CONNECTION_PRIORITY_HIGH)
    -   [CONNECTION\_PRIORITY\_LOW\_POWER](#CONNECTION_PRIORITY_LOW_POWER)
    -   [GATT\_CONNECTION\_CONGESTED](#GATT_CONNECTION_CONGESTED)
    -   [GATT\_CONNECTION\_TIMEOUT](#GATT_CONNECTION_TIMEOUT)
    -   [GATT\_FAILURE](#GATT_FAILURE)
    -   [GATT\_INSUFFICIENT\_AUTHENTICATION](#GATT_INSUFFICIENT_AUTHENTICATION)
    -   [GATT\_INSUFFICIENT\_AUTHORIZATION](#GATT_INSUFFICIENT_AUTHORIZATION)
    -   [GATT\_INSUFFICIENT\_ENCRYPTION](#GATT_INSUFFICIENT_ENCRYPTION)
    -   [GATT\_INVALID\_ATTRIBUTE\_LENGTH](#GATT_INVALID_ATTRIBUTE_LENGTH)
    -   [GATT\_INVALID\_OFFSET](#GATT_INVALID_OFFSET)
    -   [GATT\_READ\_NOT\_PERMITTED](#GATT_READ_NOT_PERMITTED)
    -   [GATT\_REQUEST\_NOT\_SUPPORTED](#GATT_REQUEST_NOT_SUPPORTED)
    -   [GATT\_SUCCESS](#GATT_SUCCESS)
    -   [GATT\_WRITE\_NOT\_PERMITTED](#GATT_WRITE_NOT_PERMITTED)
    -   [SUBRATE\_MODE\_BALANCED](#SUBRATE_MODE_BALANCED)
    -   [SUBRATE\_MODE\_HIGH](#SUBRATE_MODE_HIGH)
    -   [SUBRATE\_MODE\_LOW](#SUBRATE_MODE_LOW)
    -   [SUBRATE\_MODE\_NOT\_UPDATED](#SUBRATE_MODE_NOT_UPDATED)
    -   [SUBRATE\_MODE\_OFF](#SUBRATE_MODE_OFF)
    -   [SUBRATE\_MODE\_SYSTEM\_UPDATE](#SUBRATE_MODE_SYSTEM_UPDATE)
-   [Public methods](#public-methods_1)
    -   [abortReliableWrite](#abortReliableWrite\(android.bluetooth.BluetoothDevice\))
    -   [abortReliableWrite](#abortReliableWrite\(\))
    -   [beginReliableWrite](#beginReliableWrite\(\))
    -   [close](#close\(\))
    -   [connect](#connect\(\))
    -   [disconnect](#disconnect\(\))
    -   [discoverServices](#discoverServices\(\))
    -   [executeReliableWrite](#executeReliableWrite\(\))
    -   [getConnectedDevices](#getConnectedDevices\(\))
    -   [getConnectionState](#getConnectionState\(android.bluetooth.BluetoothDevice\))
    -   [getDevice](#getDevice\(\))
    -   [getDevicesMatchingConnectionStates](#getDevicesMatchingConnectionStates\(int[]\))
    -   [getService](#getService\(java.util.UUID\))
    -   [getServices](#getServices\(\))
    -   [readCharacteristic](#readCharacteristic\(android.bluetooth.BluetoothGattCharacteristic\))
    -   [readDescriptor](#readDescriptor\(android.bluetooth.BluetoothGattDescriptor\))
    -   [readPhy](#readPhy\(\))
    -   [readRemoteRssi](#readRemoteRssi\(\))
    -   [requestConnectionPriority](#requestConnectionPriority\(int\))
    -   [requestMtu](#requestMtu\(int\))
    -   [requestSubrateMode](#requestSubrateMode\(int\))
    -   [setCharacteristicNotification](#setCharacteristicNotification\(android.bluetooth.BluetoothGattCharacteristic,%20boolean\))
    -   [setPreferredPhy](#setPreferredPhy\(int,%20int,%20int\))
    -   [writeCharacteristic](#writeCharacteristic\(android.bluetooth.BluetoothGattCharacteristic\))
    -   [writeCharacteristic](#writeCharacteristic\(android.bluetooth.BluetoothGattCharacteristic,%20byte[],%20int\))
    -   [writeDescriptor](#writeDescriptor\(android.bluetooth.BluetoothGattDescriptor\))
    -   [writeDescriptor](#writeDescriptor\(android.bluetooth.BluetoothGattDescriptor,%20byte[]\))

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

Summary: [Constants](#constants) | [Inherited Constants](#inhconstants) | [Methods](#pubmethods) | [Inherited Methods](#inhmethods)

# BluetoothGatt Stay organized with collections Save and categorize content based on your preferences.

* * *

[Kotlin](https://developer.android.com/reference/kotlin/android/bluetooth/BluetoothGatt) |Java

`public final class BluetoothGatt`
`extends [Object](https://developer.android.com/reference/java/lang/Object)` `implements [BluetoothProfile](https://developer.android.com/reference/android/bluetooth/BluetoothProfile)`

<table class="jd-inheritance-table"><tbody><tr><td colspan="2" class="jd-inheritance-class-cell"><a href="https://developer.android.com/reference/java/lang/Object">java.lang.Object</a></td></tr><tr><td class="jd-inheritance-space">&nbsp;&nbsp;&nbsp;↳</td><td colspan="1" class="jd-inheritance-class-cell">android.bluetooth.BluetoothGatt</td></tr></tbody></table>

* * *

Public API for the Bluetooth GATT Profile.

This class provides Bluetooth GATT functionality to enable communication with Bluetooth Smart or Smart Ready devices.

To connect to a remote peripheral device, create a `[BluetoothGattCallback](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback)` and call `[BluetoothDevice.connectGatt](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#connectGatt\(android.bluetooth.BluetoothGattConnectionSettings,%20java.util.concurrent.Executor,%20android.bluetooth.BluetoothGattCallback\))` to get a instance of this class. GATT capable devices can be discovered using the Bluetooth device discovery or BLE scan process.

## Summary

|
### Constants

 |
| --- |
| `int` | `[CONNECTION_PRIORITY_BALANCED](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#CONNECTION_PRIORITY_BALANCED)`

Connection parameter update - Use the connection parameters recommended by the Bluetooth SIG.

 |
| `int` | `[CONNECTION_PRIORITY_DCK](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#CONNECTION_PRIORITY_DCK)`

Connection parameter update - Request the priority preferred for Digital Car Key for a lower latency connection.

 |
| `int` | `[CONNECTION_PRIORITY_HIGH](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#CONNECTION_PRIORITY_HIGH)`

Connection parameter update - Request a high priority, low latency connection.

 |
| `int` | `[CONNECTION_PRIORITY_LOW_POWER](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#CONNECTION_PRIORITY_LOW_POWER)`

Connection parameter update - Request low power, reduced data rate connection parameters.

 |
| `int` | `[GATT_CONNECTION_CONGESTED](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#GATT_CONNECTION_CONGESTED)`

A remote device connection is congested.

 |
| `int` | `[GATT_CONNECTION_TIMEOUT](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#GATT_CONNECTION_TIMEOUT)`

GATT connection timed out, likely due to the remote device being out of range or not advertising as connectable.

 |
| `int` | `[GATT_FAILURE](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#GATT_FAILURE)`

A GATT operation failed, errors other than the above

 |
| `int` | `[GATT_INSUFFICIENT_AUTHENTICATION](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#GATT_INSUFFICIENT_AUTHENTICATION)`

Insufficient authentication for a given operation

 |
| `int` | `[GATT_INSUFFICIENT_AUTHORIZATION](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#GATT_INSUFFICIENT_AUTHORIZATION)`

Insufficient authorization for a given operation

 |
| `int` | `[GATT_INSUFFICIENT_ENCRYPTION](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#GATT_INSUFFICIENT_ENCRYPTION)`

Insufficient encryption for a given operation

 |
| `int` | `[GATT_INVALID_ATTRIBUTE_LENGTH](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#GATT_INVALID_ATTRIBUTE_LENGTH)`

A write operation exceeds the maximum length of the attribute

 |
| `int` | `[GATT_INVALID_OFFSET](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#GATT_INVALID_OFFSET)`

A read or write operation was requested with an invalid offset

 |
| `int` | `[GATT_READ_NOT_PERMITTED](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#GATT_READ_NOT_PERMITTED)`

GATT read operation is not permitted

 |
| `int` | `[GATT_REQUEST_NOT_SUPPORTED](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#GATT_REQUEST_NOT_SUPPORTED)`

The given request is not supported

 |
| `int` | `[GATT_SUCCESS](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#GATT_SUCCESS)`

A GATT operation completed successfully

 |
| `int` | `[GATT_WRITE_NOT_PERMITTED](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#GATT_WRITE_NOT_PERMITTED)`

GATT write operation is not permitted

 |
| `int` | `[SUBRATE_MODE_BALANCED](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#SUBRATE_MODE_BALANCED)`

Connection subrate mode - Requests to enable subrate mode using balanced parameters to provide a compromise between power savings and performance.

 |
| `int` | `[SUBRATE_MODE_HIGH](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#SUBRATE_MODE_HIGH)`

Connection subrate mode - Requests to enable subrate mode with parameters optimized for high burstiness, enhanced data transfer.

 |
| `int` | `[SUBRATE_MODE_LOW](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#SUBRATE_MODE_LOW)`

Connection Subrate mode - Requests to enable subrate mode with parameters optimized for low burstiness, minimum power consumption.

 |
| `int` | `[SUBRATE_MODE_NOT_UPDATED](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#SUBRATE_MODE_NOT_UPDATED)`

Connection Subrate mode - No Update applied due to error.

 |
| `int` | `[SUBRATE_MODE_OFF](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#SUBRATE_MODE_OFF)`

Connection Subrate mode - Request to disable subrate mode.

 |
| `int` | `[SUBRATE_MODE_SYSTEM_UPDATE](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#SUBRATE_MODE_SYSTEM_UPDATE)`

Connection Subrate mode - System Update.

 |

|
### Inherited constants

 |
| --- |
| From interface `[android.bluetooth.BluetoothProfile](https://developer.android.com/reference/android/bluetooth/BluetoothProfile)`

<table class="responsive"><tbody><tr data-version-added="11"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#A2DP">A2DP</a></code><p>Advanced Audio Distribution Profile (A2DP)</p></td></tr><tr data-version-added="33"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#CSIP_SET_COORDINATOR">CSIP_SET_COORDINATOR</a></code><p>Coordinated Set Identification Profile (CSIP) set coordinator</p></td></tr><tr data-version-added="11"><td><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/String">String</a></code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#EXTRA_PREVIOUS_STATE">EXTRA_PREVIOUS_STATE</a></code><p>Extra for the connection state intents of the individual profiles.</p></td></tr><tr data-version-added="36.1"><td><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/String">String</a></code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#EXTRA_PROFILE">EXTRA_PROFILE</a></code><p>Extra for the <code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile">BluetoothProfile</a></code> that the intent applies to.</p></td></tr><tr data-version-added="11"><td><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/String">String</a></code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#EXTRA_STATE">EXTRA_STATE</a></code><p>Extra for the connection state intents of the individual profiles.</p></td></tr><tr data-version-added="18"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#GATT">GATT</a></code><p>Generic Attribute Profile (GATT)</p></td></tr><tr data-version-added="18"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#GATT_SERVER">GATT_SERVER</a></code><p>Generic Attribute Profile (GATT) Server</p></td></tr><tr data-version-added="33"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#HAP_CLIENT">HAP_CLIENT</a></code><p></p></td></tr><tr data-version-added="11"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#HEADSET">HEADSET</a></code><p>Headset and Handsfree profile</p></td></tr><tr data-version-added="14" data-version-deprecated="29"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#HEALTH">HEALTH</a></code><p><em>This constant was deprecated in API level 29. Health Device Profile (HDP) and MCAP protocol are no longer used. New apps should use Bluetooth Low Energy based solutions such as <code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothGatt">BluetoothGatt</a></code>, <code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothAdapter#listenUsingL2capChannel()">BluetoothAdapter.listenUsingL2capChannel()</a></code>, or <code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothDevice#createL2capChannel(int)">BluetoothDevice.createL2capChannel(int)</a></code></em></p></td></tr><tr data-version-added="29"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#HEARING_AID">HEARING_AID</a></code><p>Hearing Aid Device</p></td></tr><tr data-version-added="28"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#HID_DEVICE">HID_DEVICE</a></code><p>Human Interface Device (HID) Device</p></td></tr><tr data-version-added="33"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#LE_AUDIO">LE_AUDIO</a></code><p>LE Audio Device</p></td></tr><tr data-version-added="23"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#SAP">SAP</a></code><p>SIM Access Profile (SAP)</p></td></tr><tr data-version-added="11"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_CONNECTED">STATE_CONNECTED</a></code><p>The profile is in connected state</p></td></tr><tr data-version-added="11"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_CONNECTING">STATE_CONNECTING</a></code><p>The profile is in connecting state</p></td></tr><tr data-version-added="11"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_DISCONNECTED">STATE_DISCONNECTED</a></code><p>The profile is in disconnected state</p></td></tr><tr data-version-added="11"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_DISCONNECTING">STATE_DISCONNECTING</a></code><p>The profile is in disconnecting state</p></td></tr></tbody></table>

 |

|
### Public methods

 |
| --- |
| `void` | `[abortReliableWrite](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#abortReliableWrite\(android.bluetooth.BluetoothDevice\))([BluetoothDevice](https://developer.android.com/reference/android/bluetooth/BluetoothDevice) mDevice)`

_This method was deprecated in API level 19. Use `[abortReliableWrite()](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#abortReliableWrite\(\))`_

 |
| `void` | `[abortReliableWrite](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#abortReliableWrite\(\))()`

Cancels a reliable write transaction for a given device.

 |
| `boolean` | `[beginReliableWrite](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#beginReliableWrite\(\))()`

Initiates a reliable write transaction for a given remote device.

 |
| `void` | `[close](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#close\(\))()`

Close this Bluetooth GATT client.

 |
| `boolean` | `[connect](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#connect\(\))()`

Connect back to remote device.

 |
| `void` | `[disconnect](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#disconnect\(\))()`

Disconnects an established connection, or cancels a connection attempt currently in progress.

 |
| `boolean` | `[discoverServices](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#discoverServices\(\))()`

Discovers services offered by a remote device as well as their characteristics and descriptors.

 |
| `boolean` | `[executeReliableWrite](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#executeReliableWrite\(\))()`

Executes a reliable write transaction for a given remote device.

 |
| `[List](https://developer.android.com/reference/java/util/List)<[BluetoothDevice](https://developer.android.com/reference/android/bluetooth/BluetoothDevice)>` | `[getConnectedDevices](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#getConnectedDevices\(\))()`

_This method is deprecated. Not supported - please use `[BluetoothManager.getConnectedDevices(int)](https://developer.android.com/reference/android/bluetooth/BluetoothManager#getConnectedDevices\(int\))` with `[BluetoothProfile.GATT](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#GATT)` as argument_

 |
| `int` | `[getConnectionState](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#getConnectionState\(android.bluetooth.BluetoothDevice\))([BluetoothDevice](https://developer.android.com/reference/android/bluetooth/BluetoothDevice) device)`

_This method is deprecated. Not supported - please use `[BluetoothManager.getConnectedDevices(int)](https://developer.android.com/reference/android/bluetooth/BluetoothManager#getConnectedDevices\(int\))` with `[BluetoothProfile.GATT](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#GATT)` as argument_

 |
| `[BluetoothDevice](https://developer.android.com/reference/android/bluetooth/BluetoothDevice)` | `[getDevice](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#getDevice\(\))()`

Return the remote bluetooth device this GATT client targets to

 |
| `[List](https://developer.android.com/reference/java/util/List)<[BluetoothDevice](https://developer.android.com/reference/android/bluetooth/BluetoothDevice)>` | `[getDevicesMatchingConnectionStates](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#getDevicesMatchingConnectionStates\(int[]\))(int[] states)`

_This method is deprecated. Not supported - please use `[BluetoothManager.getDevicesMatchingConnectionStates(int,int[])](https://developer.android.com/reference/android/bluetooth/BluetoothManager#getDevicesMatchingConnectionStates\(int,%20int[]\))` with `[BluetoothProfile.GATT](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#GATT)` as first argument_

 |
| `[BluetoothGattService](https://developer.android.com/reference/android/bluetooth/BluetoothGattService)` | `[getService](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#getService\(java.util.UUID\))([UUID](https://developer.android.com/reference/java/util/UUID) uuid)`

Returns a `[BluetoothGattService](https://developer.android.com/reference/android/bluetooth/BluetoothGattService)`, if the requested UUID is supported by the remote device.

 |
| `[List](https://developer.android.com/reference/java/util/List)<[BluetoothGattService](https://developer.android.com/reference/android/bluetooth/BluetoothGattService)>` | `[getServices](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#getServices\(\))()`

Returns a list of GATT services offered by the remote device.

 |
| `boolean` | `[readCharacteristic](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#readCharacteristic\(android.bluetooth.BluetoothGattCharacteristic\))([BluetoothGattCharacteristic](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic) characteristic)`

Reads the requested characteristic from the associated remote device.

 |
| `boolean` | `[readDescriptor](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#readDescriptor\(android.bluetooth.BluetoothGattDescriptor\))([BluetoothGattDescriptor](https://developer.android.com/reference/android/bluetooth/BluetoothGattDescriptor) descriptor)`

Reads the value for a given descriptor from the associated remote device.

 |
| `void` | `[readPhy](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#readPhy\(\))()`

Read the current transmitter PHY and receiver PHY of the connection.

 |
| `boolean` | `[readRemoteRssi](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#readRemoteRssi\(\))()`

Read the RSSI for a connected remote device.

 |
| `boolean` | `[requestConnectionPriority](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#requestConnectionPriority\(int\))(int connectionPriority)`

Request a connection parameter update.

 |
| `boolean` | `[requestMtu](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#requestMtu\(int\))(int mtu)`

Request an MTU size used for a given connection.

 |
| `int` | `[requestSubrateMode](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#requestSubrateMode\(int\))(int subrateMode)`

Request LE subrate mode.

 |
| `boolean` | `[setCharacteristicNotification](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#setCharacteristicNotification\(android.bluetooth.BluetoothGattCharacteristic,%20boolean\))([BluetoothGattCharacteristic](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic) characteristic, boolean enable)`

Enable or disable notifications/indications for a given characteristic.

 |
| `void` | `[setPreferredPhy](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#setPreferredPhy\(int,%20int,%20int\))(int txPhy, int rxPhy, int phyOptions)`

Set the preferred connection PHY for this app.

 |
| `boolean` | `[writeCharacteristic](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#writeCharacteristic\(android.bluetooth.BluetoothGattCharacteristic\))([BluetoothGattCharacteristic](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic) characteristic)`

_This method was deprecated in API level 33. Use `[BluetoothGatt.writeCharacteristic(BluetoothGattCharacteristic,byte[],int)](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#writeCharacteristic\(android.bluetooth.BluetoothGattCharacteristic,%20byte[],%20int\))` as this is not memory safe because it relies on a `[BluetoothGattCharacteristic](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic)` object whose underlying fields are subject to change outside this method._

 |
| `int` | `[writeCharacteristic](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#writeCharacteristic\(android.bluetooth.BluetoothGattCharacteristic,%20byte[],%20int\))([BluetoothGattCharacteristic](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic) characteristic, byte[] value, int writeType)`

Writes a given characteristic and its values to the associated remote device.

 |
| `boolean` | `[writeDescriptor](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#writeDescriptor\(android.bluetooth.BluetoothGattDescriptor\))([BluetoothGattDescriptor](https://developer.android.com/reference/android/bluetooth/BluetoothGattDescriptor) descriptor)`

_This method was deprecated in API level 33. Use `[BluetoothGatt.writeDescriptor(BluetoothGattDescriptor,byte[])](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#writeDescriptor\(android.bluetooth.BluetoothGattDescriptor,%20byte[]\))` as this is not memory safe because it relies on a `[BluetoothGattDescriptor](https://developer.android.com/reference/android/bluetooth/BluetoothGattDescriptor)` object whose underlying fields are subject to change outside this method._

 |
| `int` | `[writeDescriptor](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#writeDescriptor\(android.bluetooth.BluetoothGattDescriptor,%20byte[]\))([BluetoothGattDescriptor](https://developer.android.com/reference/android/bluetooth/BluetoothGattDescriptor) descriptor, byte[] value)`

Write the value of a given descriptor to the associated remote device.

 |

|
### Inherited methods

 |
| --- |
| From class `[java.lang.Object](https://developer.android.com/reference/java/lang/Object)`

<table class="responsive"><tbody><tr data-version-added="1"><td><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object">Object</a></code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#clone()">clone</a>()</code><p>Creates and returns a copy of this object.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">boolean</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#equals(java.lang.Object)">equals</a>(<a href="https://developer.android.com/reference/java/lang/Object">Object</a> obj)</code><p>Indicates whether some other object is "equal to" this one.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#finalize()">finalize</a>()</code><p>Called by the garbage collector on an object when garbage collection determines that there are no more references to the object.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final <a href="https://developer.android.com/reference/java/lang/Class">Class</a>&lt;?&gt;</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#getClass()">getClass</a>()</code><p>Returns the runtime class of this <code translate="no" dir="ltr">Object</code>.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#hashCode()">hashCode</a>()</code><p>Returns a hash code value for the object.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#notify()">notify</a>()</code><p>Wakes up a single thread that is waiting on this object's monitor.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#notifyAll()">notifyAll</a>()</code><p>Wakes up all threads that are waiting on this object's monitor.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/String">String</a></code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#toString()">toString</a>()</code><p>Returns a string representation of the object.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#wait(long,%20int)">wait</a>(long timeoutMillis, int nanos)</code><p>Causes the current thread to wait until it is awakened, typically by being <em>notified</em> or <em>interrupted</em>, or until a certain amount of real time has elapsed.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#wait(long)">wait</a>(long timeoutMillis)</code><p>Causes the current thread to wait until it is awakened, typically by being <em>notified</em> or <em>interrupted</em>, or until a certain amount of real time has elapsed.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#wait()">wait</a>()</code><p>Causes the current thread to wait until it is awakened, typically by being <em>notified</em> or <em>interrupted</em>.</p></td></tr></tbody></table>

 |
| From interface `[android.bluetooth.BluetoothProfile](https://developer.android.com/reference/android/bluetooth/BluetoothProfile)`

<table class="responsive"><tbody><tr data-version-added="11"><td><code translate="no" dir="ltr">abstract <a href="https://developer.android.com/reference/java/util/List">List</a>&lt;<a href="https://developer.android.com/reference/android/bluetooth/BluetoothDevice">BluetoothDevice</a>&gt;</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#getConnectedDevices()">getConnectedDevices</a>()</code><p>Get connected devices for this specific profile.</p></td></tr><tr data-version-added="11"><td><code translate="no" dir="ltr">abstract int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#getConnectionState(android.bluetooth.BluetoothDevice)">getConnectionState</a>(<a href="https://developer.android.com/reference/android/bluetooth/BluetoothDevice">BluetoothDevice</a> device)</code><p>Get the current connection state of the profile</p></td></tr><tr data-version-added="11"><td><code translate="no" dir="ltr">abstract <a href="https://developer.android.com/reference/java/util/List">List</a>&lt;<a href="https://developer.android.com/reference/android/bluetooth/BluetoothDevice">BluetoothDevice</a>&gt;</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/bluetooth/BluetoothProfile#getDevicesMatchingConnectionStates(int[])">getDevicesMatchingConnectionStates</a>(int[] states)</code><p>Get a list of devices that match any of the given connection states.</p></td></tr></tbody></table>

 |

## Constants

### CONNECTION\_PRIORITY\_BALANCED

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int CONNECTION\_PRIORITY\_BALANCED

Connection parameter update - Use the connection parameters recommended by the Bluetooth SIG. This is the default value if no connection parameter update is requested.

Constant Value: 0 (0x00000000)

### CONNECTION\_PRIORITY\_DCK

Added in [API level 34](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int CONNECTION\_PRIORITY\_DCK

Connection parameter update - Request the priority preferred for Digital Car Key for a lower latency connection. This connection parameter will consume more power than `[BluetoothGatt.CONNECTION_PRIORITY_BALANCED](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#CONNECTION_PRIORITY_BALANCED)`, so it is recommended that apps do not use this unless it specifically fits their use case.

Constant Value: 3 (0x00000003)

### CONNECTION\_PRIORITY\_HIGH

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int CONNECTION\_PRIORITY\_HIGH

Connection parameter update - Request a high priority, low latency connection. An application should only request high priority connection parameters to transfer large amounts of data over LE quickly. Once the transfer is complete, the application should request `[BluetoothGatt.CONNECTION_PRIORITY_BALANCED](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#CONNECTION_PRIORITY_BALANCED)` connection parameters to reduce energy use.

Constant Value: 1 (0x00000001)

### CONNECTION\_PRIORITY\_LOW\_POWER

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int CONNECTION\_PRIORITY\_LOW\_POWER

Connection parameter update - Request low power, reduced data rate connection parameters.

Constant Value: 2 (0x00000002)

### GATT\_CONNECTION\_CONGESTED

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int GATT\_CONNECTION\_CONGESTED

A remote device connection is congested.

Constant Value: 143 (0x0000008f)

### GATT\_CONNECTION\_TIMEOUT

Added in [API level 35](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int GATT\_CONNECTION\_TIMEOUT

GATT connection timed out, likely due to the remote device being out of range or not advertising as connectable.

Constant Value: 147 (0x00000093)

### GATT\_FAILURE

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int GATT\_FAILURE

A GATT operation failed, errors other than the above

Constant Value: 257 (0x00000101)

### GATT\_INSUFFICIENT\_AUTHENTICATION

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int GATT\_INSUFFICIENT\_AUTHENTICATION

Insufficient authentication for a given operation

Constant Value: 5 (0x00000005)

### GATT\_INSUFFICIENT\_AUTHORIZATION

Added in [API level 33](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int GATT\_INSUFFICIENT\_AUTHORIZATION

Insufficient authorization for a given operation

Constant Value: 8 (0x00000008)

### GATT\_INSUFFICIENT\_ENCRYPTION

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int GATT\_INSUFFICIENT\_ENCRYPTION

Insufficient encryption for a given operation

Constant Value: 15 (0x0000000f)

### GATT\_INVALID\_ATTRIBUTE\_LENGTH

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int GATT\_INVALID\_ATTRIBUTE\_LENGTH

A write operation exceeds the maximum length of the attribute

Constant Value: 13 (0x0000000d)

### GATT\_INVALID\_OFFSET

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int GATT\_INVALID\_OFFSET

A read or write operation was requested with an invalid offset

Constant Value: 7 (0x00000007)

### GATT\_READ\_NOT\_PERMITTED

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int GATT\_READ\_NOT\_PERMITTED

GATT read operation is not permitted

Constant Value: 2 (0x00000002)

### GATT\_REQUEST\_NOT\_SUPPORTED

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int GATT\_REQUEST\_NOT\_SUPPORTED

The given request is not supported

Constant Value: 6 (0x00000006)

### GATT\_SUCCESS

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int GATT\_SUCCESS

A GATT operation completed successfully

Constant Value: 0 (0x00000000)

### GATT\_WRITE\_NOT\_PERMITTED

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int GATT\_WRITE\_NOT\_PERMITTED

GATT write operation is not permitted

Constant Value: 3 (0x00000003)

### SUBRATE\_MODE\_BALANCED

Added in [version 36.1](https://developer.android.com/topic/libraries/support-library/revisions)

public static final int SUBRATE\_MODE\_BALANCED

Connection subrate mode - Requests to enable subrate mode using balanced parameters to provide a compromise between power savings and performance.

Constant Value: 2 (0x00000002)

### SUBRATE\_MODE\_HIGH

Added in [version 36.1](https://developer.android.com/topic/libraries/support-library/revisions)

public static final int SUBRATE\_MODE\_HIGH

Connection subrate mode - Requests to enable subrate mode with parameters optimized for high burstiness, enhanced data transfer.

Constant Value: 3 (0x00000003)

### SUBRATE\_MODE\_LOW

Added in [version 36.1](https://developer.android.com/topic/libraries/support-library/revisions)

public static final int SUBRATE\_MODE\_LOW

Connection Subrate mode - Requests to enable subrate mode with parameters optimized for low burstiness, minimum power consumption. This is the most power-efficient subrate configuration.

Constant Value: 1 (0x00000001)

### SUBRATE\_MODE\_NOT\_UPDATED

Added in [version 36.1](https://developer.android.com/topic/libraries/support-library/revisions)

public static final int SUBRATE\_MODE\_NOT\_UPDATED

Connection Subrate mode - No Update applied due to error.

Constant Value: 255 (0x000000ff)

### SUBRATE\_MODE\_OFF

Added in [version 36.1](https://developer.android.com/topic/libraries/support-library/revisions)

public static final int SUBRATE\_MODE\_OFF

Connection Subrate mode - Request to disable subrate mode.

Constant Value: 0 (0x00000000)

### SUBRATE\_MODE\_SYSTEM\_UPDATE

Added in [version 36.1](https://developer.android.com/topic/libraries/support-library/revisions)

public static final int SUBRATE\_MODE\_SYSTEM\_UPDATE

Connection Subrate mode - System Update.

Constant Value: 99 (0x00000063)

## Public methods

### abortReliableWrite

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)
Deprecated in [API level 19](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public void abortReliableWrite ([BluetoothDevice](https://developer.android.com/reference/android/bluetooth/BluetoothDevice) mDevice)

**This method was deprecated in API level 19.**
Use `[abortReliableWrite()](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#abortReliableWrite\(\))`

For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Parameters |
| --- |
| `mDevice` | `BluetoothDevice`
 |

### abortReliableWrite

Added in [API level 19](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public void abortReliableWrite ()

Cancels a reliable write transaction for a given device.

Calling this function will discard all queued characteristic write operations for a given remote device.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

### beginReliableWrite

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean beginReliableWrite ()

Initiates a reliable write transaction for a given remote device.

Once a reliable write transaction has been initiated, all calls to `[writeCharacteristic(BluetoothGattCharacteristic)](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#writeCharacteristic\(android.bluetooth.BluetoothGattCharacteristic\))` are sent to the remote device for verification and queued up for atomic execution. The application will receive a `[BluetoothGattCallback.onCharacteristicWrite](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onCharacteristicWrite\(android.bluetooth.BluetoothGatt,%20android.bluetooth.BluetoothGattCharacteristic,%20int\))` callback in response to every `[writeCharacteristic(BluetoothGattCharacteristic,byte[],int)](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#writeCharacteristic\(android.bluetooth.BluetoothGattCharacteristic,%20byte[],%20int\))` call and is responsible for verifying if the value has been transmitted accurately.

After all characteristics have been queued up and verified, `[executeReliableWrite()](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#executeReliableWrite\(\))` will execute all writes. If a characteristic was not written correctly, calling `[abortReliableWrite()](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#abortReliableWrite\(\))` will cancel the current transaction without committing any values on the remote device.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Returns |
| --- |
| `boolean` | true, if the reliable write transaction has been initiated
 |

### close

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public void close ()

Close this Bluetooth GATT client.

Application should call this method as early as possible after it is done with this GATT client.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

### connect

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean connect ()

Connect back to remote device.

This method is used to re-connect to a remote device after the connection has been dropped. If the device is not in range, the re-connection will be triggered once the device is back in range.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Returns |
| --- |
| `boolean` | true, if the connection attempt was initiated successfully
 |

### disconnect

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public void disconnect ()

Disconnects an established connection, or cancels a connection attempt currently in progress.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

### discoverServices

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean discoverServices ()

Discovers services offered by a remote device as well as their characteristics and descriptors.

This is an asynchronous operation. Once service discovery is completed, the `[BluetoothGattCallback.onServicesDiscovered](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onServicesDiscovered\(android.bluetooth.BluetoothGatt,%20int\))` callback is triggered. If the discovery was successful, the remote services can be retrieved using the `[getServices()](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#getServices\(\))` function.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Returns |
| --- |
| `boolean` | true, if the remote service discovery has been started
 |

### executeReliableWrite

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean executeReliableWrite ()

Executes a reliable write transaction for a given remote device.

This function will commit all queued up characteristic write operations for a given remote device.

A `[BluetoothGattCallback.onReliableWriteCompleted](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onReliableWriteCompleted\(android.bluetooth.BluetoothGatt,%20int\))` callback is invoked to indicate whether the transaction has been executed correctly.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Returns |
| --- |
| `boolean` | true, if the request to execute the transaction has been sent
 |

### getConnectedDevices

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public [List](https://developer.android.com/reference/java/util/List)<[BluetoothDevice](https://developer.android.com/reference/android/bluetooth/BluetoothDevice)\> getConnectedDevices ()

**This method is deprecated.**
Not supported - please use `[BluetoothManager.getConnectedDevices(int)](https://developer.android.com/reference/android/bluetooth/BluetoothManager#getConnectedDevices\(int\))` with `[BluetoothProfile.GATT](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#GATT)` as argument

Get connected devices for this specific profile.

Return the set of devices which are in state `[STATE_CONNECTED](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_CONNECTED)`

| Returns |
| --- |
| `[List](https://developer.android.com/reference/java/util/List)<[BluetoothDevice](https://developer.android.com/reference/android/bluetooth/BluetoothDevice)>` | List of devices. The list will be empty on error.
 |

| Throws |
| --- |
| `[UnsupportedOperationException](https://developer.android.com/reference/java/lang/UnsupportedOperationException)` | on every call |

### getConnectionState

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public int getConnectionState ([BluetoothDevice](https://developer.android.com/reference/android/bluetooth/BluetoothDevice) device)

**This method is deprecated.**
Not supported - please use `[BluetoothManager.getConnectedDevices(int)](https://developer.android.com/reference/android/bluetooth/BluetoothManager#getConnectedDevices\(int\))` with `[BluetoothProfile.GATT](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#GATT)` as argument

Get the current connection state of the profile

| Parameters |
| --- |
| `device` | `BluetoothDevice`: Remote bluetooth device.
 |

| Returns |
| --- |
| `int` | State of the profile connection. One of `[STATE_CONNECTED](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_CONNECTED)`, `[STATE_CONNECTING](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_CONNECTING)`, `[STATE_DISCONNECTED](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_DISCONNECTED)`, `[STATE_DISCONNECTING](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_DISCONNECTING)`
Value is one of the following:
-   `[STATE_DISCONNECTED](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_DISCONNECTED)`
-   `[STATE_CONNECTING](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_CONNECTING)`
-   `[STATE_CONNECTED](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_CONNECTED)`
-   `[STATE_DISCONNECTING](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_DISCONNECTING)`

 |

| Throws |
| --- |
| `[UnsupportedOperationException](https://developer.android.com/reference/java/lang/UnsupportedOperationException)` | on every call |

### getDevice

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public [BluetoothDevice](https://developer.android.com/reference/android/bluetooth/BluetoothDevice) getDevice ()

Return the remote bluetooth device this GATT client targets to

| Returns |
| --- |
| `[BluetoothDevice](https://developer.android.com/reference/android/bluetooth/BluetoothDevice)` | remote bluetooth device
 |

### getDevicesMatchingConnectionStates

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public [List](https://developer.android.com/reference/java/util/List)<[BluetoothDevice](https://developer.android.com/reference/android/bluetooth/BluetoothDevice)\> getDevicesMatchingConnectionStates (int\[\] states)

**This method is deprecated.**
Not supported - please use `[BluetoothManager.getDevicesMatchingConnectionStates(int,int[])](https://developer.android.com/reference/android/bluetooth/BluetoothManager#getDevicesMatchingConnectionStates\(int,%20int[]\))` with `[BluetoothProfile.GATT](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#GATT)` as first argument

Get a list of devices that match any of the given connection states.

If none of the devices match any of the given states, an empty list will be returned.

| Parameters |
| --- |
| `states` | `int`: Array of states. States can be one of `[BluetoothProfile.STATE_CONNECTED](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_CONNECTED)`, `[BluetoothProfile.STATE_CONNECTING](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_CONNECTING)`, `[BluetoothProfile.STATE_DISCONNECTED](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_DISCONNECTED)`, `[BluetoothProfile.STATE_DISCONNECTING](https://developer.android.com/reference/android/bluetooth/BluetoothProfile#STATE_DISCONNECTING)`,
 |

| Returns |
| --- |
| `[List](https://developer.android.com/reference/java/util/List)<[BluetoothDevice](https://developer.android.com/reference/android/bluetooth/BluetoothDevice)>` | List of devices. The list will be empty on error.
 |

| Throws |
| --- |
| `[UnsupportedOperationException](https://developer.android.com/reference/java/lang/UnsupportedOperationException)` | on every call |

### getService

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public [BluetoothGattService](https://developer.android.com/reference/android/bluetooth/BluetoothGattService) getService ([UUID](https://developer.android.com/reference/java/util/UUID) uuid)

Returns a `[BluetoothGattService](https://developer.android.com/reference/android/bluetooth/BluetoothGattService)`, if the requested UUID is supported by the remote device.

This function requires that service discovery has been completed for the given device.

If multiple instances of the same service (as identified by UUID) exist, the first instance of the service is returned.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.

| Parameters |
| --- |
| `uuid` | `UUID`: UUID of the requested service
 |

| Returns |
| --- |
| `[BluetoothGattService](https://developer.android.com/reference/android/bluetooth/BluetoothGattService)` | BluetoothGattService if supported, or null if the requested service is not offered by the remote device.
 |

### getServices

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public [List](https://developer.android.com/reference/java/util/List)<[BluetoothGattService](https://developer.android.com/reference/android/bluetooth/BluetoothGattService)\> getServices ()

Returns a list of GATT services offered by the remote device.

This function requires that service discovery has been completed for the given device.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.

| Returns |
| --- |
| `[List](https://developer.android.com/reference/java/util/List)<[BluetoothGattService](https://developer.android.com/reference/android/bluetooth/BluetoothGattService)>` | List of services on the remote device. Returns an empty list if service discovery has not yet been performed.
 |

### readCharacteristic

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean readCharacteristic ([BluetoothGattCharacteristic](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic) characteristic)

Reads the requested characteristic from the associated remote device.

This is an asynchronous operation. The result of the read operation is reported by the `[BluetoothGattCallback.onCharacteristicRead(BluetoothGatt,BluetoothGattCharacteristic,byte[],int)](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onCharacteristicRead\(android.bluetooth.BluetoothGatt,%20android.bluetooth.BluetoothGattCharacteristic,%20byte[],%20int\))` callback.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Parameters |
| --- |
| `characteristic` | `BluetoothGattCharacteristic`: Characteristic to read from the remote device
 |

| Returns |
| --- |
| `boolean` | true, if the read operation was initiated successfully
 |

### readDescriptor

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean readDescriptor ([BluetoothGattDescriptor](https://developer.android.com/reference/android/bluetooth/BluetoothGattDescriptor) descriptor)

Reads the value for a given descriptor from the associated remote device.

Once the read operation has been completed, the `[BluetoothGattCallback.onDescriptorRead](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onDescriptorRead\(android.bluetooth.BluetoothGatt,%20android.bluetooth.BluetoothGattDescriptor,%20int\))` callback is triggered, signaling the result of the operation.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Parameters |
| --- |
| `descriptor` | `BluetoothGattDescriptor`: Descriptor value to read from the remote device
 |

| Returns |
| --- |
| `boolean` | true, if the read operation was initiated successfully
 |

### readPhy

Added in [API level 26](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public void readPhy ()

Read the current transmitter PHY and receiver PHY of the connection. The values are returned in `[BluetoothGattCallback.onPhyRead](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onPhyRead\(android.bluetooth.BluetoothGatt,%20int,%20int,%20int\))`
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

### readRemoteRssi

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean readRemoteRssi ()

Read the RSSI for a connected remote device.

The `[BluetoothGattCallback.onReadRemoteRssi](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onReadRemoteRssi\(android.bluetooth.BluetoothGatt,%20int,%20int\))` callback will be invoked when the RSSI value has been read.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Returns |
| --- |
| `boolean` | true, if the RSSI value has been requested successfully
 |

### requestConnectionPriority

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean requestConnectionPriority (int connectionPriority)

Request a connection parameter update.

This function will send a connection parameter update request to the remote device.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Parameters |
| --- |
| `connectionPriority` | `int`: Request a specific connection priority. Must be one of `[BluetoothGatt.CONNECTION_PRIORITY_BALANCED](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#CONNECTION_PRIORITY_BALANCED)`, `[BluetoothGatt.CONNECTION_PRIORITY_HIGH](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#CONNECTION_PRIORITY_HIGH)` `[BluetoothGatt.CONNECTION_PRIORITY_LOW_POWER](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#CONNECTION_PRIORITY_LOW_POWER)`, or `[BluetoothGatt.CONNECTION_PRIORITY_DCK](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#CONNECTION_PRIORITY_DCK)`.
 |

| Returns |
| --- |
| `boolean` |
 |

| Throws |
| --- |
| `[IllegalArgumentException](https://developer.android.com/reference/java/lang/IllegalArgumentException)` | If the parameters are outside of their specified range. |

### requestMtu

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean requestMtu (int mtu)

Request an MTU size used for a given connection. Please note that starting from Android 14, the Android Bluetooth stack requests the BLE ATT MTU to 517 bytes when the first GATT client requests an MTU, and disregards all subsequent MTU requests. Check out [MTU is set to 517 for the first GATT client requesting an MTU](https://developer.android.com/about/versions/14/behavior-changes-all#mtu-set-to-517) for more information.

When performing a write request operation (write without response), the data sent is truncated to the MTU size. This function may be used to request a larger MTU size to be able to send more data at once.

A `[BluetoothGattCallback.onMtuChanged](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onMtuChanged\(android.bluetooth.BluetoothGatt,%20int,%20int\))` callback will indicate whether this operation was successful.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Parameters |
| --- |
| `mtu` | `int`
 |

| Returns |
| --- |
| `boolean` | true, if the new MTU value has been requested successfully
 |

### requestSubrateMode

Added in [version 36.1](https://developer.android.com/topic/libraries/support-library/revisions)

public int requestSubrateMode (int subrateMode)

Request LE subrate mode.

Configure/Request subrating with this API, sending a subrate request to the remote device based on Subrate Mode. This function should be used in conjunction with `[ERROR(/requestConnectionPriority)](https://developer.android.com/)` to manage link latency and power consumption effectively.

This method requires the calling app to have the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission. Additionally, an app must either have the `[Manifest.permission.BLUETOOTH_PRIVILEGED](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_PRIVILEGED)` or be associated with the Companion Device manager (see `[android.companion.CompanionDeviceManager.associate(AssociationRequest,android.companion.CompanionDeviceManager.Callback,Handler)](https://developer.android.com/reference/android/companion/CompanionDeviceManager#associate\(android.companion.AssociationRequest,%20android.companion.CompanionDeviceManager.Callback,%20android.os.Handler\))`).
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.

| Parameters |
| --- |
| `subrateMode` | `int`: Request a specific subrate mode.
Value is one of the following:
-   `[SUBRATE_MODE_OFF](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#SUBRATE_MODE_OFF)`
-   `[SUBRATE_MODE_LOW](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#SUBRATE_MODE_LOW)`
-   `[SUBRATE_MODE_BALANCED](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#SUBRATE_MODE_BALANCED)`
-   `[SUBRATE_MODE_HIGH](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#SUBRATE_MODE_HIGH)`

 |

| Returns |
| --- |
| `int` | true, if the request is send to the Bluetooth stack.
Value is one of the following:
-   `[BluetoothStatusCodes.SUCCESS](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#SUCCESS)`
-   `[BluetoothStatusCodes.ERROR_BLUETOOTH_NOT_ENABLED](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_BLUETOOTH_NOT_ENABLED)`
-   `[BluetoothStatusCodes.ERROR_BLUETOOTH_NOT_ALLOWED](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_BLUETOOTH_NOT_ALLOWED)`
-   `[BluetoothStatusCodes.ERROR_MISSING_BLUETOOTH_CONNECT_PERMISSION](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_MISSING_BLUETOOTH_CONNECT_PERMISSION)`
-   `[BluetoothStatusCodes.ERROR_DEVICE_NOT_BONDED](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_DEVICE_NOT_BONDED)`
-   `[BluetoothStatusCodes.FEATURE_NOT_SUPPORTED](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#FEATURE_NOT_SUPPORTED)`
-   `[BluetoothStatusCodes.ERROR_UNKNOWN](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_UNKNOWN)`

 |

| Throws |
| --- |
| `[IllegalArgumentException](https://developer.android.com/reference/java/lang/IllegalArgumentException)` | If the parameters are outside of their specified range. |

### setCharacteristicNotification

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean setCharacteristicNotification ([BluetoothGattCharacteristic](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic) characteristic,
                boolean enable)

Enable or disable notifications/indications for a given characteristic.

Once notifications are enabled for a characteristic, a `[BluetoothGattCallback.onCharacteristicChanged(BluetoothGatt,BluetoothGattCharacteristic,byte[])](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onCharacteristicChanged\(android.bluetooth.BluetoothGatt,%20android.bluetooth.BluetoothGattCharacteristic,%20byte[]\))` callback will be triggered if the remote device indicates that the given characteristic has changed.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Parameters |
| --- |
| `characteristic` | `BluetoothGattCharacteristic`: The characteristic for which to enable notifications
 |
| `enable` | `boolean`: Set to true to enable notifications/indications

 |

| Returns |
| --- |
| `boolean` | true, if the requested notification status was set successfully
 |

### setPreferredPhy

Added in [API level 26](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public void setPreferredPhy (int txPhy,
                int rxPhy,
                int phyOptions)

Set the preferred connection PHY for this app. Please note that this is just a recommendation, whether the PHY change will happen depends on other applications preferences, local and remote controller capabilities. Controller can override these settings.

`[BluetoothGattCallback.onPhyUpdate](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onPhyUpdate\(android.bluetooth.BluetoothGatt,%20int,%20int,%20int\))` will be triggered as a result of this call, even if no PHY change happens. It is also triggered when remote device updates the PHY.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Parameters |
| --- |
| `txPhy` | `int`: preferred transmitter PHY.
Value is either `0` or a combination of the following:
-   `[BluetoothDevice.PHY_LE_1M_MASK](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#PHY_LE_1M_MASK)`
-   `[BluetoothDevice.PHY_LE_2M_MASK](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#PHY_LE_2M_MASK)`
-   `[BluetoothDevice.PHY_LE_CODED_MASK](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#PHY_LE_CODED_MASK)`
-   `[BluetoothDevice.PHY_LE_HDT_MASK](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#PHY_LE_HDT_MASK)`

 |
| `rxPhy` | `int`: preferred receiver PHY.
Value is either `0` or a combination of the following:

-   `[BluetoothDevice.PHY_LE_1M_MASK](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#PHY_LE_1M_MASK)`
-   `[BluetoothDevice.PHY_LE_2M_MASK](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#PHY_LE_2M_MASK)`
-   `[BluetoothDevice.PHY_LE_CODED_MASK](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#PHY_LE_CODED_MASK)`
-   `[BluetoothDevice.PHY_LE_HDT_MASK](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#PHY_LE_HDT_MASK)`

 |
| `phyOptions` | `int`: preferred coding to use when transmitting on the LE Coded PHY. Can be one of `[BluetoothDevice.PHY_OPTION_NO_PREFERRED](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#PHY_OPTION_NO_PREFERRED)`, `[BluetoothDevice.PHY_OPTION_S2](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#PHY_OPTION_S2)` or `[BluetoothDevice.PHY_OPTION_S8](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#PHY_OPTION_S8)`.

 |

### writeCharacteristic

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)
Deprecated in [API level 33](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean writeCharacteristic ([BluetoothGattCharacteristic](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic) characteristic)

**This method was deprecated in API level 33.**
Use `[BluetoothGatt.writeCharacteristic(BluetoothGattCharacteristic,byte[],int)](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#writeCharacteristic\(android.bluetooth.BluetoothGattCharacteristic,%20byte[],%20int\))` as this is not memory safe because it relies on a `[BluetoothGattCharacteristic](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic)` object whose underlying fields are subject to change outside this method.

Writes a given characteristic and its values to the associated remote device.

Once the write operation has been completed, the `[BluetoothGattCallback.onCharacteristicWrite](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onCharacteristicWrite\(android.bluetooth.BluetoothGatt,%20android.bluetooth.BluetoothGattCharacteristic,%20int\))` callback is invoked, reporting the result of the operation.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Parameters |
| --- |
| `characteristic` | `BluetoothGattCharacteristic`: Characteristic to write on the remote device
 |

| Returns |
| --- |
| `boolean` | true, if the write operation was initiated successfully
 |

| Throws |
| --- |
| `[IllegalArgumentException](https://developer.android.com/reference/java/lang/IllegalArgumentException)` | if characteristic or its value are null |

### writeCharacteristic

Added in [API level 33](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public int writeCharacteristic ([BluetoothGattCharacteristic](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic) characteristic,
                byte\[\] value,
                int writeType)

Writes a given characteristic and its values to the associated remote device.

Once the write operation has been completed, the `[BluetoothGattCallback.onCharacteristicWrite](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onCharacteristicWrite\(android.bluetooth.BluetoothGatt,%20android.bluetooth.BluetoothGattCharacteristic,%20int\))` callback is invoked, reporting the result of the operation.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Parameters |
| --- |
| `characteristic` | `BluetoothGattCharacteristic`: Characteristic to write on the remote device.
This value cannot be `null`.
 |
| `value` | `byte`: This value cannot be `null`.

 |
| `writeType` | `int`: Value is one of the following:

-   `[BluetoothGattCharacteristic.WRITE_TYPE_DEFAULT](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic#WRITE_TYPE_DEFAULT)`
-   `[BluetoothGattCharacteristic.WRITE_TYPE_NO_RESPONSE](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic#WRITE_TYPE_NO_RESPONSE)`
-   `[BluetoothGattCharacteristic.WRITE_TYPE_SIGNED](https://developer.android.com/reference/android/bluetooth/BluetoothGattCharacteristic#WRITE_TYPE_SIGNED)`

 |

| Returns |
| --- |
| `int` | whether the characteristic was successfully written to.
Value is one of the following:
-   `[BluetoothStatusCodes.SUCCESS](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#SUCCESS)`
-   `[BluetoothStatusCodes.ERROR_MISSING_BLUETOOTH_CONNECT_PERMISSION](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_MISSING_BLUETOOTH_CONNECT_PERMISSION)`
-   `[BluetoothStatusCodes.ERROR_PROFILE_SERVICE_NOT_BOUND](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_PROFILE_SERVICE_NOT_BOUND)`
-   `[BluetoothStatusCodes.ERROR_GATT_WRITE_NOT_ALLOWED](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_GATT_WRITE_NOT_ALLOWED)`
-   `[BluetoothStatusCodes.ERROR_GATT_WRITE_REQUEST_BUSY](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_GATT_WRITE_REQUEST_BUSY)`
-   `[BluetoothStatusCodes.ERROR_UNKNOWN](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_UNKNOWN)`

 |

| Throws |
| --- |
| `[IllegalArgumentException](https://developer.android.com/reference/java/lang/IllegalArgumentException)` | if characteristic or value are null |

### writeDescriptor

Added in [API level 18](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)
Deprecated in [API level 33](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean writeDescriptor ([BluetoothGattDescriptor](https://developer.android.com/reference/android/bluetooth/BluetoothGattDescriptor) descriptor)

**This method was deprecated in API level 33.**
Use `[BluetoothGatt.writeDescriptor(BluetoothGattDescriptor,byte[])](https://developer.android.com/reference/android/bluetooth/BluetoothGatt#writeDescriptor\(android.bluetooth.BluetoothGattDescriptor,%20byte[]\))` as this is not memory safe because it relies on a `[BluetoothGattDescriptor](https://developer.android.com/reference/android/bluetooth/BluetoothGattDescriptor)` object whose underlying fields are subject to change outside this method.

Write the value of a given descriptor to the associated remote device.

A `[BluetoothGattCallback.onDescriptorWrite](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onDescriptorWrite\(android.bluetooth.BluetoothGatt,%20android.bluetooth.BluetoothGattDescriptor,%20int\))` callback is triggered to report the result of the write operation.
For apps targeting `[Build.VERSION_CODES.R](https://developer.android.com/reference/android/os/Build.VERSION_CODES#R)` or lower, this requires the `[Manifest.permission.BLUETOOTH](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH)` permission which can be gained with a simple `<uses-permission>` manifest tag.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Parameters |
| --- |
| `descriptor` | `BluetoothGattDescriptor`: Descriptor to write to the associated remote device
 |

| Returns |
| --- |
| `boolean` | true, if the write operation was initiated successfully
 |

| Throws |
| --- |
| `[IllegalArgumentException](https://developer.android.com/reference/java/lang/IllegalArgumentException)` | if descriptor or its value are null |

### writeDescriptor

Added in [API level 33](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public int writeDescriptor ([BluetoothGattDescriptor](https://developer.android.com/reference/android/bluetooth/BluetoothGattDescriptor) descriptor,
                byte\[\] value)

Write the value of a given descriptor to the associated remote device.

A `[BluetoothGattCallback.onDescriptorWrite](https://developer.android.com/reference/android/bluetooth/BluetoothGattCallback#onDescriptorWrite\(android.bluetooth.BluetoothGatt,%20android.bluetooth.BluetoothGattDescriptor,%20int\))` callback is triggered to report the result of the write operation.
For apps targeting `[Build.VERSION_CODES.S](https://developer.android.com/reference/android/os/Build.VERSION_CODES#S)` or or higher, this requires the `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)` permission which can be gained with `[android.app.Activity.requestPermissions(String[],int)](https://developer.android.com/reference/android/app/Activity#requestPermissions\(java.lang.String[],%20int\))`.
Requires `[Manifest.permission.BLUETOOTH_CONNECT](https://developer.android.com/reference/android/Manifest.permission#BLUETOOTH_CONNECT)`

| Parameters |
| --- |
| `descriptor` | `BluetoothGattDescriptor`: Descriptor to write to the associated remote device.
This value cannot be `null`.
 |
| `value` | `byte`: This value cannot be `null`.

 |

| Returns |
| --- |
| `int` | true, if the write operation was initiated successfully.
Value is one of the following:
-   `[BluetoothStatusCodes.SUCCESS](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#SUCCESS)`
-   `[BluetoothStatusCodes.ERROR_MISSING_BLUETOOTH_CONNECT_PERMISSION](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_MISSING_BLUETOOTH_CONNECT_PERMISSION)`
-   `[BluetoothStatusCodes.ERROR_PROFILE_SERVICE_NOT_BOUND](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_PROFILE_SERVICE_NOT_BOUND)`
-   `[BluetoothStatusCodes.ERROR_GATT_WRITE_NOT_ALLOWED](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_GATT_WRITE_NOT_ALLOWED)`
-   `[BluetoothStatusCodes.ERROR_GATT_WRITE_REQUEST_BUSY](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_GATT_WRITE_REQUEST_BUSY)`
-   `[BluetoothStatusCodes.ERROR_UNKNOWN](https://developer.android.com/reference/android/bluetooth/BluetoothStatusCodes#ERROR_UNKNOWN)`

 |

| Throws |
| --- |
| `[IllegalArgumentException](https://developer.android.com/reference/java/lang/IllegalArgumentException)` | if descriptor or value are null |