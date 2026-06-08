# AMD ROCm on WSL for Strix Halo

This machine uses an AMD Ryzen AI Max+ 395 / Strix Halo APU with Radeon 8060S
graphics. On WSL, the working ROCm path is AMD's newer ROCDXG/librocdxg stack,
not the older legacy roc4wsl approach.

Validated local setup:

- OS: Ubuntu 24.04 on WSL2
- WSL device bridge: `/dev/dxg`
- ROCm: 7.2.x
- ROCDXG/librocdxg: v1.2.0
- GPU target: `gfx1151`
- GPU name in ROCm: `AMD Radeon(TM) 8060S Graphics`
- PyTorch: `2.9.1+rocm7.2.1`

## Why ROCDXG Is Needed

In WSL, AMD ROCm does not use the native Linux `/dev/kfd` and `/dev/dri` path.
Instead, it talks to the Windows GPU driver through Microsoft DXCore exposed as
`/dev/dxg`.

AMD's ROCDXG library, `librocdxg.so`, is the user-mode bridge that lets ROCm use
that `/dev/dxg` path. Without it, `rocminfo` may fail with errors like:

```text
No WDDM adapters found.
hsa_init Failed, possibly no supported GPU devices
```

or:

```text
Cannot load librocdxg.so
dlsym failed ... undefined symbol: hsaKmtOpenKFD
```

## One-Time System Setup

Install build tools:

```bash
sudo apt-get update
sudo apt-get install -y cmake build-essential pkg-config git
```

Build and install `librocdxg`:

```bash
rm -rf /tmp/librocdxg
git clone --depth 1 --branch v1.2.0 https://github.com/ROCm/librocdxg.git /tmp/librocdxg

cd /tmp/librocdxg
mkdir -p build
cd build

cmake .. -DWIN_SDK="/mnt/c/Program Files (x86)/Windows Kits/10/Include/10.0.26100.0/shared"
make -j"$(nproc)"
sudo make install
sudo ldconfig
```

If your Windows SDK is installed under a different version, list available paths:

```bash
ls "/mnt/c/Program Files (x86)/Windows Kits/10/Include"
```

Then adjust the `WIN_SDK` path.

## Required Environment Variable

For ROCm 7.2.x, set this before running ROCm/PyTorch commands:

```bash
export HSA_ENABLE_DXG_DETECTION=1
```

To persist it for future shells, add this near the top of `~/.bashrc`, before
any early `return` for non-interactive shells:

```bash
export HSA_ENABLE_DXG_DETECTION=1
```

## Validate ROCm

Run:

```bash
rocminfo | rg -n "gfx1151|AMD Radeon\\(TM\\) 8060S|Device Type|Compute Unit|Done"
```

Expected signs of success:

```text
Name:                    gfx1151
Marketing Name:          AMD Radeon(TM) 8060S Graphics
Device Type:             GPU
Compute Unit:            40
Name:                    amdgcn-amd-amdhsa--gfx1151
*** Done ***
```

`rocm-smi` is not the best validation command on this WSL path. Use `rocminfo`
and a framework-level test instead.

## Install ROCm PyTorch In A Project

Use a Python 3.12 virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip setuptools wheel
```

Install AMD's ROCm 7.2.1 PyTorch wheel set:

```bash
python -m pip install --no-cache-dir --force-reinstall \
  "https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2.1/torch-2.9.1%2Brocm7.2.1.lw.gitff65f5bc-cp312-cp312-linux_x86_64.whl" \
  "https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2.1/torchvision-0.24.0%2Brocm7.2.1.gitb919bd0c-cp312-cp312-linux_x86_64.whl" \
  "https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2.1/torchaudio-2.9.0%2Brocm7.2.1.gite3c6ee2b-cp312-cp312-linux_x86_64.whl" \
  "https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2.1/triton-3.5.1%2Brocm7.2.1.gita272dfa8-cp312-cp312-linux_x86_64.whl"
```

## Validate PyTorch

PyTorch still names the HIP/ROCm device API `cuda`, so `torch.cuda` is expected.

```bash
python - <<'PY'
import torch

print("torch:", torch.__version__)
print("hip:", torch.version.hip)
print("available:", torch.cuda.is_available())
print("device_count:", torch.cuda.device_count())

if torch.cuda.is_available():
    print("device:", torch.cuda.get_device_name(0))
    x = torch.randn((2048, 2048), device="cuda", dtype=torch.float16)
    y = torch.randn((2048, 2048), device="cuda", dtype=torch.float16)
    z = x @ y
    torch.cuda.synchronize()
    print("matmul:", z.shape, z.dtype, float(z.float().mean().cpu()))
PY
```

Expected signs of success:

```text
available: True
device_count: 1
device: AMD Radeon(TM) 8060S Graphics
matmul: torch.Size([2048, 2048]) torch.float16 ...
```

## Notes For Other Projects

- Reuse the same system-level ROCDXG install across projects.
- Create a separate `.venv` per project.
- Install the ROCm PyTorch wheels inside each project venv.
- Keep `HSA_ENABLE_DXG_DETECTION=1` available in the shell that launches Python.
- If `rocminfo` fails after a Windows driver update, first verify `/dev/dxg`
  exists, then rerun `rocminfo` with `HSA_ENABLE_DXG_DETECTION=1`.
- If PyTorch imports but reports no GPU, validate `rocminfo` before debugging
  Python packages.

## Useful References

- AMD WSL guide for Ryzen/Strix/Strix Halo:
  https://rocmdocs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installryz/wsl/howto_wsl.html
- AMD ROCDXG/librocdxg repository and compatibility matrix:
  https://github.com/ROCm/librocdxg
- AMD ROCm PyTorch wheel installation:
  https://rocm.docs.amd.com/projects/radeon-ryzen/en/latest/docs/install/installrad/native_linux/install-pytorch.html
