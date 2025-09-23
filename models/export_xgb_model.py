#!/usr/bin/env python
"""
Converte um pickle de XGBRegressor para .ubj e salva feature_names.
Uso:
    python scripts/export_xgb_model.py \
        --pkl models/model_rossmann.pkl \
        --out models/export
"""
from __future__ import annotations
import argparse, json, pickle
from pathlib import Path
import xgboost as xgb  # type: ignore

def main(pkl_path: Path, out_dir: Path):
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(pkl_path, "rb") as f:
        model = pickle.load(f)

    booster = model.get_booster()
    booster.save_model(str(out_dir / "model_rossmann.ubj"))

    feature_names = booster.feature_names or [
        "store","promo","store_type","assortment","competition_distance",
        "competition_open_since_month","competition_open_since_year","promo2",
        "promo2_since_week","promo2_since_year","competition_time_month","promo_time_week",
        "day_of_week_sin","day_of_week_cos","week_of_year_cos","week_of_year_sin",
        "month_cos","month_sin","day_sin","day_cos"
    ]
    (out_dir / "feature_names.json").write_text(
        json.dumps(feature_names, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("Export OK ->", out_dir)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pkl", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    main(args.pkl, args.out)
