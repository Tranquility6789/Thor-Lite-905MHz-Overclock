#!/usr/bin/env python3
"""thor_gpu_oc.py - raise the GPU top frequency/voltage level in an AYN Thor Lite boot image.

Reads YOUR OWN boot.img (Android boot header v2), patches the GPU top level in the
device-tree blobs inside it, and writes a new image. Nothing is downloaded or redistributed.
Standard library only (Python 3.8+).

  python3 thor_gpu_oc.py boot.img --info
  python3 thor_gpu_oc.py boot.img -o boot_gpu905_lv336.img --freq 905 --level 336
"""
import argparse, hashlib, re, struct, sys

KNOWN_LEVELS = {64, 128, 144, 192, 224, 256, 320, 336, 384, 416}  # levels seen/verified on Thor Lite
MAX_VERIFIED_MHZ = 905                                            # highest frequency verified so far
PAGE_FALLBACK = 4096

def die(msg):
    sys.exit("error: " + msg)

def parse_fdt(b):
    """Return {node_path: {prop: (data_offset, data_bytes)}} for one device-tree blob."""
    magic, total, off_struct, off_str, _r, _v, _l, _b, sz_str, _s = struct.unpack_from(">10I", b, 0)
    if magic != 0xd00dfeed:
        raise ValueError("not a dtb")
    strs = b[off_str:off_str + sz_str]
    p, path, stack, nodes = off_struct, [], [], {}
    while True:
        tok = struct.unpack_from(">I", b, p)[0]; p += 4
        if tok == 1:
            e = b.index(b"\0", p); name = b[p:e].decode(); p = (e + 1 + 3) & ~3
            path.append(name); full = "/".join(path); nodes[full] = {}; stack.append(full)
        elif tok == 2:
            path.pop(); stack.pop()
        elif tok == 3:
            ln, no = struct.unpack_from(">II", b, p); p += 8
            nodes[stack[-1]][strs[no:strs.index(b"\0", no)].decode()] = (p, b[p:p + ln])
            p = (p + ln + 3) & ~3
        elif tok == 9:
            break
    return total, nodes

def read_layout(d):
    if d[:8] != b"ANDROID!":
        die("not an Android boot image (missing ANDROID! magic)")
    ksz, _, rsz, _, ssz = struct.unpack_from("<5I", d, 8)
    page, hver = struct.unpack_from("<2I", d, 36)
    if hver != 2:
        die(f"boot header version {hver} is not supported (this tool only handles version 2)")
    rdsz, _rdoff, _hsz, dtbsz, _dtba = struct.unpack_from("<IQIIQ", d, 1632)
    al = lambda x: (x + page - 1) // page * page
    ko = page; ro = ko + al(ksz); so = ro + al(rsz); rdo = so + al(ssz); dto = rdo + al(rdsz)
    return dict(page=page, ksz=ksz, rsz=rsz, ssz=ssz, rdsz=rdsz, dtbsz=dtbsz,
                ko=ko, ro=ro, so=so, rdo=rdo, dto=dto, end=dto + al(dtbsz))

def blobs(d, lay):
    dtb = bytes(d[lay["dto"]:lay["dto"] + lay["dtbsz"]]); o = 0
    while o + 8 <= len(dtb) and dtb[o:o + 4] == b"\xd0\x0d\xfe\xed":
        try:
            total, nodes = parse_fdt(dtb[o:])
        except Exception:
            break
        yield o, nodes
        o += total

def gpu_tables(nodes):
    """(opp nodes sorted by freq desc, pwrlevel@0 nodes) for one blob."""
    opp = []
    for path, props in nodes.items():
        if re.fullmatch(r"/soc/gpu-opp-table_v2/opp-\d+", path) and "opp-hz" in props and "opp-microvolt" in props:
            opp.append((struct.unpack(">Q", props["opp-hz"][1])[0], path))
    opp.sort(reverse=True)
    top = [p for p, props in nodes.items()
           if p.endswith("qcom,gpu-pwrlevel@0") and "qcom,gpu-freq" in props]
    return opp, top

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("boot_img"); ap.add_argument("-o", "--output")
    ap.add_argument("--freq", type=int, default=905, help="new GPU top frequency in MHz (default 905)")
    ap.add_argument("--level", type=int, default=336, help="voltage level for the top entry (default 336)")
    ap.add_argument("--info", action="store_true", help="print the GPU table and exit")
    ap.add_argument("--full", action="store_true", help="write a full-size image instead of trimming trailing padding")
    ap.add_argument("--force", action="store_true", help="allow values outside the verified range (can cause crashes)")
    a = ap.parse_args()

    d = bytearray(open(a.boot_img, "rb").read()); lay = read_layout(d)
    found = []
    for o, nodes in blobs(d, lay):
        opp, top = gpu_tables(nodes)
        found.append((o, nodes, opp, top))
        if opp:
            print(f"dtb blob @{o}: GPU levels MHz = {[hz // 10**6 if hz % 10**6 == 0 else hz / 10**6 for hz, _ in opp]}, "
                  f"top level value = {struct.unpack('>I', nodes[opp[0][1]]['opp-microvolt'][1])[0]}")
        else:
            print(f"dtb blob @{o}: no GPU table (skipped)")
    targets = [f for f in found if f[2] and f[3]]
    if not targets:
        die("no supported GPU table found in this image")
    if a.info:
        return
    if not a.output:
        die("give an output file with -o")
    if a.output == a.boot_img:
        die("output must be a different file from the input")

    new_hz = a.freq * 10**6
    if not a.force:
        if a.freq > MAX_VERIFIED_MHZ:
            die(f"{a.freq}MHz is above the highest verified value ({MAX_VERIFIED_MHZ}MHz); use --force to try anyway")
        if a.level not in KNOWN_LEVELS:
            die(f"level {a.level} is not one of the known levels {sorted(KNOWN_LEVELS)}; use --force to try anyway")
    for o, nodes, opp, top in targets:
        if len(opp) < 2 or new_hz <= opp[1][0]:
            die("new frequency must be higher than the second-highest GPU level in the table")

    changed = 0
    for o, nodes, opp, top in targets:
        old_hz, opp_path = opp[0]; props = nodes[opp_path]
        struct.pack_into(">Q", d, lay["dto"] + o + props["opp-hz"][0], new_hz)
        struct.pack_into(">I", d, lay["dto"] + o + props["opp-microvolt"][0], a.level)
        changed += 2
        for p in top:
            off, val = nodes[p]["qcom,gpu-freq"]
            if struct.unpack(">I", val)[0] == old_hz:
                struct.pack_into(">I", d, lay["dto"] + o + off, new_hz); changed += 1

    # refresh the header's SHA-1 id (kernel, ramdisk, second, recovery dtbo, dtb; each followed by its size)
    h = hashlib.sha1()
    for off, sz in ((lay["ko"], lay["ksz"]), (lay["ro"], lay["rsz"]), (lay["so"], lay["ssz"]),
                    (lay["rdo"], lay["rdsz"]), (lay["dto"], lay["dtbsz"])):
        h.update(bytes(d[off:off + sz])); h.update(struct.pack("<I", sz))
    d[0x240:0x240 + 32] = h.digest() + b"\0" * 12

    out = bytes(d) if a.full else bytes(d[:lay["end"]])
    open(a.output, "wb").write(out)
    print(f"patched {changed} values across {len(targets)} dtb blob(s): top GPU level -> {a.freq}MHz, voltage level {a.level}")
    print(f"wrote {a.output} ({len(out)} bytes)")

if __name__ == "__main__":
    main()
