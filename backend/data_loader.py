"""
Loads real ParcelPilot data from the supplied xlsx at startup.
Replaces the earlier placeholder mock_data.py now that the real data pack
has been provided. DATA_PACK_DIR is the single place that needs to change
if the pack ever moves.
"""
import pandas as pd
from pathlib import Path
from models import Account, Order, Ticket

DATA_PACK_DIR = Path(__file__).resolve().parent.parent / "data_pack"
XLSX_PATH = DATA_PACK_DIR / "ParcelPilot_Assessment_Data.xlsx"

_readme_df = pd.read_excel(XLSX_PATH, sheet_name="README", header=None)
_readme = dict(zip(_readme_df[0], _readme_df[1]))
DATASET_SNAPSHOT = str(_readme.get("Dataset snapshot", "unknown"))

_acc_df = pd.read_excel(XLSX_PATH, sheet_name="accounts")
_ord_df = pd.read_excel(XLSX_PATH, sheet_name="orders")
_tkt_df = pd.read_excel(XLSX_PATH, sheet_name="tickets")


def _clean(d: dict) -> dict:
    """NaN -> None so Pydantic optional fields validate correctly."""
    return {k: (None if pd.isna(v) else v) for k, v in d.items()}


ACCOUNTS = {row["account_id"]: Account(**_clean(row.to_dict())) for _, row in _acc_df.iterrows()}
ORDERS = {row["order_id"]: Order(**_clean(row.to_dict())) for _, row in _ord_df.iterrows()}
TICKETS = {row["ticket_id"]: Ticket(**_clean(row.to_dict())) for _, row in _tkt_df.iterrows()}
