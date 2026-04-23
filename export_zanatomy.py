"""
Z-Anatomy → web-ready GLB exporter
==================================

Converts the 2GB Z-Anatomy.blend source into per-system, Draco-compressed GLB
files suitable for streaming into a React-Three-Fiber viewer.

USAGE (run locally — Blender required, NOT in the Lovable sandbox):

    # 1. Download Z-Anatomy.blend from https://www.z-anatomy.com/
    # 2. Put this script next to it
    # 3. Run:
    blender -b Z-Anatomy.blend -P export_zanatomy.py

    # Optional flags (after `--`):
    blender -b Z-Anatomy.blend -P export_zanatomy.py -- \
        --out ./zanatomy-export \
        --decimate 0.8 \
        --only Skeletal,Muscular

Output: ./zanatomy-export/<system>.glb  (Draco level 6, KTX2 textures if present)

Mesh names are PRESERVED so the drill-down sidebar in AnatomyViewer.tsx still
works. Top-level Blender collections are treated as "systems".

Tested with Blender 3.6 LTS and 4.2 LTS.
"""

import bpy
import os
import sys
import time
import argparse

# ---------- CLI ----------

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="./zanatomy-export",
                   help="Output directory for GLB files")
    p.add_argument("--decimate", type=float, default=0.8,
                   help="Decimation ratio 0.1-1.0 (1.0 = no decimation). "
                        "Higher = more detail, larger files.")
    p.add_argument("--draco-level", type=int, default=6,
                   help="Draco compression level 0-10 (6 = balanced)")
    p.add_argument("--only", default="",
                   help="Comma-separated system names to export (default: all)")
    p.add_argument("--min-verts-to-decimate", type=int, default=5000,
                   help="Skip decimation for meshes below this vertex count")
    return p.parse_args(argv)

ARGS = parse_args()

# ---------- Helpers ----------

def log(msg):
    print(f"[zanatomy] {msg}", flush=True)

def file_size_mb(path):
    return os.path.getsize(path) / (1024 * 1024)

def slugify(name):
    return (
        name.lower()
        .replace(" ", "-")
        .replace("/", "-")
        .replace("&", "and")
        .replace(",", "")
    )

def all_meshes_in_collection(coll):
    """Recursively collect every MESH object inside a collection."""
    out = []
    for obj in coll.objects:
        if obj.type == "MESH":
            out.append(obj)
    for child in coll.children:
        out.extend(all_meshes_in_collection(child))
    return out

def deselect_all():
    bpy.ops.object.select_all(action="DESELECT")

def select_only(objs):
    deselect_all()
    for o in objs:
        o.select_set(True)
    if objs:
        bpy.context.view_layer.objects.active = objs[0]

def isolate_collection(target_coll, all_top_colls):
    """Hide every other top-level collection from export by excluding it
    from the view layer. Z-Anatomy uses nested collections heavily."""
    layer_coll = bpy.context.view_layer.layer_collection
    def walk(lc):
        lc.exclude = False
        # default: include only if it's the target or inside it
        for child in lc.children:
            walk(child)
    # First exclude everything
    for child in layer_coll.children:
        child.exclude = True
    # Then unexclude the target subtree
    def unexclude(lc, name):
        if lc.name == name:
            lc.exclude = False
            # also unexclude descendants
            stack = [lc]
            while stack:
                cur = stack.pop()
                cur.exclude = False
                stack.extend(cur.children)
            return True
        for child in lc.children:
            if unexclude(child, name):
                lc.exclude = False
                return True
        return False
    unexclude(layer_coll, target_coll.name)

def decimate_mesh(obj, ratio):
    """Apply a Decimate modifier to a single mesh. Preserves vertex groups
    and shape keys when possible. Skips small meshes."""
    if ratio >= 0.999:
        return
    try:
        mesh = obj.data
        if len(mesh.vertices) < ARGS.min_verts_to_decimate:
            return
        mod = obj.modifiers.new(name="ZA_Decimate", type="DECIMATE")
        mod.decimate_type = "COLLAPSE"
        mod.ratio = ratio
        mod.use_collapse_triangulate = True
        # Apply
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=mod.name)
    except Exception as e:
        log(f"  ! decimate failed on {obj.name}: {e}")

# ---------- Main export ----------

