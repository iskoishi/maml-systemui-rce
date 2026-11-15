# 当主题变成代码：MIUI 锁屏 MAML 的反射执行面

> 设备：Xiaomi 22101317C ｜ Android 14 (SDK 34) ｜ HyperOS OS2.0.6.0.UMQCNXM
> 性质：本地漏洞（需用户应用一个恶意主题），无 root，执行上下文为 `com.android.systemui`（uid 1000）
> 版本范围：仅在上述设备与版本实测；其它版本未验证

---

## 摘要

MIUI 的锁屏主题不是"图片 + 布局"，而是一份可被执行的脚本（MAML）。锁屏清单里有一类命令 `<MethodCommand>`，它的 `class` / `method` / `params` / `paramTypes` 四个属性会被框架直接翻译成 `Class.forName(...).getMethod(...).invoke(...)`。

这意味着：**用户应用一个第三方主题，等价于在 SystemUI 进程里执行主题作者指定的、任意签名的静态方法调用，参数完全由作者控制。**

我们在真机上确认了这一点：锁屏 manifest 里写入一行 `Log.d`，日志由 `com.android.systemui`（pid 3281，user system）打出，且 `loadMethod()` 明确解析到了 `android.util.Log.d(String, String)`。同一路径下 `android.app.ActivityManager.getService()` 也能被解析。

---

## 一、背景

MIUI 从 MIUI 6 起就有自己的声明式 UI/脚本框架 MAML（Miui Advanced Markup Language），用于锁屏、AOD（息屏显示）、状态栏插件。主题包中的锁屏部分是一个独立 zip，内部 `advance/manifest.xml` 是入口文件，根节点为 `<Lockscreen>`。

`<ExternalCommands>` 是 MAML 的"命令区"，设计意图是让设计师能写交互——音乐控制、充电动画、天气联动。它支持的命令类型包括 `VariableCommand`、`ExternCommand`、`BinderCommand`、`IntentCommand`、`MultiCommand`，以及本文的主角 `MethodCommand`。

`MethodCommand` 的语义，直白地说，就是"在宿主的进程里反射调用一个 Java 方法"：

```xml
<MethodCommand class="某个类的全名"
               method="方法名"
               params="参数1,参数2"
               paramTypes="String,String"
               target="某个对象" targetType="var" />
```

`class` + `method` 走静态调用；`target` + `method` 走实例调用。`params` 是**表达式列表**而不是字符串字面量——这一点后面会讲到，是复现时最容易踩的坑。

---

## 二、执行面在哪里

锁屏的 MAML 由 SystemUI 加载与渲染。调用链（静态确认）：

```
Keyguard 显示
  └─ ScreenElementRoot.init()
       └─ 解析 <ExternalCommands>
            └─ Trigger action="init"
                 └─ ActionCommand.MethodCommand.init()   → Class.forName / getMethod
                      └─ doPerform()                    → Method.invoke
```

在我们的静态审计里（SystemUI 的 `classes3.dex`，635 个 MAML 类都在这个 dex 中），这条路径上：

- `BaseMethodCommand.init()` 无条件调用 `Class.forName`
- `loadMethod()` 无条件调用 `getMethod`
- `doPerform()` 走 `Method.invoke`
- **没有类名白名单、没有方法白名单、没有签名校验、没有 `Build.IS_DEBUGGABLE` 之类的开关**

唯一新增的门是 `MethodCommand` 构造对象时的 `CAPABILITY_CREATE_OBJ` 能力位，但它只影响"能不能 new 一个对象"，对 `class` + `method` 这种静态调用不生效；而且 `ScreenElementRoot.init()` 默认 `mCapability = -1`（全开）。

---

## 三、证据

### 3.1 静态证据

