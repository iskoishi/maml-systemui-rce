#!/usr/bin/env python3
"""
MAML 主题净化器 (maml-purifier.py)
===================================
剥离 MIUI/HyperOS 锁屏 MAML manifest 里的反射命令，用于导入/应用主题前自我免疫。

威胁背景：
  MAML 的 <MethodCommand class="..." method="..." params="..."> 会被 SystemUI
  当作 Class.forName(...).getMethod(...).invoke(...) 执行（见配套技术文章）。
  class 属性 = 反射目标类，是唯一的"代码执行"标记。

净化策略（保守、不影响正常主题）：
  仅删除带 class 属性的元素（MethodCommand / ExternCommand / 任何反射命令），
  保留纯 UI 元素与不反射的命令（VariableCommand / MultiCommand 无 class 等）。

用法:
  python3 maml-purifier.py <manifest.xml>          # 净化 manifest，输出到 stdout
  python3 maml-purifier.py <theme.mtz>             # 净化 mtz 内的 lockscreen 子 zip 的 advance/manifest.xml
  python3 maml-purifier.py <in.xml> -o <out.xml>   # 净化并写入文件

无破坏性动作：不删除 UI 元素、不改主题包其余内容、不触碰设备。
"""
import sys, re, zipfile, os, shutil

def purify_manifest(xml_text):
    """剥离带 class 属性的反射命令。返回 (净化后文本, 是否改动, 移除数)。"""
    removed = [0]

    def strip_class_elems(text):
        # 自闭合命令: <X ... class="..." ... />
        def _sc(m):
            removed[0] += 1
            return ''
        new = re.sub(r'<\w+[^>]*\bclass\s*=\s*"[^"]*"[^>]*/>', _sc, text)
        # 成对命令: <X ... class="..." ...> ... </X>（非贪婪，跨行）
        def _pc(m):
            removed[0] += 1
            return ''
        new = re.sub(r'<\w+[^>]*\bclass\s*=\s*"[^"]*"[^>]*>.*?</\w+\s*>', _pc, new, flags=re.S)
        return new

    out = strip_class_elems(xml_text)
    # 清理剥除后遗留的空 ExternalCommands/Trigger 包裹（跨行空白）
    out = re.sub(r'<ExternalCommands>\s*</ExternalCommands>', '', out, flags=re.S)
    out = re.sub(r'<Trigger[^>]*>\s*</Trigger>', '', out, flags=re.S)
    # 兜底：ExternalCommands 内只剩空白/注释时也整体清掉
    out = re.sub(r'<ExternalCommands>\s*(?:<!--.*?-->\s*)*</ExternalCommands>', '', out, flags=re.S)
    return out, out != xml_text, removed[0]

def purify_mtz(path):
    """净化 mtz 内 lockscreen 子 zip 的 advance/manifest.xml。"""
    tmp = path + '.purified'
    with zipfile.ZipFile(path) as zin:
        names = zin.namelist()
        # 找 lockscreen 子 zip（无扩展名，通常是 zip）
        lock_cands = [n for n in names if n.lower().endswith('lockscreen') or '/lockscreen' in n.lower()]
        target = None
        for n in names:
            data = zin.read(n)
            if data[:2] == b'PK' and ('lockscreen' in n.lower() or n.lower().endswith('.zip')):
                target = n
                break
        if target is None:
            print(f'[!] 未找到 lockscreen 子 zip（候选: {lock_cands or "无"}），仅列出内容')
            with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
                for n in names:
                    zout.writestr(n, zin.read(n))
            return
        # 打开子 zip，净化 manifest
        sub = zipfile.ZipFile(io_bytes(zin.read(target)))
        sub_names = sub.namelist()
        manifest = 'advance/manifest.xml'
        if manifest not in sub_names:
            print(f'[!] 子 zip 内无 {manifest}，子 zip 内容: {sub_names[:10]}')
            return
        mtext = sub.read(manifest).decode('utf-8', 'replace')
        clean, changed, n = purify_manifest(mtext)
        print(f'[*] {target} -> {manifest}: {"剥离 " + str(n) + " 个反射命令" if changed else "无反射命令"}')
        # 重建子 zip
        sub_tmp = io_bytes(b'')
        import io
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as zs:
            for sn in sub_names:
                if sn == manifest:
                    zs.writestr(sn, clean)
                else:
                    zs.writestr(sn, sub.read(sn))
        sub_data = buf.getvalue()
        # 重建 mtz
        with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as zout:
            for n in names:
                if n == target:
                    zout.writestr(n, sub_data)
                else:
                    zout.writestr(n, zin.read(n))
        print(f'[+] 已写出 {tmp}')

def io_bytes(b):
    import io
    return io.BytesIO(b)

def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        print(__doc__)
        return
    src = args[0]
    out = None
    if '-o' in args:
        out = args[args.index('-o') + 1]
    if src.endswith('.mtz') or src.endswith('.zip'):
        purify_mtz(src)
        return
    # manifest 文件
    with open(src, encoding='utf-8', errors='replace') as f:
        text = f.read()
    clean, changed, n = purify_manifest(text)
    if changed:
        print(f'[*] 剥离 {n} 个反射命令')
    else:
        print('[*] 无反射命令，manifest 已安全')
    if out:
        with open(out, 'w', encoding='utf-8') as f:
            f.write(clean)
        print(f'[+] 已写入 {out}')
    else:
        sys.stdout.write(clean)

if __name__ == '__main__':
    main()
