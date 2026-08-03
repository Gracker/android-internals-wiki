# ScanSettings  |  API reference
> 原文链接: https://developer.android.com/reference/android/bluetooth/le/ScanSettings

---

-   [Android Developers](https://developer.android.com/)
-   [Develop](https://developer.android.com/develop)
-   [API reference](https://developer.android.com/reference)

-   On this page
-   [Summary](#summary)
    -   [Nested classes](#nested-classes)
    -   [Constants](#constants)
    -   [Inherited constants](#inherited-constants)
    -   [Fields](#fields)
    -   [Public methods](#public-methods)
    -   [Inherited methods](#inherited-methods)
-   [Constants](#constants_1)
    -   [AUTO\_BATCH\_MIN\_REPORT\_DELAY\_MILLIS](#AUTO_BATCH_MIN_REPORT_DELAY_MILLIS)
    -   [CALLBACK\_TYPE\_ALL\_MATCHES](#CALLBACK_TYPE_ALL_MATCHES)
    -   [CALLBACK\_TYPE\_ALL\_MATCHES\_AUTO\_BATCH](#CALLBACK_TYPE_ALL_MATCHES_AUTO_BATCH)
    -   [CALLBACK\_TYPE\_FIRST\_MATCH](#CALLBACK_TYPE_FIRST_MATCH)
    -   [CALLBACK\_TYPE\_MATCH\_LOST](#CALLBACK_TYPE_MATCH_LOST)
    -   [MATCH\_MODE\_AGGRESSIVE](#MATCH_MODE_AGGRESSIVE)
    -   [MATCH\_MODE\_STICKY](#MATCH_MODE_STICKY)
    -   [MATCH\_NUM\_FEW\_ADVERTISEMENT](#MATCH_NUM_FEW_ADVERTISEMENT)
    -   [MATCH\_NUM\_MAX\_ADVERTISEMENT](#MATCH_NUM_MAX_ADVERTISEMENT)
    -   [MATCH\_NUM\_ONE\_ADVERTISEMENT](#MATCH_NUM_ONE_ADVERTISEMENT)
    -   [PHY\_LE\_ALL\_SUPPORTED](#PHY_LE_ALL_SUPPORTED)
    -   [SCAN\_MODE\_BALANCED](#SCAN_MODE_BALANCED)
    -   [SCAN\_MODE\_LOW\_LATENCY](#SCAN_MODE_LOW_LATENCY)
    -   [SCAN\_MODE\_LOW\_POWER](#SCAN_MODE_LOW_POWER)
    -   [SCAN\_MODE\_OPPORTUNISTIC](#SCAN_MODE_OPPORTUNISTIC)
    -   [SCAN\_TYPE\_ACTIVE](#SCAN_TYPE_ACTIVE)
    -   [SCAN\_TYPE\_PASSIVE](#SCAN_TYPE_PASSIVE)
    -   [SCAN\_TYPE\_UNKNOWN](#SCAN_TYPE_UNKNOWN)
-   [Fields](#fields_1)
    -   [CREATOR](#CREATOR)
-   [Public methods](#public-methods_1)
    -   [describeContents](#describeContents\(\))
    -   [getCallbackType](#getCallbackType\(\))
    -   [getLegacy](#getLegacy\(\))
    -   [getPhy](#getPhy\(\))
    -   [getReportDelayMillis](#getReportDelayMillis\(\))
    -   [getRssiThreshold](#getRssiThreshold\(\))
    -   [getScanMode](#getScanMode\(\))
    -   [getScanResultType](#getScanResultType\(\))
    -   [getScanType](#getScanType\(\))
    -   [writeToParcel](#writeToParcel\(android.os.Parcel,%20int\))

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

Summary: [Nested Classes](#nestedclasses) | [Constants](#constants) | [Inherited Constants](#inhconstants) | [Fields](#lfields) | [Methods](#pubmethods) | [Inherited Methods](#inhmethods)

# ScanSettings Stay organized with collections Save and categorize content based on your preferences.

* * *

[Kotlin](https://developer.android.com/reference/kotlin/android/bluetooth/le/ScanSettings) |Java

`public final class ScanSettings`
`extends [Object](https://developer.android.com/reference/java/lang/Object)` `implements [Parcelable](https://developer.android.com/reference/android/os/Parcelable)`

<table class="jd-inheritance-table"><tbody><tr><td colspan="2" class="jd-inheritance-class-cell"><a href="https://developer.android.com/reference/java/lang/Object">java.lang.Object</a></td></tr><tr><td class="jd-inheritance-space">&nbsp;&nbsp;&nbsp;↳</td><td colspan="1" class="jd-inheritance-class-cell">android.bluetooth.le.ScanSettings</td></tr></tbody></table>

* * *

Bluetooth LE scan settings are passed to `[BluetoothLeScanner.startScan](https://developer.android.com/reference/android/bluetooth/le/BluetoothLeScanner#startScan\(android.bluetooth.le.ScanCallback\))` to define the parameters for the scan.

## Summary

|
### Nested classes

 |
| --- |
| `class` | `[ScanSettings.Builder](https://developer.android.com/reference/android/bluetooth/le/ScanSettings.Builder)`

Builder for `[ScanSettings](https://developer.android.com/reference/android/bluetooth/le/ScanSettings)`.

 |

|
### Constants

 |
| --- |
| `long` | `[AUTO_BATCH_MIN_REPORT_DELAY_MILLIS](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#AUTO_BATCH_MIN_REPORT_DELAY_MILLIS)`

Minimum report delay for `[ScanSettings.CALLBACK_TYPE_ALL_MATCHES_AUTO_BATCH](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#CALLBACK_TYPE_ALL_MATCHES_AUTO_BATCH)`.

 |
| `int` | `[CALLBACK_TYPE_ALL_MATCHES](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#CALLBACK_TYPE_ALL_MATCHES)`

Trigger a callback for every Bluetooth advertisement found that matches the filter criteria.

 |
| `int` | `[CALLBACK_TYPE_ALL_MATCHES_AUTO_BATCH](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#CALLBACK_TYPE_ALL_MATCHES_AUTO_BATCH)`

A result callback for every Bluetooth advertisement found that matches the filter criteria is only triggered when screen is turned on.

 |
| `int` | `[CALLBACK_TYPE_FIRST_MATCH](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#CALLBACK_TYPE_FIRST_MATCH)`

A result callback is only triggered for the first advertisement packet received that matches the filter criteria.

 |
| `int` | `[CALLBACK_TYPE_MATCH_LOST](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#CALLBACK_TYPE_MATCH_LOST)`

Receive a callback when advertisements are no longer received from a device that has been previously reported by a first match callback.

 |
| `int` | `[MATCH_MODE_AGGRESSIVE](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#MATCH_MODE_AGGRESSIVE)`

In Aggressive mode, hw will determine a match sooner even with feeble signal strength and few number of sightings/match in a duration.

 |
| `int` | `[MATCH_MODE_STICKY](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#MATCH_MODE_STICKY)`

For sticky mode, higher threshold of signal strength and sightings is required before reporting by hw.

 |
| `int` | `[MATCH_NUM_FEW_ADVERTISEMENT](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#MATCH_NUM_FEW_ADVERTISEMENT)`

Match few advertisement per filter, depends on current capability and availability of the resources in hw.

 |
| `int` | `[MATCH_NUM_MAX_ADVERTISEMENT](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#MATCH_NUM_MAX_ADVERTISEMENT)`

Match as many advertisement per filter as hw could allow, depends on current capability and availability of the resources in hw.

 |
| `int` | `[MATCH_NUM_ONE_ADVERTISEMENT](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#MATCH_NUM_ONE_ADVERTISEMENT)`

Determines how many advertisements to match per filter, as this is scarce hw resource.

 |
| `int` | `[PHY_LE_ALL_SUPPORTED](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#PHY_LE_ALL_SUPPORTED)`

Use all supported PHYs for scanning.

 |
| `int` | `[SCAN_MODE_BALANCED](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#SCAN_MODE_BALANCED)`

Perform Bluetooth LE scan in balanced power mode.

 |
| `int` | `[SCAN_MODE_LOW_LATENCY](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#SCAN_MODE_LOW_LATENCY)`

Scan using highest duty cycle.

 |
| `int` | `[SCAN_MODE_LOW_POWER](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#SCAN_MODE_LOW_POWER)`

Perform Bluetooth LE scan in low power mode.

 |
| `int` | `[SCAN_MODE_OPPORTUNISTIC](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#SCAN_MODE_OPPORTUNISTIC)`

A special Bluetooth LE scan mode.

 |
| `int` | `[SCAN_TYPE_ACTIVE](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#SCAN_TYPE_ACTIVE)`

Does active scanning, scan results are delivered upon scan responses arrive.

 |
| `int` | `[SCAN_TYPE_PASSIVE](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#SCAN_TYPE_PASSIVE)`

Does passive scanning, scan responses are ignored.

 |
| `int` | `[SCAN_TYPE_UNKNOWN](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#SCAN_TYPE_UNKNOWN)`

Scan type is unknown.

 |

|
### Inherited constants

 |
| --- |
| From interface `[android.os.Parcelable](https://developer.android.com/reference/android/os/Parcelable)`

<table class="responsive"><tbody><tr data-version-added="1"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/os/Parcelable#CONTENTS_FILE_DESCRIPTOR">CONTENTS_FILE_DESCRIPTOR</a></code><p>Descriptor bit used with <code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/os/Parcelable#describeContents()">describeContents()</a></code>: indicates that the Parcelable object's flattened representation includes a file descriptor.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/os/Parcelable#PARCELABLE_WRITE_RETURN_VALUE">PARCELABLE_WRITE_RETURN_VALUE</a></code><p>Flag for use with <code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/os/Parcelable#writeToParcel(android.os.Parcel,%20int)">writeToParcel(Parcel, int)</a></code>: the object being written is a return value, that is the result of a function such as "<code translate="no" dir="ltr">Parcelable someFunction()</code>", "<code translate="no" dir="ltr">void someFunction(out Parcelable)</code>", or "<code translate="no" dir="ltr">void someFunction(inout Parcelable)</code>".</p></td></tr></tbody></table>

 |

|
### Fields

 |
| --- |
| `public static final [Creator](https://developer.android.com/reference/android/os/Parcelable.Creator)<[ScanSettings](https://developer.android.com/reference/android/bluetooth/le/ScanSettings)>` | `[CREATOR](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#CREATOR)`

 |

|
### Public methods

 |
| --- |
| `int` | `[describeContents](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#describeContents\(\))()`

Describe the kinds of special objects contained in this Parcelable instance's marshaled representation.

 |
| `int` | `[getCallbackType](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#getCallbackType\(\))()` |
| `boolean` | `[getLegacy](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#getLegacy\(\))()`

Returns whether only legacy advertisements will be returned.

 |
| `int` | `[getPhy](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#getPhy\(\))()`

Returns the physical layer used during a scan.

 |
| `long` | `[getReportDelayMillis](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#getReportDelayMillis\(\))()`

Returns report delay timestamp based on the device clock.

 |
| `int` | `[getRssiThreshold](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#getRssiThreshold\(\))()` |
| `int` | `[getScanMode](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#getScanMode\(\))()` |
| `int` | `[getScanResultType](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#getScanResultType\(\))()` |
| `int` | `[getScanType](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#getScanType\(\))()` |
| `void` | `[writeToParcel](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#writeToParcel\(android.os.Parcel,%20int\))([Parcel](https://developer.android.com/reference/android/os/Parcel) dest, int flags)`

Flatten this object in to a Parcel.

 |

|
### Inherited methods

 |
| --- |
| From class `[java.lang.Object](https://developer.android.com/reference/java/lang/Object)`

<table class="responsive"><tbody><tr data-version-added="1"><td><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object">Object</a></code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#clone()">clone</a>()</code><p>Creates and returns a copy of this object.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">boolean</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#equals(java.lang.Object)">equals</a>(<a href="https://developer.android.com/reference/java/lang/Object">Object</a> obj)</code><p>Indicates whether some other object is "equal to" this one.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#finalize()">finalize</a>()</code><p>Called by the garbage collector on an object when garbage collection determines that there are no more references to the object.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final <a href="https://developer.android.com/reference/java/lang/Class">Class</a>&lt;?&gt;</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#getClass()">getClass</a>()</code><p>Returns the runtime class of this <code translate="no" dir="ltr">Object</code>.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#hashCode()">hashCode</a>()</code><p>Returns a hash code value for the object.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#notify()">notify</a>()</code><p>Wakes up a single thread that is waiting on this object's monitor.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#notifyAll()">notifyAll</a>()</code><p>Wakes up all threads that are waiting on this object's monitor.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/String">String</a></code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#toString()">toString</a>()</code><p>Returns a string representation of the object.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#wait(long,%20int)">wait</a>(long timeoutMillis, int nanos)</code><p>Causes the current thread to wait until it is awakened, typically by being <em>notified</em> or <em>interrupted</em>, or until a certain amount of real time has elapsed.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#wait(long)">wait</a>(long timeoutMillis)</code><p>Causes the current thread to wait until it is awakened, typically by being <em>notified</em> or <em>interrupted</em>, or until a certain amount of real time has elapsed.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#wait()">wait</a>()</code><p>Causes the current thread to wait until it is awakened, typically by being <em>notified</em> or <em>interrupted</em>.</p></td></tr></tbody></table>

 |
| From interface `[android.os.Parcelable](https://developer.android.com/reference/android/os/Parcelable)`

<table class="responsive"><tbody><tr data-version-added="1"><td><code translate="no" dir="ltr">abstract int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/os/Parcelable#describeContents()">describeContents</a>()</code><p>Describe the kinds of special objects contained in this Parcelable instance's marshaled representation.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">abstract void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/android/os/Parcelable#writeToParcel(android.os.Parcel,%20int)">writeToParcel</a>(<a href="https://developer.android.com/reference/android/os/Parcel">Parcel</a> dest, int flags)</code><p>Flatten this object in to a Parcel.</p></td></tr></tbody></table>

 |

## Constants

### AUTO\_BATCH\_MIN\_REPORT\_DELAY\_MILLIS

Added in [API level 34](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final long AUTO\_BATCH\_MIN\_REPORT\_DELAY\_MILLIS

Minimum report delay for `[ScanSettings.CALLBACK_TYPE_ALL_MATCHES_AUTO_BATCH](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#CALLBACK_TYPE_ALL_MATCHES_AUTO_BATCH)`.

Constant Value: 600000 (0x00000000000927c0)

### CALLBACK\_TYPE\_ALL\_MATCHES

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int CALLBACK\_TYPE\_ALL\_MATCHES

Trigger a callback for every Bluetooth advertisement found that matches the filter criteria. If no filter is active, all advertisement packets are reported.

Constant Value: 1 (0x00000001)

### CALLBACK\_TYPE\_ALL\_MATCHES\_AUTO\_BATCH

Added in [API level 34](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int CALLBACK\_TYPE\_ALL\_MATCHES\_AUTO\_BATCH

A result callback for every Bluetooth advertisement found that matches the filter criteria is only triggered when screen is turned on. While the screen is turned off, the advertisements are batched and the batched result callbacks are triggered every report delay. When the batch scan with this callback type is activated, the batched result callbacks are also triggered while turning on screen or disabling the scan. This callback type must be used with a report delay of `[ScanSettings.AUTO_BATCH_MIN_REPORT_DELAY_MILLIS](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#AUTO_BATCH_MIN_REPORT_DELAY_MILLIS)` or greater.

Constant Value: 8 (0x00000008)

### CALLBACK\_TYPE\_FIRST\_MATCH

Added in [API level 23](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int CALLBACK\_TYPE\_FIRST\_MATCH

A result callback is only triggered for the first advertisement packet received that matches the filter criteria.

Constant Value: 2 (0x00000002)

### CALLBACK\_TYPE\_MATCH\_LOST

Added in [API level 23](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int CALLBACK\_TYPE\_MATCH\_LOST

Receive a callback when advertisements are no longer received from a device that has been previously reported by a first match callback.

Constant Value: 4 (0x00000004)

### MATCH\_MODE\_AGGRESSIVE

Added in [API level 23](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int MATCH\_MODE\_AGGRESSIVE

In Aggressive mode, hw will determine a match sooner even with feeble signal strength and few number of sightings/match in a duration.

Constant Value: 1 (0x00000001)

### MATCH\_MODE\_STICKY

Added in [API level 23](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int MATCH\_MODE\_STICKY

For sticky mode, higher threshold of signal strength and sightings is required before reporting by hw.

Constant Value: 2 (0x00000002)

### MATCH\_NUM\_FEW\_ADVERTISEMENT

Added in [API level 23](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int MATCH\_NUM\_FEW\_ADVERTISEMENT

Match few advertisement per filter, depends on current capability and availability of the resources in hw.

Constant Value: 2 (0x00000002)

### MATCH\_NUM\_MAX\_ADVERTISEMENT

Added in [API level 23](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int MATCH\_NUM\_MAX\_ADVERTISEMENT

Match as many advertisement per filter as hw could allow, depends on current capability and availability of the resources in hw.

Constant Value: 3 (0x00000003)

### MATCH\_NUM\_ONE\_ADVERTISEMENT

Added in [API level 23](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int MATCH\_NUM\_ONE\_ADVERTISEMENT

Determines how many advertisements to match per filter, as this is scarce hw resource. Match one advertisement per filter.

Constant Value: 1 (0x00000001)

### PHY\_LE\_ALL\_SUPPORTED

Added in [API level 26](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int PHY\_LE\_ALL\_SUPPORTED

Use all supported PHYs for scanning. This will check the controller capabilities, and start the scan on 1Mbit and LE Coded PHYs if supported, or on the 1Mbit PHY only.

Constant Value: 255 (0x000000ff)

### SCAN\_MODE\_BALANCED

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int SCAN\_MODE\_BALANCED

Perform Bluetooth LE scan in balanced power mode. Scan results are returned at a rate that provides a good trade-off between scan frequency and power consumption.

Constant Value: 1 (0x00000001)

### SCAN\_MODE\_LOW\_LATENCY

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int SCAN\_MODE\_LOW\_LATENCY

Scan using highest duty cycle. It's recommended to only use this mode when the application is running in the foreground.

Constant Value: 2 (0x00000002)

### SCAN\_MODE\_LOW\_POWER

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int SCAN\_MODE\_LOW\_POWER

Perform Bluetooth LE scan in low power mode. This is the default scan mode as it consumes the least power. This mode is enforced if the scanning application is not in foreground.

Constant Value: 0 (0x00000000)

### SCAN\_MODE\_OPPORTUNISTIC

Added in [API level 23](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final int SCAN\_MODE\_OPPORTUNISTIC

A special Bluetooth LE scan mode. Applications using this scan mode will passively listen for other scan results without starting BLE scans themselves.

Constant Value: -1 (0xffffffff)

### SCAN\_TYPE\_ACTIVE

Added in [version 36.1](https://developer.android.com/topic/libraries/support-library/revisions)

public static final int SCAN\_TYPE\_ACTIVE

Does active scanning, scan results are delivered upon scan responses arrive.

Constant Value: 2 (0x00000002)

### SCAN\_TYPE\_PASSIVE

Added in [version 36.1](https://developer.android.com/topic/libraries/support-library/revisions)

public static final int SCAN\_TYPE\_PASSIVE

Does passive scanning, scan responses are ignored.

Constant Value: 1 (0x00000001)

### SCAN\_TYPE\_UNKNOWN

Added in [version 36.1](https://developer.android.com/topic/libraries/support-library/revisions)

public static final int SCAN\_TYPE\_UNKNOWN

Scan type is unknown.

Constant Value: 0 (0x00000000)

## Fields

### CREATOR

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public static final [Creator](https://developer.android.com/reference/android/os/Parcelable.Creator)<[ScanSettings](https://developer.android.com/reference/android/bluetooth/le/ScanSettings)\> CREATOR

## Public methods

### describeContents

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public int describeContents ()

Describe the kinds of special objects contained in this Parcelable instance's marshaled representation. For example, if the object will include a file descriptor in the output of `[writeToParcel(Parcel,int)](https://developer.android.com/reference/android/os/Parcelable#writeToParcel\(android.os.Parcel,%20int\))`, the return value of this method must include the `[CONTENTS_FILE_DESCRIPTOR](https://developer.android.com/reference/android/os/Parcelable#CONTENTS_FILE_DESCRIPTOR)` bit.

| Returns |
| --- |
| `int` | a bitmask indicating the set of special object types marshaled by this Parcelable object instance.
Value is either `0` or
-   `[CONTENTS_FILE_DESCRIPTOR](https://developer.android.com/reference/android/os/Parcelable#CONTENTS_FILE_DESCRIPTOR)`

 |

### getCallbackType

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public int getCallbackType ()

| Returns |
| --- |
| `int` |
 |

### getLegacy

Added in [API level 26](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean getLegacy ()

Returns whether only legacy advertisements will be returned. Legacy advertisements include advertisements as specified by the Bluetooth core specification 4.2 and below.

| Returns |
| --- |
| `boolean` |
 |

### getPhy

Added in [API level 26](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public int getPhy ()

Returns the physical layer used during a scan.

| Returns |
| --- |
| `int` |
 |

### getReportDelayMillis

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public long getReportDelayMillis ()

Returns report delay timestamp based on the device clock.

| Returns |
| --- |
| `long` |
 |

### getRssiThreshold

Added in [version 36.1](https://developer.android.com/topic/libraries/support-library/revisions)

public int getRssiThreshold ()

| Returns |
| --- |
| `int` |
 |

### getScanMode

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public int getScanMode ()

| Returns |
| --- |
| `int` |
 |

### getScanResultType

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public int getScanResultType ()

| Returns |
| --- |
| `int` |
 |

### getScanType

Added in [version 36.1](https://developer.android.com/topic/libraries/support-library/revisions)

public int getScanType ()

| Returns |
| --- |
| `int` | Value is one of the following:
-   `[SCAN_TYPE_UNKNOWN](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#SCAN_TYPE_UNKNOWN)`
-   `[SCAN_TYPE_PASSIVE](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#SCAN_TYPE_PASSIVE)`
-   `[SCAN_TYPE_ACTIVE](https://developer.android.com/reference/android/bluetooth/le/ScanSettings#SCAN_TYPE_ACTIVE)`

 |

### writeToParcel

Added in [API level 21](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public void writeToParcel ([Parcel](https://developer.android.com/reference/android/os/Parcel) dest,
                int flags)

Flatten this object in to a Parcel.

| Parameters |
| --- |
| `dest` | `Parcel`: The Parcel in which the object should be written.
This value cannot be `null`.
 |
| `flags` | `int`: Additional flags about how the object should be written. May be 0 or `[Parcelable.PARCELABLE_WRITE_RETURN_VALUE](https://developer.android.com/reference/android/os/Parcelable#PARCELABLE_WRITE_RETURN_VALUE)`.
Value is either `0` or a combination of the following:

-   `[Parcelable.PARCELABLE_WRITE_RETURN_VALUE](https://developer.android.com/reference/android/os/Parcelable#PARCELABLE_WRITE_RETURN_VALUE)`

 |