| 项 | 值 |
|---|---|
| `/system_ext/priv-app/MiuiSystemUI/MiuiSystemUI.apk` | 46,866,083 B，SHA-256 `9f9477a14f8b7762f1feffdc47ed36d10772112ec59a2b6f689f5a0b8fb2e936` |
| ├ `classes3.dex`（MAML 所在） | SHA-256 `700a432634a94dc7779df38016877c9a129f562a1409876c0a4ec1dea9d14f20` |
| 关键类 | `com.miui.maml.ActionCommand$MethodCommand`、`BaseMethodCommand`、`TargetCommand` |
| 关键属性解析 | `class` / `method` / `params` / `paramTypes` / `return` / `returnType` / `target` / `targetType` |

### 3.2 动态证据（真机）

最小无害 manifest（只做一次日志，加一个文本元素便于肉眼确认渲染）：

```xml
<?xml version="1.0" encoding="utf-8"?>
<Lockscreen displayDesktop="false" frameRate="0" screenWidth="1080" version="2">
    <ExternalCommands>
        <Trigger action="init">
            <MethodCommand class="android.util.Log" method="d"
                params="'POC','STAGE1_ALIVE'" paramTypes="String,String" />
            <MethodCommand class="android.app.ActivityManager" method="getService"
                return="ams" />
        </Trigger>
    </ExternalCommands>
    <Text x="120" y="400" size="42" color="#FFFF0000" text="POC-OK" />
</Lockscreen>
```

熄屏再亮屏后，logcat：

```
D/ScreenElementRoot( 3281): init
D/ActionCommand( 3281): MethodCommand, target=null type=SCREEN_ELEMENT,
        class=android.util.Log type=SCREEN_ELEMENT, method=d
D/ActionCommand( 3281):     loadMethod(), successful.
        public static int android.util.Log.d(java.lang.String,java.lang.String)
D/ActionCommand( 3281): MethodCommand, target=null type=SCREEN_ELEMENT,
        class=android.app.ActivityManager type=SCREEN_ELEMENT, method=getService
D/ActionCommand( 3281):     loadMethod(), successful.
        public static android.app.IActivityManager android.app.ActivityManager.getService()
D/POC     ( 3281): STAGE1_ALIVE
```

`pid 3281` 的身份：

```
$ ps -A -o PID,USER,NAME | grep 3281
3281  system  com.android.systemui
```

即 **uid 1000 / user system / SELinux 域 `system_app`**。锁屏界面同时渲染出 `POC-OK` 红字，说明 manifest 确实被当作锁屏内容加载并执行。

### 3.3 一个容易踩的坑（复现必读）

`params` 是**表达式**，不是字符串。写成 `params="POC,STAGE1_ALIVE"` 时，`POC` 被当成未定义变量求值为 `null`，最终调用 `Log.d(null, null)`，抛出：

```
E/ActionCommand: java.lang.reflect.InvocationTargetException
E/ActionCommand:  cause: java.lang.NullPointerException: println needs a message
```

字面量必须用单引号：`params="'POC','STAGE1_ALIVE'"`。

同理，`return` 变量默认写进 double 桶（`returnType` 缺省为 `NUM`），要让 `target` 能取到对象，按静态分析需要显式写 `returnType="object"`（这一点为反汇编推断，未做真机复验）。

---

## 四、影响

| 维度 | 说明 |
|---|---|
| 权限 | 无需 root、无需 shell、无需任何系统授权（执行侧） |
| 触发条件 | 仅需"恶意锁屏包出现在锁屏资源位置 + 被加载一次"；**执行侧不消耗任何权限** |
| 投递前置（前提，非洞本身） | 攻击者前置。本次研究实测的投递需要 **shell** 权限（把恶意锁屏资源写入设备并触发应用）；执行侧无需任何权限。投递与执行分离：漏洞本体是"主题被加载后在 SystemUI 内反射执行" |
| 上下文 | `com.android.systemui`，uid 1000，SELinux `system_app` |
| 能力 | 任意类的静态方法调用（**真机已证明**：`Log.d` 实际打出 `STAGE1_ALIVE`）；拿到对象后可调实例方法（静态推断，未真机验证）；参数完全可控 |
| SystemUI 持有 | `GRANT_RUNTIME_PERMISSIONS`、`WRITE_SECURE_SETTINGS`、`INTERACT_ACROSS_USERS`、可见性极高的系统服务句柄 |
| 边界 | **不能直接 root**。SELinux 域仍是 `system_app`，无法关 SELinux、无法写系统分区、无法 su |

