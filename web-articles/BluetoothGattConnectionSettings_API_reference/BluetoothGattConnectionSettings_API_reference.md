# BluetoothGattConnectionSettings  |  API reference
> 原文链接: https://developer.android.com/reference/android/bluetooth/BluetoothGattConnectionSettings

---

-   [Android Developers](https://developer.android.com/)
-   [Develop](https://developer.android.com/develop)
-   [API reference](https://developer.android.com/reference)

Was this helpful?

-   On this page
-   [Summary](#summary)
    -   [Nested classes](#nested-classes)
    -   [Public methods](#public-methods)
    -   [Inherited methods](#inherited-methods)
-   [Public methods](#public-methods_1)
    -   [getTransport](#getTransport\(\))
    -   [isAutoConnectEnabled](#isAutoConnectEnabled\(\))
    -   [isAutomaticMtuEnabled](#isAutomaticMtuEnabled\(\))
    -   [isOpportunisticEnabled](#isOpportunisticEnabled\(\))
    -   [toString](#toString\(\))

Added in [API level 37](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

Summary: [Nested Classes](#nestedclasses) | [Methods](#pubmethods) | [Inherited Methods](#inhmethods)

# BluetoothGattConnectionSettings Stay organized with collections Save and categorize content based on your preferences.

* * *

[Kotlin](https://developer.android.com/reference/kotlin/android/bluetooth/BluetoothGattConnectionSettings) |Java

`public final class BluetoothGattConnectionSettings`
`extends [Object](https://developer.android.com/reference/java/lang/Object)`

<table class="jd-inheritance-table"><tbody><tr><td colspan="2" class="jd-inheritance-class-cell"><a href="https://developer.android.com/reference/java/lang/Object">java.lang.Object</a></td></tr><tr><td class="jd-inheritance-space">&nbsp;&nbsp;&nbsp;↳</td><td colspan="1" class="jd-inheritance-class-cell">android.bluetooth.BluetoothGattConnectionSettings</td></tr></tbody></table>

* * *

Defines parameters for creating BluetoothGatt connection.

Used with `[BluetoothDevice.connectGatt](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#connectGatt\(android.bluetooth.BluetoothGattConnectionSettings,%20java.util.concurrent.Executor,%20android.bluetooth.BluetoothGattCallback\))` to create a Gatt client connection.

`[BluetoothDevice.connectGatt](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#connectGatt\(android.bluetooth.BluetoothGattConnectionSettings,%20java.util.concurrent.Executor,%20android.bluetooth.BluetoothGattCallback\))` ensures It applies the Gatt settings passed as part of `[BluetoothGattConnectionSettings](https://developer.android.com/reference/android/bluetooth/BluetoothGattConnectionSettings)`

**See also:**

-   `[BluetoothDevice.connectGatt](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#connectGatt\(android.bluetooth.BluetoothGattConnectionSettings,%20java.util.concurrent.Executor,%20android.bluetooth.BluetoothGattCallback\))`

## Summary

|
### Nested classes

 |
| --- |
| `class` | `[BluetoothGattConnectionSettings.Builder](https://developer.android.com/reference/android/bluetooth/BluetoothGattConnectionSettings.Builder)`

Builder for `[BluetoothGattConnectionSettings](https://developer.android.com/reference/android/bluetooth/BluetoothGattConnectionSettings)`.

 |

|
### Public methods

 |
| --- |
| `int` | `[getTransport](https://developer.android.com/reference/android/bluetooth/BluetoothGattConnectionSettings#getTransport\(\))()`

Returns the transport to be used for GATT connection.

 |
| `boolean` | `[isAutoConnectEnabled](https://developer.android.com/reference/android/bluetooth/BluetoothGattConnectionSettings#isAutoConnectEnabled\(\))()`

Returns true if auto connection enabled or false otherwise.

 |
| `boolean` | `[isAutomaticMtuEnabled](https://developer.android.com/reference/android/bluetooth/BluetoothGattConnectionSettings#isAutomaticMtuEnabled\(\))()`

Returns true if the automatic MTU exchange is enabled for this connection or false otherwise.

 |
| `boolean` | `[isOpportunisticEnabled](https://developer.android.com/reference/android/bluetooth/BluetoothGattConnectionSettings#isOpportunisticEnabled\(\))()`

Returns if the GATT connection is opportunistic or not.

 |
| `[String](https://developer.android.com/reference/java/lang/String)` | `[toString](https://developer.android.com/reference/android/bluetooth/BluetoothGattConnectionSettings#toString\(\))()`

Returns a `[String](https://developer.android.com/reference/java/lang/String)` that describes each BluetoothGattConnectionSettings parameter current value.

 |

|
### Inherited methods

 |
| --- |
| From class `[java.lang.Object](https://developer.android.com/reference/java/lang/Object)`

<table class="responsive"><tbody><tr data-version-added="1"><td><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object">Object</a></code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#clone()">clone</a>()</code><p>Creates and returns a copy of this object.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">boolean</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#equals(java.lang.Object)">equals</a>(<a href="https://developer.android.com/reference/java/lang/Object">Object</a> obj)</code><p>Indicates whether some other object is "equal to" this one.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#finalize()">finalize</a>()</code><p>Called by the garbage collector on an object when garbage collection determines that there are no more references to the object.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final <a href="https://developer.android.com/reference/java/lang/Class">Class</a>&lt;?&gt;</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#getClass()">getClass</a>()</code><p>Returns the runtime class of this <code translate="no" dir="ltr">Object</code>.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">int</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#hashCode()">hashCode</a>()</code><p>Returns a hash code value for the object.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#notify()">notify</a>()</code><p>Wakes up a single thread that is waiting on this object's monitor.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#notifyAll()">notifyAll</a>()</code><p>Wakes up all threads that are waiting on this object's monitor.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/String">String</a></code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#toString()">toString</a>()</code><p>Returns a string representation of the object.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#wait(long,%20int)">wait</a>(long timeoutMillis, int nanos)</code><p>Causes the current thread to wait until it is awakened, typically by being <em>notified</em> or <em>interrupted</em>, or until a certain amount of real time has elapsed.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#wait(long)">wait</a>(long timeoutMillis)</code><p>Causes the current thread to wait until it is awakened, typically by being <em>notified</em> or <em>interrupted</em>, or until a certain amount of real time has elapsed.</p></td></tr><tr data-version-added="1"><td><code translate="no" dir="ltr">final void</code></td><td width="100%"><code translate="no" dir="ltr"><a href="https://developer.android.com/reference/java/lang/Object#wait()">wait</a>()</code><p>Causes the current thread to wait until it is awakened, typically by being <em>notified</em> or <em>interrupted</em>.</p></td></tr></tbody></table>

 |

## Public methods

### getTransport

Added in [API level 37](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public int getTransport ()

Returns the transport to be used for GATT connection.

| Returns |
| --- |
| `int` | Value is one of the following:
-   `[BluetoothDevice.TRANSPORT_AUTO](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#TRANSPORT_AUTO)`
-   `[BluetoothDevice.TRANSPORT_BREDR](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#TRANSPORT_BREDR)`
-   `[BluetoothDevice.TRANSPORT_LE](https://developer.android.com/reference/android/bluetooth/BluetoothDevice#TRANSPORT_LE)`

 |

### isAutoConnectEnabled

Added in [API level 37](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean isAutoConnectEnabled ()

Returns true if auto connection enabled or false otherwise.

| Returns |
| --- |
| `boolean` |
 |

### isAutomaticMtuEnabled

Added in [API level 37](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean isAutomaticMtuEnabled ()

Returns true if the automatic MTU exchange is enabled for this connection or false otherwise.

| Returns |
| --- |
| `boolean` |
 |

### isOpportunisticEnabled

Added in [API level 37](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public boolean isOpportunisticEnabled ()

Returns if the GATT connection is opportunistic or not.

| Returns |
| --- |
| `boolean` |
 |

### toString

Added in [API level 37](https://developer.android.com/guide/topics/manifest/uses-sdk-element#ApiLevels)

public [String](https://developer.android.com/reference/java/lang/String) toString ()

Returns a `[String](https://developer.android.com/reference/java/lang/String)` that describes each BluetoothGattConnectionSettings parameter current value.

| Returns |
| --- |
| `[String](https://developer.android.com/reference/java/lang/String)` | a string representation of the object.
 |

Was this helpful?