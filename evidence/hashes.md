# 证据索引

## 环境（真机）

| 项 | 值 |
|---|---|
| 机型 | Xiaomi 22101317C |
| Android | 14（SDK 34） |
| 系统 | HyperOS OS2.0.6.0.UMQCNXM（MIUI V816） |
| 执行进程 | `com.android.systemui`，pid 3281，user `system`（uid 1000） |

## 二进制

| 文件 | 大小 | SHA-256 |
|---|---|---|
| OS2.0.6 `MiuiSystemUI.apk` | 46,866,083 B | `9f9477a14f8b7762f1feffdc47ed36d10772112ec59a2b6f689f5a0b8fb2e936` |
| OS2.0.6 `classes3.dex`（MAML 所在） | — | `700a432634a94dc7779df38016877c9a129f562a1409876c0a4ec1dea9d14f20` |
| OS4.0.6 `MiuiSystemUI.apk` | 52,007,560 B | `9b577948b8fa3267548a464d91e03a9ac964280bbb40c1612302d7eff6dce695` |

## 原始日志

`logcat.txt`：真机抓取的 `ScreenElementRoot` / `ActionCommand` / `POC` 三个 tag，170 行，未删改。

关键行：

```
D/ScreenElementRoot( 3281): init
D/ActionCommand( 3281): MethodCommand, target=null type=SCREEN_ELEMENT,
        class=android.util.Log type=SCREEN_ELEMENT, method=d
D/ActionCommand( 3281):     loadMethod(), successful.
        public static int android.util.Log.d(java.lang.String,java.lang.String)
D/ActionCommand( 3281):     loadMethod(), successful.
        public static android.app.IActivityManager android.app.ActivityManager.getService()
D/POC     ( 3281): STAGE1_ALIVE
```

## 身份核对

```
$ ps -A -o PID,USER,NAME | grep 3281
3281  system  com.android.systemui
```

## 跨版本对照（OS4.0.6）

从 `lhasa-images-OS4.0.6.0.XPNCNXM` 的 `super.img`（sparse v1.0 → LP v10.2）中提取 `system_ext`（EROFS，607.54 MiB）后取出的 `MiuiSystemUI.apk`：

- `com.miui.maml.ActionCommand$MethodCommand` / `BaseMethodCommand` / `TargetCommand` / `FieldCommand` 全部存在
- `Class.forName` → `getMethod` → `Method.invoke` 三步逐指令保留
- 无白名单、无 `Build.IS_DEBUGGABLE`、无签名校验
- `ReflectionHelper` 的 9 个反射句柄（含 `setAccessible`）全部保留
- 与 OS2.0.6 的方法级 diff：仅 `goto <end>` → `return-void`（等价）、异常表重排、`const-string/jumbo` 升宽
