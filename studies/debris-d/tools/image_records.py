"""image_records.py - DEBRIS-D (cft-debris, MIT): one record a compiled image.

Every image and bank cftc wrote stays in DEBRIS-D's scratch (an image carries
cft-fp256's routines). This writes, for each, its SHA-256 and its bank's, the
counts its manifest states, and the command that rebuilds it from this
repository's source at cft-fp256 0aa997a3 (the archive, SHA-256 e01003cc...).
usage: python -I -B image_records.py  ->  studies/debris-d/images.tsv (overwritten: a record, not a log)
"""
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dd  # noqa: E402

ARCH = "e01003cc0b984864b065ce3395f56fa189451fcb0cd98cce5b11b3c17a9c29b8"


def main():
    rows = []
    for man_path in sorted(glob.glob(dd.SCRATCH + "/images/*/*.manifest.json")):
        sub = os.path.basename(os.path.dirname(man_path))
        if sub == "try":
            continue
        stem = os.path.basename(man_path)[:-len(".manifest.json")]
        m = json.load(open(man_path))
        src = os.path.basename(m["source"]["path"].replace("\\", "/"))
        u, p = m["uses"], m["per_step"]
        tgt = m["target"]["name"]
        r = m.get("routines", {})
        gen = ""
        if src.startswith("field"):
            # generated sources live in scratch (debris-d/field_sources.sha256): regenerate first
            n = src[len("field"):].split("-")[0].replace("lane", "")
            gen = "python -I -B studies/debris-d/q2/gen_field.py %s <scratch>/systems/%s%s; " % (
                n, src, " --lane" if "lane" in src else "")
            where = "<scratch>/systems/"
        else:
            where = "studies/debris-d/systems/"
        cmd = (gen + "python -I -B <archive %s>/python/cftc %s%s --steps %d --format %s%s "
               "--stem %s" % (ARCH[:12], where, src, m["steps"], m["format"],
                              "" if tgt == "sw" else " --target " + tgt, stem))
        rows.append("\t".join([
            sub + "/" + stem, dd.sha256_file(man_path.replace(".manifest.json", ".cftp")),
            dd.sha256_file(man_path.replace(".manifest.json", ".bank")), m["source"]["sha256"], m["format"], tgt,
            str(m["steps"]), str(u["instructions"]), str(p["instructions"]), str(p["alu"]), str(p["loads"]),
            str(p["stores"]), str(u["bank_slots"]), str(u["scratch_slots"]), str(u["scratch_declared"]),
            ",".join(u["features"]), json.dumps(r.get("per_call", {}), sort_keys=True),
            str(r.get("instructions_quiet", "")), json.dumps(p["by_op"], sort_keys=True), cmd]))
    head = "\t".join(["image", "cftp_sha256", "bank_sha256", "source_sha256", "format", "target", "steps_a_segment",
                      "image_instructions", "per_step_instructions", "per_step_alu", "per_step_loads",
                      "per_step_stores", "bank_slots", "scratch_slots", "scratch_declared", "features",
                      "routine_instructions_per_call", "routine_instructions_a_step", "per_step_by_op",
                      "rebuild_command"])
    out = os.path.join(dd.ROOT, "images.tsv")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("# DEBRIS-D's compiled images (kept in its scratch, not here), written by image_records.py sha256 %s\n"
                % dd.sha256_file(os.path.abspath(__file__)))
        f.write(head + "\n" + "\n".join(rows) + "\n")
    print("%d images -> %s" % (len(rows), out))


if __name__ == "__main__":
    main()
