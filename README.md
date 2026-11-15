# MAML 锁屏反射执行面（HyperOS 2.0.6 / 4.0.6）

> 状态：**未修复**（截至 2026-11-14）
> 影响：本地（投递需 shell 权限 + 需应用一个第三方主题）→ `com.android.systemui`（uid 1000 / user system）代码执行
> 边界：不涉及 root；SELinux 域仍为 `system_app`

## 这是什么

MIUI / HyperOS 的锁屏主题（MAML）清单里，`<MethodCommand class="..." method="..." params="..." paramTypes="...">` 会被框架直接翻译成 `Class.forName(...).getMethod(...).invoke(...)`，且**没有类名白名单、没有方法白名单、没有签名校验、没有调试开关**。

因此"应用一个第三方主题"等价于"在 SystemUI 进程里执行主题作者指定的任意静态方法调用"。本文给出真机证据（OS2.0.6）与跨版本静态对照（OS4.0.6，逐指令等价）。

## 目录

| 路径 | 内容 |
|---|---|
| [`article.md`](article.md) | 完整技术文章（中文） |
| [`poc/minimal-manifest.xml`](poc/minimal-manifest.xml) | 最小无害 PoC：只写一条日志 + 一个文本元素 |
| [`evidence/logcat.txt`](evidence/logcat.txt) | 真机 logcat 原始输出（170 行，未删改） |
| [`evidence/hashes.md`](evidence/hashes.md) | 设备版本、SystemUI APK / dex 哈希 |
| [`timeline.md`](timeline.md) | 时间线与厂商响应记录 |

## 快速验证（无害）

把 `poc/minimal-manifest.xml` 作为锁屏包内的 `advance/manifest.xml` 应用后，熄屏再亮屏，应看到：

```
D/ScreenElementRoot( <systemui-pid>): init
D/ActionCommand( <systemui-pid>): MethodCommand, class=android.util.Log ... method=d
D/ActionCommand( <systemui-pid>):     loadMethod(), successful.  public static int android.util.Log.d(java.lang.String,java.lang.String)
D/POC     ( <systemui-pid>): STAGE1_ALIVE
```

> 注意：`params` 是表达式而非字符串。裸写 `params="POC,ALIVE"` 会被当成未定义变量求值成 null（表现为 `NullPointerException: println needs a message`），字面量必须用单引号。

## 支持

如果这些内容对你有帮助：<https://afdian.com/a/iskoishi>

## 免责

本文仅用于安全研究与推动修复。仓库内不含任何可用于实际攻击的主题包、不含投递链实现、不含针对具体第三方工具的利用代码。