需要强调的是：这不是"主题能画 UI"的问题，而是"主题是代码"的问题。用户对主题的心理模型是内容——一张图片、一套图标、一个布局；没有任何理由要求用户对主题做安全审查。主题的分发渠道（社区站点、网盘、群聊）也普遍没有签名与审计机制。

---

## 五、修复建议

1. **收窄 `MethodCommand`**：移除 `class` 反射，只允许调用与 `ScreenElement` 绑定的既定方法；或维护一份极小的白名单（且白名单里不能出现 `java.lang.reflect`、`Runtime`、`ProcessBuilder`、`ActivityManager`、`ServiceManager` 这类类）。
2. **加载前静态校验**：锁屏 manifest 进入解析器前做一次结构检查，拒绝 `<ExternalCommands>` 中的反射类命令。这一条对正常主题零影响——正常主题用的是 `VariableCommand` / `ExternCommand` / `BinderCommand`，它们都绑定在 MAML 自己的对象模型上。
3. **主题包签名**：引入作者私钥签名并在加载时校验，而不是依赖主题商店的 DRM（DRM 只覆盖商店分发的主题）。
4. **能力最小化**：即便保留反射，也应在独立的低权限进程或受限 ClassLoader 中执行，而不是直接跑在 SystemUI 主进程里。

---

## 六、关于厂商响应（一段吐槽）

小米安全中心公开承诺：**收到安全报告后 5 天内给任何一位安全研究员回复**。

实际情况是：我提交的一个「应用锁」相关漏洞，到今天已经快 **四周**，没有任何回复；其间通过官方渠道追问，也没有任何回应。五天承诺变成四周静默，这个 SLA 不如不写——不写至少不会让人误以为沟通是双向的。

所以本文这个 MAML 洞我没有走 SRC。理由不是赌气，是两个现实判断：

1. 一旦进入厂商修复流程，主题链路上所有相关校验会被一并整改，正常第三方主题生态会被误伤——那不是我想看到的结果；
2. 对一个连"5 天回复"都做不到的通道，指望它在合理时间内给出修复，本身就不现实。

如果厂商希望补丁先于公开，给我一个能真正收到回复的邮箱即可；否则本文按"发布即公开"处理。

---

## 七、版本覆盖与局限

| 版本 | 证据类型 | 结论 |
|---|---|---|
| HyperOS **OS2.0.6.0.UMQCNXM**（Android 14，本文验证机） | 真机运行 + 静态 | 反射执行成立（日志、pid、渲染全部实测） |
| HyperOS **OS4.0.6.0.XPNCNXM**（Android 17 / SDK 37，固件镜像 `super.img` 内 `build.prop` 读出；**未真机验证**） | 纯静态 | `ActionCommand$MethodCommand` / `BaseMethodCommand` 结构与 2.0.6 **逐指令等价**：`Class.forName` → `getMethod` → `Method.invoke` 三步完整保留；无白名单、无 `IS_DEBUGGABLE` 开关、无签名校验；`ReflectionHelper` 的 9 个反射句柄（含 `setAccessible`）全部还在 |

- 4.0.6 的 SystemUI：`MiuiSystemUI.apk` 52,007,560 B，SHA-256 `9b577948b8fa3267548a464d91e03a9ac964280bbb40c1612302d7eff6dce695`；659 个 `com.miui.maml.*` 类全部位于其中的 `classes3.dex`。
- 即：这不是某个旧版本遗留的代码路径，**跨两个大版本持续存在**（代码层面确认，4.0.6 未真机验证）。
- 局限：4.0.6 只做了静态对照，未在真机验证；其它机型、其它版本未取素材，不做外推。
- 时间线：2026-11-14 完成 2.0.6 真机验证与 4.0.6 静态对照；本机无补丁。

---

## 八、支持

如果这篇文章对你有帮助，可以通过爱发电支持我继续做这类研究：<https://afdian.com/a/iskoishi>