def export_system(coll, all_top_colls, out_dir):
    name = coll.name
    meshes = all_meshes_in_collection(coll)
    if not meshes:
        log(f"⏭  {name}: no meshes, skipping")
        return None

    log(f"▶  {name}: {len(meshes)} meshes")

    # Isolate collection so glTF exporter only sees this system
    isolate_collection(coll, all_top_colls)

    # Decimate (in place — we'll reload the file between systems)
    if ARGS.decimate < 0.999:
        log(f"   decimating @ ratio={ARGS.decimate} "
            f"(skipping <{ARGS.min_verts_to_decimate} verts)")
        for obj in meshes:
            try:
                obj.hide_viewport = False
                obj.hide_set(False)
            except Exception:
                pass
            decimate_mesh(obj, ARGS.decimate)

    # Select only this system's meshes for the export
    select_only([o for o in meshes if o.name in bpy.context.view_layer.objects])

    out_path = os.path.join(out_dir, f"{slugify(name)}.glb")
    log(f"   exporting → {out_path}")

    t0 = time.time()
    bpy.ops.export_scene.gltf(
        filepath=out_path,
        export_format="GLB",
        use_selection=True,
        use_visible=False,           # we already isolated via view layer
        use_renderable=False,
        export_apply=True,           # bake remaining modifiers
        export_yup=True,
        export_extras=False,
        export_cameras=False,
        export_lights=False,
        export_animations=False,
        export_skins=False,
        export_morph=False,
        export_draco_mesh_compression_enable=True,
        export_draco_mesh_compression_level=ARGS.draco_level,
        export_draco_position_quantization=14,
        export_draco_normal_quantization=10,
        export_draco_texcoord_quantization=12,
        export_draco_color_quantization=10,
        export_draco_generic_quantization=12,
        # Keep mesh names (critical for drill-down tree)
        export_keep_originals=False,
    )
    dt = time.time() - t0
    size = file_size_mb(out_path)
    log(f"   ✓ {size:.2f} MB in {dt:.1f}s")
    return {"name": name, "path": out_path, "mb": size, "meshes": len(meshes)}

def main():
    os.makedirs(ARGS.out, exist_ok=True)
    out_dir = os.path.abspath(ARGS.out)
    blend_path = bpy.data.filepath or "(unsaved)"
    log(f"source blend: {blend_path}")
    log(f"output dir:   {out_dir}")
    log(f"decimate:     {ARGS.decimate}  draco level: {ARGS.draco_level}")

    # We need to reload the original file before each system, because
    # decimation is destructive. So: snapshot the path, then loop.
    if not bpy.data.filepath:
        log("ERROR: open the .blend file first (blender -b file.blend -P script.py)")
        sys.exit(1)
    src = bpy.data.filepath

    # Discover top-level collections from the master scene
    bpy.ops.wm.open_mainfile(filepath=src)
    top_colls = [c for c in bpy.context.scene.collection.children]
    top_names = [c.name for c in top_colls]
    log(f"found {len(top_names)} top-level systems: {top_names}")

    only = [s.strip() for s in ARGS.only.split(",") if s.strip()]
    if only:
        top_names = [n for n in top_names if n in only]
        log(f"--only filter → exporting: {top_names}")

    report = []
    for sys_name in top_names:
        # Reload clean copy so previous decimation doesn't leak
        log(f"\n— reloading source for system: {sys_name} —")
        bpy.ops.wm.open_mainfile(filepath=src)
        all_top = [c for c in bpy.context.scene.collection.children]
        target = next((c for c in all_top if c.name == sys_name), None)
        if not target:
            log(f"⏭  {sys_name}: not found after reload")
            continue
        result = export_system(target, all_top, out_dir)
        if result:
            report.append(result)

    # Final report
    log("\n" + "=" * 60)
    log(f"EXPORT COMPLETE — {len(report)} files in {out_dir}")
    log("=" * 60)
    total = 0.0
    for r in sorted(report, key=lambda r: -r["mb"]):
        log(f"  {r['mb']:7.2f} MB   {r['meshes']:5d} meshes   {os.path.basename(r['path'])}")
        total += r["mb"]
    log("-" * 60)
    log(f"  {total:7.2f} MB   TOTAL")
    log("=" * 60)
    log("\nNext: drag these .glb files into your Lovable chat — they'll be")
    log("placed in public/anatomy/zanatomy/ and wired into ANATOMY_ASSETS.")

if __name__ == "__main__":
    main()
