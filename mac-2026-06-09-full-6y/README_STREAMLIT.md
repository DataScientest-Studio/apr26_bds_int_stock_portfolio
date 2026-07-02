# Streamlit App Setup

This file explains how to install the project requirements and run the Streamlit application.

The app entry point is:

```bash
app.py
```

## Prerequisites

- Python 3.12 is recommended for the current `requirements.txt`.
- Run the commands from the project root, the folder that contains `app.py` and `requirements.txt`.
- The app expects the prepared files in `data/`, `models/`, and `report_assets/` to already exist. They are included in this project folder.

Important: `requirements.txt` includes ROCm PyTorch wheel URLs for Linux/Python 3.12. Those lines are intended for this Linux/ROCm setup. If you are on macOS, Windows, or a machine without ROCm support, install the non-PyTorch requirements first or replace the PyTorch wheel lines with the correct PyTorch install command for your machine.

## 1. Create a Virtual Environment

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

On Windows PowerShell, use:

```powershell
.venv\Scripts\Activate.ps1
```

## 2. Install Requirements

Upgrade `pip` first:

```bash
python -m pip install --upgrade pip
```

Then install the project dependencies:

```bash
python -m pip install -r requirements.txt
```

This installs the main app dependencies, including:

- `streamlit`
- `pandas`
- `numpy`
- `matplotlib`
- `seaborn`
- `scikit-learn`
- `joblib`
- `xgboost`

## 3. Run the Streamlit App

From the project root:

```bash
streamlit run app.py
```

If you want to bind the app to all network interfaces, for example on a remote machine:

```bash
streamlit run app.py --server.address 0.0.0.0 --server.port 8501
```

After startup, Streamlit prints a local URL similar to:

```text
http://localhost:8501
```

Open that URL in your browser.

## 4. Stop the App

In the terminal where Streamlit is running, press:

```text
Ctrl+C
```

## Troubleshooting

If `streamlit` is not found, make sure the virtual environment is active and dependencies were installed:

```bash
source .venv/bin/activate
python -m pip install -r requirements.txt
```

If dependency installation fails on the ROCm PyTorch wheel lines, use a Python 3.12 Linux environment with ROCm support, or edit those PyTorch lines for your platform before installing.

If the app starts but a page fails to load, check that these folders and files are present:

```text
data/
models/
report_assets/
```

The Streamlit app reads precomputed CSV/model outputs from those folders instead of retraining models at runtime.
