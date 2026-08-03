# android/app/src/com/android/bluetooth/le_scan - platform/packages/modules/Bluetooth
> 原文链接: https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/

---

[android](https://android.googlesource.com/?format=HTML)/[platform](https://android.googlesource.com/platform/)/[packages](https://android.googlesource.com/platform/packages/)/[modules](https://android.googlesource.com/platform/packages/modules/)/[Bluetooth](https://android.googlesource.com/platform/packages/modules/Bluetooth/)/[refs/tags/android-17.0.0\_r1](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1)/[.](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/)/[android](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android)/[app](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app)/[src](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src?autodive=0)/[com](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com?autodive=0)/[android](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android?autodive=0)/[bluetooth](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth)/le\_scan

tree: de1f269b13bb1e051def6f4b4a1d9f362383e4ea

1.  [AdvtFilterOnFoundOnLostInfo.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/AdvtFilterOnFoundOnLostInfo.kt)
2.  [AppCurrentConsumptionStats.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/AppCurrentConsumptionStats.kt)
3.  [AppScanStats.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/AppScanStats.kt)
4.  [BatchScanThrottler.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/BatchScanThrottler.kt)
5.  [BatchScanUtil.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/BatchScanUtil.kt)
6.  [FilterParams.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/FilterParams.kt)
7.  [MsftAdvMonitor.java](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/MsftAdvMonitor.java)
8.  [MsftAdvMonitorMergedFilterList.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/MsftAdvMonitorMergedFilterList.kt)
9.  [PeriodicScanManager.java](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/PeriodicScanManager.java)
10.  [PeriodicScanNativeCallback.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/PeriodicScanNativeCallback.kt)
11.  [PeriodicScanNativeInterface.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/PeriodicScanNativeInterface.kt)
12.  [ScanBinder.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScanBinder.kt)
13.  [ScanClient.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScanClient.kt)
14.  [ScanController.java](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScanController.java)
15.  [ScanFilterQueue.java](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScanFilterQueue.java)
16.  [ScanManager.java](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScanManager.java)
17.  [ScanMetricsReporter.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScanMetricsReporter.kt)
18.  [ScanNativeCallback.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScanNativeCallback.kt)
19.  [ScanNativeInterface.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScanNativeInterface.kt)
20.  [ScannerApp.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScannerApp.kt)
21.  [ScannerMap.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScannerMap.kt)
22.  [ScanRadioStats.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScanRadioStats.kt)
23.  [ScanSuspendManager.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScanSuspendManager.kt)
24.  [ScanThrottler.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScanThrottler.kt)
25.  [ScanUtil.kt](https://android.googlesource.com/platform/packages/modules/Bluetooth/+/refs/tags/android-17.0.0_r1/android/app/src/com/android/bluetooth/le_scan/ScanUtil.kt)